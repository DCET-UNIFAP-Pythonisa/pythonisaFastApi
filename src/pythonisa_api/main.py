"""Ponto de entrada: `uvicorn pythonisa_api.main:app`."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pythonisa_api.api.erros import registrar_tratadores
from pythonisa_api.api.v1 import router as router_v1
from pythonisa_api.config import Settings
from pythonisa_api.db.base import criar_engine, criar_fabrica_sessao
from pythonisa_api.ml.modelo import carregar_preditor


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    app = FastAPI(title="Pythonisa API", version="0.1.0")
    app.state.settings = settings
    # Tabelas não são criadas na subida: isso é papel do `cli init-db`.
    app.state.engine = criar_engine(settings.database_url)
    app.state.fabrica_sessao = criar_fabrica_sessao(app.state.engine)
    # Modelo gerado pelo comando `treinar`; sem ele, as previsões usam só a grade (Nível 1).
    app.state.preditor = carregar_preditor(Path(settings.caminho_modelo))

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
