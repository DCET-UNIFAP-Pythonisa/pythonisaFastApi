"""Regressão linear do tempo de cada trecho entre paradas consecutivas (Nível 2).

Cada exemplo de treino é um trecho de uma viagem: "da ordem i para a i+1, saindo às HH:MM,
levou N segundos". As variáveis são categóricas: trecho, hora cheia, tipo de dia e as
combinações trecho×hora e trecho×tipo de dia. A regressão continua linear, mas as combinações
deixam o efeito do pico ser maior nos trechos mais longos (o trânsito multiplica o tempo).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
from pathlib import Path

import joblib
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from pythonisa_api.db.models import RegistroDeteccao
from pythonisa_api.services.passagem import TIPO_DIA_POR_DIA_DA_SEMANA
from pythonisa_api.tempo import agora_local

MINIMO_TRECHOS = 50
DURACAO_MAXIMA_S = 3600  # trechos mais longos são considerados erro de dado

log = logging.getLogger(__name__)


@dataclass
class Trecho:
    id_linha: str
    ordem_origem: int
    momento: datetime
    segundos: float


def _variaveis(id_linha: str, ordem_origem: int, momento: datetime) -> list[str]:
    trecho = f"{id_linha}:{ordem_origem}"
    hora = str(momento.hour)
    tipo_dia = TIPO_DIA_POR_DIA_DA_SEMANA[momento.weekday()]
    return [trecho, hora, tipo_dia, f"{trecho}@{hora}", f"{trecho}@{tipo_dia}"]


class PreditorTrecho:
    def __init__(self, modelo, versao: str, metricas: dict):
        self.modelo = modelo
        self.versao = versao
        self.metricas = metricas

    def prever_segundos(self, id_linha: str, ordem_origem: int, momento: datetime) -> float:
        return float(self.modelo.predict([_variaveis(id_linha, ordem_origem, momento)])[0])


def montar_trechos(sessao: Session) -> list[Trecho]:
    """Pares de passagens consecutivas (ordem i → i+1) da mesma viagem."""
    registros = sessao.execute(
        select(
            RegistroDeteccao.id_viagem,
            RegistroDeteccao.id_linha,
            RegistroDeteccao.ordem_itinerario,
            RegistroDeteccao.timestamp_passagem,
        )
        .where(
            RegistroDeteccao.id_viagem.is_not(None),
            RegistroDeteccao.ordem_itinerario.is_not(None),
        )
        .order_by(RegistroDeteccao.id_viagem, RegistroDeteccao.ordem_itinerario)
    ).all()
    trechos = []
    for a, b in pairwise(registros):
        if a.id_viagem != b.id_viagem or b.ordem_itinerario != a.ordem_itinerario + 1:
            continue
        segundos = (b.timestamp_passagem - a.timestamp_passagem).total_seconds()
        if 0 < segundos <= DURACAO_MAXIMA_S:
            trechos.append(Trecho(a.id_linha, a.ordem_itinerario, a.timestamp_passagem, segundos))
    return trechos


def treinar(trechos: list[Trecho], dias_teste: int = 7) -> PreditorTrecho:
    """Treina com os dias mais antigos e avalia nos últimos `dias_teste` dias."""
    if len(trechos) < MINIMO_TRECHOS:
        raise ValueError(f"{len(trechos)} trechos no histórico (mínimo {MINIMO_TRECHOS})")
    corte = max(t.momento.date() for t in trechos) - timedelta(days=dias_teste)
    treino = [t for t in trechos if t.momento.date() <= corte]
    teste = [t for t in trechos if t.momento.date() > corte]
    if not treino:
        raise ValueError(f"o histórico precisa cobrir mais de {dias_teste} dias")

    def x(lista):
        return [_variaveis(t.id_linha, t.ordem_origem, t.momento) for t in lista]

    def y(lista):
        return [t.segundos for t in lista]

    modelo = make_pipeline(OneHotEncoder(handle_unknown="ignore"), LinearRegression())
    modelo.fit(x(treino), y(treino))

    # Baseline para comparação: média do trecho naquela hora (ou média geral).
    somas: dict[tuple[str, int], list[float]] = {}
    for t in treino:
        somas.setdefault((f"{t.id_linha}:{t.ordem_origem}", t.momento.hour), []).append(t.segundos)
    medias = {chave: sum(v) / len(v) for chave, v in somas.items()}
    media_geral = sum(y(treino)) / len(treino)
    baseline = [
        medias.get((f"{t.id_linha}:{t.ordem_origem}", t.momento.hour), media_geral) for t in teste
    ]

    previsto = modelo.predict(x(teste))
    treinado_em = agora_local().strftime("%Y-%m-%dT%H:%M")
    metricas = {
        "mae_segundos": round(float(mean_absolute_error(y(teste), previsto)), 1),
        "mae_baseline_segundos": round(float(mean_absolute_error(y(teste), baseline)), 1),
        "r2": round(float(r2_score(y(teste), previsto)), 3),
        "amostras_treino": len(treino),
        "amostras_teste": len(teste),
        "treinado_em": treinado_em,
    }
    return PreditorTrecho(modelo, f"regressao-linear-{treinado_em}", metricas)


def salvar_preditor(preditor: PreditorTrecho, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    dados = {"modelo": preditor.modelo, "versao": preditor.versao, "metricas": preditor.metricas}
    joblib.dump(dados, caminho)


def carregar_preditor(caminho: Path) -> PreditorTrecho | None:
    """Carrega o modelo salvo pelo comando `treinar`; sem arquivo válido, devolve None.

    O arquivo é um pickle: só carregue modelos gerados por este projeto (nunca um caminho
    vindo de uma requisição).
    """
    if not caminho.exists():
        return None
    try:
        dados = joblib.load(caminho)
        return PreditorTrecho(dados["modelo"], dados["versao"], dados["metricas"])
    except Exception:  # arquivo corrompido ou de outra versão: segue sem modelo (Nível 1)
        log.warning("Não foi possível carregar o modelo em %s; usando só a grade.", caminho)
        return None
