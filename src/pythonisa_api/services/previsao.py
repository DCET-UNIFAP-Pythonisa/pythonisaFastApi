"""Previsão de chegada do próximo ônibus de uma linha numa parada.

Nível 1: horário programado (grade + minutos programados até a parada).
Nível 2: com um preditor, o tempo de cada trecho vem da regressão (ver ml/modelo.py).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from pythonisa_api.db.models import HorarioProgramado, Linha, Parada
from pythonisa_api.erros import ParadaForaDaLinha
from pythonisa_api.services.consulta import obter_linha, obter_parada
from pythonisa_api.services.passagem import TIPO_DIA_POR_DIA_DA_SEMANA


class Preditor(Protocol):
    versao: str

    def prever_segundos(self, id_linha: str, ordem_origem: int, momento: datetime) -> float: ...


@dataclass
class Previsao:
    linha: Linha
    parada: Parada
    situacao: str
    horario_programado: datetime | None
    horario_previsto: datetime | None
    minutos_restantes: int | None
    diferenca_minutos: int | None
    versao_modelo: str | None
    gerado_em: datetime


def _situacao(diferenca_minutos: int) -> str:
    if diferenca_minutos < -1:
        return "adiantado"
    if diferenca_minutos > 1:
        return "atrasado"
    return "no_horario"


def prever_chegada(
    sessao: Session,
    id_linha: str,
    id_parada: str,
    agora: datetime,
    preditor: Preditor | None = None,
) -> Previsao:
    """Próxima chegada (programada e prevista) a partir de `agora` (naive, horário local)."""
    linha = obter_linha(sessao, id_linha)
    parada = obter_parada(sessao, id_parada)
    minutos = {item.ordem: item.minutos_programados for item in linha.itinerario}
    ordens = [item.ordem for item in linha.itinerario if item.id_parada == id_parada]
    if not ordens:
        raise ParadaForaDaLinha(id_linha, id_parada)

    tipo_dia = TIPO_DIA_POR_DIA_DA_SEMANA[agora.weekday()]
    partidas = sessao.scalars(
        select(HorarioProgramado.hora_partida).where(
            HorarioProgramado.id_linha == id_linha, HorarioProgramado.tipo_dia == tipo_dia
        )
    ).all()

    candidatos = []  # (previsto, programado) de cada partida × ocorrência da parada
    for hora in partidas:
        partida = datetime.combine(agora.date(), hora)
        for ordem in ordens:
            programado = partida + timedelta(minutes=minutos[ordem])
            previsto = programado
            if previsto >= agora:
                candidatos.append((previsto, programado))

    versao = preditor.versao if preditor else None
    if not candidatos:
        return Previsao(linha, parada, "sem_servico", None, None, None, None, versao, agora)

    previsto, programado = min(candidatos)
    diferenca = round((previsto - programado).total_seconds() / 60)
    return Previsao(
        linha=linha,
        parada=parada,
        situacao=_situacao(diferenca),
        horario_programado=programado,
        horario_previsto=previsto,
        minutos_restantes=round((previsto - agora).total_seconds() / 60),
        diferenca_minutos=diferenca,
        versao_modelo=versao,
        gerado_em=agora,
    )
