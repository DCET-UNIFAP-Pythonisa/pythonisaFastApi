"""Ponto de entrada: `uvicorn pythonisa_api.main:app`."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pythonisa_api.api.erros import registrar_tratadores
from pythonisa_api.api.v1 import router as router_v1
from pythonisa_api.config import Settings
from pythonisa_api.db.base import criar_engine, criar_fabrica_sessao


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    app = FastAPI(title="Pythonisa API", version="0.1.0")
    app.state.settings = settings
    # Tabelas não são criadas na subida: isso é papel do `cli init-db`.
    app.state.engine = criar_engine(settings.database_url)
    app.state.fabrica_sessao = criar_fabrica_sessao(app.state.engine)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registrar_tratadores(app)
    app.include_router(router_v1, prefix="/api/v1")
    return app


app = create_app()
