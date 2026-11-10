"""Consultas de linhas e paradas. Sem FastAPI: recebe uma sessão e devolve modelos."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from pythonisa_api.db.models import Linha, Parada, RotaParada
from pythonisa_api.erros import LinhaNaoEncontrada, ParadaNaoEncontrada


def listar_linhas(sessao: Session) -> list[Linha]:
    return list(sessao.scalars(select(Linha).order_by(Linha.nome)))


def obter_linha(sessao: Session, id_linha: str) -> Linha:
    linha = sessao.get(Linha, id_linha)
    if linha is None:
        raise LinhaNaoEncontrada(id_linha)
    return linha


def listar_paradas(sessao: Session, id_linha: str | None = None) -> list[Parada]:
    consulta = select(Parada).order_by(Parada.nome, Parada.id)
    if id_linha is not None:
        obter_linha(sessao, id_linha)
        consulta = consulta.where(
            Parada.id.in_(select(RotaParada.id_parada).where(RotaParada.id_linha == id_linha))
        )
    return list(sessao.scalars(consulta))


def obter_parada(sessao: Session, id_parada: str) -> Parada:
    parada = sessao.get(Parada, id_parada)
    if parada is None:
        raise ParadaNaoEncontrada(id_parada)
    return parada


def linhas_da_parada(sessao: Session, id_parada: str) -> list[Linha]:
    obter_parada(sessao, id_parada)
    consulta = (
        select(Linha)
        .where(Linha.id.in_(select(RotaParada.id_linha).where(RotaParada.id_parada == id_parada)))
        .order_by(Linha.nome)
    )
    return list(sessao.scalars(consulta))
