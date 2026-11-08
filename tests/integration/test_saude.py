def test_health_responde_ok(cliente):
    r = cliente.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "modelo_carregado": False}


def test_cors_liberado_para_origem_configurada(cliente):
    r = cliente.get("/api/v1/health", headers={"Origin": "http://localhost:5555"})
    assert r.headers["access-control-allow-origin"] in ("*", "http://localhost:5555")
