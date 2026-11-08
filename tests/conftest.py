import pytest
from fastapi.testclient import TestClient

from pythonisa_api.config import Settings
from pythonisa_api.main import create_app


@pytest.fixture
def settings_teste(tmp_path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'teste.db'}",
        cors_origins=["*"],
        _env_file=None,
    )


@pytest.fixture
def app(settings_teste):
    return create_app(settings_teste)


@pytest.fixture
def cliente(app):
    with TestClient(app) as c:
        yield c
