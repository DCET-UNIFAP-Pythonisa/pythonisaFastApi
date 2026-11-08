from fastapi import APIRouter

router = APIRouter(tags=["saúde"])


@router.get("/health")
def health() -> dict:
    # modelo_carregado passa a refletir o preditor na Parte 2 (ML).
    return {"status": "ok", "modelo_carregado": False}
