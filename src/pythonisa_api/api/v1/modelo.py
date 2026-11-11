from fastapi import APIRouter, Request

from pythonisa_api.erros import ModeloNaoTreinado

router = APIRouter(prefix="/modelo", tags=["modelo"])


@router.get("", summary="Versão e métricas do modelo de previsão carregado")
def modelo(request: Request) -> dict:
    preditor = request.app.state.preditor
    if preditor is None:
        raise ModeloNaoTreinado()
    return {"versao": preditor.versao, **preditor.metricas}
