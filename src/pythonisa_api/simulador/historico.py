"""Histórico simulado de passagens, base de treino da regressão (Nível 2).

Para cada partida da grade, o ônibus passa por todas as paradas do itinerário.
O tempo de cada trecho é o programado ajustado pelo trânsito:

    Δt = max(30 s, programado × fator_horario × fator_dia × ruído)

Fora do pico (fator 0,85) o ônibus tende a adiantar; no pico (1,3), a atrasar.
A semente fixa torna o histórico reprodutível.
"""

import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pythonisa_api.db.models import HorarioProgramado, Linha, RegistroDeteccao, Viagem
from pythonisa_api.services.passagem import TIPO_DIA_POR_DIA_DA_SEMANA

PICOS = [(time(6, 30), time(8, 30)), (time(11, 30), time(13, 30)), (time(17, 0), time(19, 0))]
FATOR_PICO, FATOR_FORA_DO_PICO = 1.3, 0.85
FATOR_DIA = {"util": 1.0, "sabado": 0.9, "domingo": 0.8}
TRECHO_MINIMO_S = 30
DESVIO_PARTIDA_S = 120  # a saída varia em torno do horário da grade
DESVIO_RUIDO = 0.1


def fator_horario(hora: time) -> float:
    return FATOR_PICO if any(inicio <= hora < fim for inicio, fim in PICOS) else FATOR_FORA_DO_PICO


def fator_dia(tipo_dia: str) -> float:
    return FATOR_DIA[tipo_dia]


def simular_historico(sessao: Session, ate: date, dias: int, semente: int = 42) -> int:
    """Simula os `dias` anteriores a `ate` e devolve quantas passagens gravou.

    Dias que já têm viagens simuladas são pulados, então rodar de novo não duplica.
    """
    rng = random.Random(semente)
    linhas = sessao.scalars(select(Linha).order_by(Linha.id)).all()
    total = 0
    for atras in range(dias, 0, -1):
        dia = ate - timedelta(days=atras)
        ja_simulado = sessao.scalar(
            select(func.count())
            .select_from(Viagem)
            .where(Viagem.data == dia, Viagem.origem == "simulado")
        )
        if ja_simulado:
            continue
        tipo_dia = TIPO_DIA_POR_DIA_DA_SEMANA[dia.weekday()]
        for linha in linhas:
            horarios = sessao.scalars(
                select(HorarioProgramado)
                .where(
                    HorarioProgramado.id_linha == linha.id, HorarioProgramado.tipo_dia == tipo_dia
                )
                .order_by(HorarioProgramado.hora_partida)
            ).all()
            for horario in horarios:
                total += _simular_viagem(sessao, linha, horario, dia, tipo_dia, rng)
        sessao.commit()
    return total


def _simular_viagem(sessao, linha, horario, dia, tipo_dia, rng) -> int:
    viagem = Viagem(id_linha=linha.id, id_horario=horario.id, data=dia, origem="simulado")
    sessao.add(viagem)
    sessao.flush()

    atraso_partida = timedelta(seconds=round(rng.gauss(0, DESVIO_PARTIDA_S)))
    momento = datetime.combine(dia, horario.hora_partida) + atraso_partida
    anterior = None
    for item in linha.itinerario:
        if anterior is not None:
            programado_s = (item.minutos_programados - anterior.minutos_programados) * 60
            fator = fator_horario(momento.time()) * fator_dia(tipo_dia)
            segundos = programado_s * fator * rng.lognormvariate(0, DESVIO_RUIDO)
            momento += timedelta(seconds=round(max(TRECHO_MINIMO_S, segundos)))
        sessao.add(
            RegistroDeteccao(
                id_linha=linha.id,
                id_parada=item.id_parada,
                id_viagem=viagem.id,
                ordem_itinerario=item.ordem,
                timestamp_passagem=momento,
                origem="simulado",
                recebido_em=momento,
            )
        )
        anterior = item
    return len(linha.itinerario)
