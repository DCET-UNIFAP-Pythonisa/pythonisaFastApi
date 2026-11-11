"""Dependências injetadas nas rotas."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session


def obter_preditor(request: Request):
    """Modelo carregado na subida do app, ou None (previsões só pela grade)."""
    return request.app.state.preditor


def obter_sessao(request: Request) -> Iterator[Session]:
    with request.app.state.fabrica_sessao() as sessao:
        yield sessao


# Atalho para as rotas: `sessao: SessaoDep` recebe uma sessão aberta por requisição.
SessaoDep = Annotated[Session, Depends(obter_sessao)]
