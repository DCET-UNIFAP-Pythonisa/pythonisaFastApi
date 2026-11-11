from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import AwareDatetime

from pythonisa_api.api.deps import SessaoDep
from pythonisa_api.schemas.previsao import PrevisaoSaida
from pythonisa_api.services.previsao import prever_chegada
from pythonisa_api.tempo import agora_local, para_local_naive

router = APIRouter(prefix="/previsoes", tags=["previsões"])


@router.get(
    "",
    response_model=PrevisaoSaida,
    summary="Próxima chegada de uma linha numa parada (programado e previsto)",
)
def prever(
    id_linha: str,
    id_parada: str,
    sessao: SessaoDep,
    agora: Annotated[
        AwareDatetime | None,
        Query(description="Simula outro momento (ex.: horário de pico na demo). Exige fuso."),
    ] = None,
):
    momento = para_local_naive(agora) if agora else agora_local()
    return prever_chegada(sessao, id_linha, id_parada, momento)
