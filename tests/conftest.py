from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pythonisa_api.config import Settings
from pythonisa_api.db.base import criar_tabelas
from pythonisa_api.main import create_app
from pythonisa_api.seed.carregar import carregar_seed


@pytest.fixture
def settings_teste(tmp_path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'teste.db'}",
        cors_origins=["http://localhost:5555"],
        caminho_modelo=str(tmp_path / "modelo.joblib"),
        _env_file=None,
    )


@pytest.fixture
def app(settings_teste):
    app = create_app(settings_teste)
    criar_tabelas(app.state.engine)
    yield app
    app.state.engine.dispose()


@pytest.fixture
def cliente(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sessao(app):
    with app.state.fabrica_sessao() as s:
        yield s


SEED_MINI = Path(__file__).parent / "fixtures" / "seed_mini"


@pytest.fixture
def sessao_com_seed_mini(sessao):
    carregar_seed(sessao, SEED_MINI)
    return sessao


@pytest.fixture
def api(cliente, sessao_com_seed_mini):
    """Cliente HTTP com o seed mini carregado."""
    return cliente
