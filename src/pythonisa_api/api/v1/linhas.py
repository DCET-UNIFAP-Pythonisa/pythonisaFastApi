from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from pythonisa_api.api.deps import obter_sessao
from pythonisa_api.schemas.consulta import ItinerarioSaida, LinhaSaida
from pythonisa_api.services import consulta

router = APIRouter(prefix="/linhas", tags=["linhas"])
SessaoDep = Annotated[Session, Depends(obter_sessao)]


@router.get("", response_model=list[LinhaSaida], summary="Lista as linhas")
def listar_linhas(sessao: SessaoDep):
    return consulta.listar_linhas(sessao)


@router.get(
    "/{id_linha}/paradas",
    response_model=ItinerarioSaida,
    summary="Itinerário ordenado da linha (para desenhar a rota no mapa)",
)
def itinerario(id_linha: str, sessao: SessaoDep):
    linha = consulta.obter_linha(sessao, id_linha)
    return {"linha": linha, "itinerario": linha.itinerario}
