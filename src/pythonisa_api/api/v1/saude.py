from fastapi import APIRouter, Request

router = APIRouter(tags=["saúde"])


@router.get("/health")
def health(request: Request) -> dict:
    return {"status": "ok", "modelo_carregado": request.app.state.preditor is not None}
