from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from pythonisa_api.api.deps import obter_sessao
from pythonisa_api.schemas.consulta import LinhaSaida, ParadaProximaSaida, ParadaSaida
from pythonisa_api.services import consulta, geo

router = APIRouter(prefix="/paradas", tags=["paradas"])
SessaoDep = Annotated[Session, Depends(obter_sessao)]


@router.get("", response_model=list[ParadaSaida], summary="Lista as paradas")
def listar_paradas(sessao: SessaoDep, id_linha: str | None = None):
    return consulta.listar_paradas(sessao, id_linha)


# Declarada antes das rotas com {id_parada} para "proxima" não ser lida como um id.
@router.get(
    "/proxima", response_model=ParadaProximaSaida, summary="Parada mais próxima de um ponto"
)
def parada_proxima(
    sessao: SessaoDep,
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
):
    parada, distancia = geo.parada_mais_proxima(
        consulta.listar_paradas(sessao), latitude, longitude
    )
    return {"parada": parada, "distancia_metros": round(distancia)}


@router.get(
    "/{id_parada}/linhas", response_model=list[LinhaSaida], summary="Linhas que atendem a parada"
)
def linhas_da_parada(id_parada: str, sessao: SessaoDep):
    return consulta.linhas_da_parada(sessao, id_parada)
