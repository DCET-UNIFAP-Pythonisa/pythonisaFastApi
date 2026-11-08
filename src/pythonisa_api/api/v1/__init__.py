from fastapi import APIRouter

from pythonisa_api.api.v1 import saude

router = APIRouter()
router.include_router(saude.router)
