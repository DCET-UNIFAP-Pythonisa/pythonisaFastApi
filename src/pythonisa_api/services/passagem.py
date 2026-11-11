"""Registro de passagem de ônibus por parada (usado pelo simulador e, no futuro, pela VC)."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pythonisa_api.db.models import HorarioProgramado, RegistroDeteccao, RotaParada, Viagem
from pythonisa_api.erros import DadosInvalidos, ParadaForaDaLinha
from pythonisa_api.schemas.passagem import PassagemEntrada
from pythonisa_api.services.consulta import obter_linha, obter_parada
from pythonisa_api.tempo import agora_local, para_local_naive

TOLERANCIA_HORARIO = timedelta(minutes=15)
TIPO_DIA_POR_DIA_DA_SEMANA = ["util"] * 5 + ["sabado", "domingo"]  # segunda=0 ... domingo=6


def horario_mais_proximo(
    sessao: Session, id_linha: str, momento: datetime
) -> HorarioProgramado | None:
    """Horário da grade mais próximo de `momento` (até 15 min de diferença), ou None."""
    tipo_dia = TIPO_DIA_POR_DIA_DA_SEMANA[momento.weekday()]
    horarios = sessao.scalars(
        select(HorarioProgramado).where(
            HorarioProgramado.id_linha == id_linha, HorarioProgramado.tipo_dia == tipo_dia
        )
    ).all()

    def diferenca(horario: HorarioProgramado) -> timedelta:
        return abs(datetime.combine(momento.date(), horario.hora_partida) - momento)

    candidatos = [h for h in horarios if diferenca(h) <= TOLERANCIA_HORARIO]
    return min(candidatos, key=diferenca, default=None)


def registrar_passagem(sessao: Session, entrada: PassagemEntrada) -> RegistroDeteccao:
    linha = obter_linha(sessao, entrada.id_linha)
    obter_parada(sessao, entrada.id_parada)
    ordens = list(
        sessao.scalars(
            select(RotaParada.ordem).where(
                RotaParada.id_linha == linha.id, RotaParada.id_parada == entrada.id_parada
            )
        )
    )
    if not ordens:
        raise ParadaForaDaLinha(entrada.id_linha, entrada.id_parada)

    momento = para_local_naive(entrada.timestamp_passagem)
    id_viagem = entrada.id_viagem
    ordem = min(ordens)

    if id_viagem is not None:
        viagem = sessao.get(Viagem, id_viagem)
        if viagem is None or viagem.id_linha != linha.id:
            raise DadosInvalidos(f"Viagem '{id_viagem}' não existe para a linha '{linha.id}'.")
        # Parada repetida no itinerário (ex.: terminal na ordem 1 e na última):
        # usa a primeira ordem depois da última passagem registrada nesta viagem.
        ultima = sessao.scalar(
            select(func.max(RegistroDeteccao.ordem_itinerario)).where(
                RegistroDeteccao.id_viagem == id_viagem
            )
        )
        if ultima is not None:
            ordem = min((o for o in ordens if o > ultima), default=ordem)
    elif 1 in ordens:
        # Passagem na primeira parada = início de uma nova viagem.
        horario = horario_mais_proximo(sessao, linha.id, momento)
        viagem = Viagem(
            id_linha=linha.id,
            data=momento.date(),
            origem=entrada.origem,
            id_horario=horario.id if horario else None,
        )
        sessao.add(viagem)
        sessao.flush()
        id_viagem = viagem.id

    registro = RegistroDeteccao(
        id_linha=linha.id,
        id_parada=entrada.id_parada,
        id_viagem=id_viagem,
        ordem_itinerario=ordem,
        timestamp_passagem=momento,
        origem=entrada.origem,
        texto_letreiro=entrada.texto_letreiro,
        confianca_ocr=entrada.confianca_ocr,
        recebido_em=agora_local(),
    )
    sessao.add(registro)
    sessao.commit()
    return registro
