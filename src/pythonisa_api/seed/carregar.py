"""Carga dos dados fixos (linhas, paradas, itinerários, grade e letreiros) a partir de JSON.

Idempotente: pode rodar várias vezes. Linhas e paradas são atualizadas, o itinerário de
cada linha é substituído e horários/padrões só são inseridos se ainda não existirem.
Arquivo ou campo inválido vira ErroSeed e nada é gravado (a transação é desfeita).
"""

import json
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from itertools import pairwise
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pythonisa_api.db.models import HorarioProgramado, Linha, PadraoLetreiro, Parada, RotaParada
from pythonisa_api.services.geo import haversine_metros

DIRETORIO_PADRAO = Path(__file__).parent / "dados"

SENTIDOS = {"ida", "volta"}
TIPOS_DIA = {"util", "sabado", "domingo"}
# Distância em linha reta subestima o trajeto pelas ruas; 1.3 compensa a sinuosidade.
FATOR_TORTUOSIDADE = 1.3
VELOCIDADE_PROGRAMADA_M_POR_MIN = 20_000 / 60  # 20 km/h


class ErroSeed(Exception):
    pass


@dataclass(frozen=True)
class ResumoSeed:
    linhas: int
    paradas: int
    itens_itinerario: int
    horarios: int
    padroes: int


