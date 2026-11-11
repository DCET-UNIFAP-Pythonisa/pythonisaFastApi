from fastapi import APIRouter

from pythonisa_api.api.v1 import deteccoes, linhas, paradas, previsoes, saude

router = APIRouter()
router.include_router(saude.router)
router.include_router(linhas.router)
router.include_router(paradas.router)
router.include_router(deteccoes.router)
router.include_router(previsoes.router)
