from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from pythonisa_api import cli
from pythonisa_api.db.models import Viagem
from pythonisa_api.main import create_app
from pythonisa_api.ml.modelo import (
    carregar_preditor,
    montar_trechos,
    salvar_preditor,
    treinar,
)
from pythonisa_api.seed.carregar import carregar_seed
from pythonisa_api.simulador.historico import simular_historico

SEGUNDA = datetime(2026, 11, 30)


@pytest.fixture
def historico(sessao_com_seed_mini):
    simular_historico(sessao_com_seed_mini, ate=date(2026, 11, 28), dias=21)
    return sessao_com_seed_mini


@pytest.fixture
def preditor(historico):
    return treinar(montar_trechos(historico))


def _viagens(sessao, id_linha):
    return sessao.scalar(
        select(func.count()).select_from(Viagem).where(Viagem.id_linha == id_linha)
    )


def test_montar_trechos_pares_consecutivos_da_mesma_viagem(historico):
    trechos = montar_trechos(historico)
    # Itinerários do seed mini: linha-a com 4 paradas (3 trechos), linha-b com 3 (2 trechos).
    assert len(trechos) == 3 * _viagens(historico, "linha-a") + 2 * _viagens(historico, "linha-b")
    assert all(t.segundos > 0 for t in trechos)


def test_regressao_aprende_o_pico(preditor):
    # 07:00 é pico; na hora 6 só a partida das 06:30 é pico.
    pico = preditor.prever_segundos("linha-a", 1, SEGUNDA.replace(hour=7))
    antes = preditor.prever_segundos("linha-a", 1, SEGUNDA.replace(hour=6))
    assert pico > antes
    assert set(preditor.metricas) == {
        "mae_segundos",
        "mae_baseline_segundos",
        "r2",
        "amostras_treino",
        "amostras_teste",
        "treinado_em",
    }
    assert preditor.versao.startswith("regressao-linear-")


def test_treinar_sem_historico():
    with pytest.raises(ValueError):
        treinar([])


def test_salvar_e_carregar(preditor, tmp_path):
    caminho = tmp_path / "modelos" / "modelo.joblib"
    salvar_preditor(preditor, caminho)
    carregado = carregar_preditor(caminho)
    momento = SEGUNDA.replace(hour=7)
    assert carregado.versao == preditor.versao
    assert carregado.prever_segundos("linha-a", 2, momento) == pytest.approx(
        preditor.prever_segundos("linha-a", 2, momento)
    )


def test_carregar_arquivo_ausente_ou_corrompido(tmp_path):
    assert carregar_preditor(tmp_path / "nao-existe.joblib") is None
    corrompido = tmp_path / "corrompido.joblib"
    corrompido.write_bytes(b"\x00 isto nao e um modelo \xff")
    assert carregar_preditor(corrompido) is None


def test_sem_modelo_servidor_sobe_no_nivel_1(cliente):
    assert cliente.get("/api/v1/health").json()["modelo_carregado"] is False
    r = cliente.get("/api/v1/modelo")
    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "MODELO_NAO_TREINADO"


def test_com_modelo_salvo_servidor_carrega(preditor, settings_teste):
    salvar_preditor(preditor, Path(settings_teste.caminho_modelo))
    app = create_app(settings_teste)
    try:
        with TestClient(app) as cliente:
            assert cliente.get("/api/v1/health").json()["modelo_carregado"] is True
            r = cliente.get("/api/v1/modelo")
    finally:
        app.state.engine.dispose()
    assert r.status_code == 200
    assert r.json()["versao"] == preditor.versao
    assert "mae_segundos" in r.json()


def test_cli_treinar(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    monkeypatch.setenv("CAMINHO_MODELO", str(tmp_path / "modelo.joblib"))
    assert cli.main(["init-db"]) == 0
    assert cli.main(["seed"]) == 0
    assert cli.main(["treinar"]) == 1
    assert "simular-historico" in capsys.readouterr().err
    assert cli.main(["simular-historico", "--dias", "21"]) == 0
    assert cli.main(["treinar"]) == 0
    assert (tmp_path / "modelo.joblib").exists()


def test_regressao_nao_perde_para_a_media_simples_no_seed_real(sessao):
    carregar_seed(sessao)
    simular_historico(sessao, ate=date(2026, 11, 28), dias=28)
    metricas = treinar(montar_trechos(sessao)).metricas
    assert metricas["mae_segundos"] <= metricas["mae_baseline_segundos"]
