def test_health_responde_ok(cliente):
    r = cliente.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "modelo_carregado": False}


def test_cors_libera_so_a_origem_configurada(cliente):
    # A origem liberada vem de settings_teste (tests/conftest.py).
    liberada = cliente.get("/api/v1/health", headers={"Origin": "http://localhost:5555"})
    outra = cliente.get("/api/v1/health", headers={"Origin": "http://outro.site"})
    assert liberada.headers["access-control-allow-origin"] == "http://localhost:5555"
    assert "access-control-allow-origin" not in outra.headers


def test_metodo_nao_permitido_mantem_cabecalho_allow(cliente):
    r = cliente.post("/api/v1/health")
    assert r.status_code == 405
    assert r.json()["erro"]["codigo"] == "ERRO_HTTP"
    assert "GET" in r.headers["allow"]