def _ler(diretorio: Path, nome: str):
    try:
        return json.loads((diretorio / nome).read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        # OSError: arquivo ausente ou ilegível. ValueError: JSON inválido ou texto fora de UTF-8.
        raise ErroSeed(f"{nome}: não foi possível ler o arquivo ({erro})") from erro


def _hora(texto: str, contexto: str) -> time:
    try:
        return time.fromisoformat(texto)
    except ValueError as erro:
        raise ErroSeed(f"{contexto}: horário inválido '{texto}'") from erro


def _expandir_grade(inicio: time, fim: time, intervalo_min: int) -> list[time]:
    base = datetime(2000, 1, 1)
    atual = base.replace(hour=inicio.hour, minute=inicio.minute)
    limite = base.replace(hour=fim.hour, minute=fim.minute)
    horarios = []
    while atual <= limite:
        horarios.append(atual.time())
        atual += timedelta(minutes=intervalo_min)
    return horarios


def _minutos_programados(coordenadas: list[tuple[float, float]]) -> list[int]:
    minutos, acumulado = [0], 0.0
    for (lat1, lon1), (lat2, lon2) in pairwise(coordenadas):
        acumulado += haversine_metros(lat1, lon1, lat2, lon2)
        minutos.append(round(acumulado * FATOR_TORTUOSIDADE / VELOCIDADE_PROGRAMADA_M_POR_MIN))
    return minutos


def _validar(linhas, paradas, itinerarios, grade, letreiros) -> None:
    ids_linhas = {linha["id"] for linha in linhas}
    ids_paradas = {parada["id"] for parada in paradas}

    for nome_arquivo, conteudo in [
        ("itinerarios.json", itinerarios),
        ("grade.json", grade),
        ("letreiros.json", letreiros),
    ]:
        desconhecidas = set(conteudo) - ids_linhas
        if desconhecidas:
            raise ErroSeed(f"{nome_arquivo}: linhas desconhecidas {sorted(desconhecidas)}")
        faltando = ids_linhas - set(conteudo)
        if faltando:
            raise ErroSeed(f"{nome_arquivo}: linhas sem dados {sorted(faltando)}")

    for id_linha, itens in itinerarios.items():
        if not itens:
            raise ErroSeed(f"itinerarios.json: linha '{id_linha}' com itinerário vazio")
        for posicao, item in enumerate(itens, start=1):
            if item["id_parada"] not in ids_paradas:
                raise ErroSeed(
                    f"itinerarios.json: linha '{id_linha}', ordem {posicao}: "
                    f"parada '{item['id_parada']}' não existe em paradas.json"
                )
            if item["sentido"] not in SENTIDOS:
                raise ErroSeed(
                    f"itinerarios.json: linha '{id_linha}', ordem {posicao}: "
                    f"sentido '{item['sentido']}' inválido (use ida/volta)"
                )

    for id_linha, por_tipo in grade.items():
        for tipo_dia, faixa in por_tipo.items():
            if tipo_dia not in TIPOS_DIA:
                raise ErroSeed(f"grade.json: linha '{id_linha}': tipo de dia '{tipo_dia}' inválido")
            contexto = f"grade.json: linha '{id_linha}', {tipo_dia}"
            if faixa["intervalo_min"] <= 0:
                raise ErroSeed(f"{contexto}: intervalo_min deve ser positivo")
            if _hora(faixa["inicio"], contexto) > _hora(faixa["fim"], contexto):
                raise ErroSeed(f"{contexto}: início depois do fim")


def carregar_seed(sessao: Session, diretorio: Path = DIRETORIO_PADRAO) -> ResumoSeed:
    try:
        return _carregar(sessao, diretorio)
    except (KeyError, TypeError, ValueError) as erro:
        # Campo obrigatório ausente, chave desconhecida ou valor de tipo/formato errado no JSON.
        sessao.rollback()
        raise ErroSeed(f"campo ausente ou inválido nos arquivos de seed: {erro}") from erro
    except IntegrityError as erro:
        sessao.rollback()
        raise ErroSeed(f"dados inválidos nos arquivos de seed: {erro.orig}") from erro


def _carregar(sessao: Session, diretorio: Path) -> ResumoSeed:
    linhas = _ler(diretorio, "linhas.json")
    paradas = _ler(diretorio, "paradas.json")
    itinerarios = _ler(diretorio, "itinerarios.json")
    grade = _ler(diretorio, "grade.json")
    letreiros = _ler(diretorio, "letreiros.json")
    _validar(linhas, paradas, itinerarios, grade, letreiros)

    for dados in linhas:
        sessao.merge(Linha(**dados))
    for dados in paradas:
        sessao.merge(Parada(**dados))
    sessao.flush()

    coordenadas = {p["id"]: (p["latitude"], p["longitude"]) for p in paradas}
    total_itens = 0
    for id_linha, itens in itinerarios.items():
        sessao.execute(delete(RotaParada).where(RotaParada.id_linha == id_linha))
        minutos = _minutos_programados([coordenadas[i["id_parada"]] for i in itens])
        for ordem, (item, minuto) in enumerate(zip(itens, minutos, strict=True), start=1):
            sessao.add(
                RotaParada(
                    id_linha=id_linha,
                    ordem=ordem,
                    id_parada=item["id_parada"],
                    sentido=item["sentido"],
                    minutos_programados=minuto,
                )
            )
        total_itens += len(itens)

    total_horarios = 0
    for id_linha, por_tipo in grade.items():
        existentes = set(
            sessao.execute(
                select(HorarioProgramado.tipo_dia, HorarioProgramado.hora_partida).where(
                    HorarioProgramado.id_linha == id_linha
                )
            ).all()
        )
        for tipo_dia, faixa in por_tipo.items():
            horarios = _expandir_grade(
                time.fromisoformat(faixa["inicio"]),
                time.fromisoformat(faixa["fim"]),
                faixa["intervalo_min"],
            )
            for hora in horarios:
                if (tipo_dia, hora) not in existentes:
                    sessao.add(
                        HorarioProgramado(id_linha=id_linha, tipo_dia=tipo_dia, hora_partida=hora)
                    )
            total_horarios += len(horarios)

    total_padroes = 0
    for id_linha, padroes in letreiros.items():
        existentes = set(
            sessao.scalars(
                select(PadraoLetreiro.padrao).where(PadraoLetreiro.id_linha == id_linha)
            ).all()
        )
        for dados in padroes:
            if dados["padrao"] not in existentes:
                sessao.add(PadraoLetreiro(id_linha=id_linha, **dados))
                existentes.add(dados["padrao"])
        total_padroes += len(padroes)

    sessao.commit()
    return ResumoSeed(
        linhas=len(linhas),
        paradas=len(paradas),
        itens_itinerario=total_itens,
        horarios=total_horarios,
        padroes=total_padroes,
    )
