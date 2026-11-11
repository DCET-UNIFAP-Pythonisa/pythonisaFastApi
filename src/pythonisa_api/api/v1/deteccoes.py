from fastapi import APIRouter, status

from pythonisa_api.api.deps import SessaoDep
from pythonisa_api.schemas.passagem import PassagemEntrada, PassagemSaida
from pythonisa_api.services.passagem import registrar_passagem

router = APIRouter(prefix="/deteccoes", tags=["passagens"])


@router.post(
    "",
    response_model=PassagemSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Registra a passagem de um ônibus por uma parada",
)
def registrar(entrada: PassagemEntrada, sessao: SessaoDep):
    return registrar_passagem(sessao, entrada)
