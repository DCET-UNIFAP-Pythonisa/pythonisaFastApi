def _erro(resposta):
    return resposta.json()["erro"]["codigo"]


def test_listar_linhas(api):
    r = api.get("/api/v1/linhas")
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.json()[0] == {
        "id": "linha-a",
        "codigo": None,
        "nome": "Linha A",
        "empresa": "Empresa X",
    }


def test_itinerario_da_linha(api):
    r = api.get("/api/v1/linhas/linha-a/paradas")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["linha"] == {"id": "linha-a", "nome": "Linha A"}
    assert [i["ordem"] for i in corpo["itinerario"]] == [1, 2, 3, 4]
    ultimo = corpo["itinerario"][3]
    assert ultimo["sentido"] == "volta"
    assert ultimo["minutos_programados"] == 12
    assert ultimo["parada"]["id"] == "p4"
    assert set(ultimo["parada"]) == {"id", "nome", "referencia", "latitude", "longitude"}


def test_itinerario_linha_inexistente(api):
    r = api.get("/api/v1/linhas/xyz/paradas")
    assert r.status_code == 404
    assert _erro(r) == "LINHA_NAO_ENCONTRADA"


def test_listar_paradas(api):
    r = api.get("/api/v1/paradas")
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_listar_paradas_por_linha(api):
    r = api.get("/api/v1/paradas", params={"id_linha": "linha-b"})
    assert {p["id"] for p in r.json()} == {"p5", "p3", "p2"}


def test_listar_paradas_linha_inexistente(api):
    r = api.get("/api/v1/paradas", params={"id_linha": "xyz"})
    assert r.status_code == 404
    assert _erro(r) == "LINHA_NAO_ENCONTRADA"


def test_parada_mais_proxima(api):
    r = api.get("/api/v1/paradas/proxima", params={"latitude": 0.0085, "longitude": -51.0085})
    assert r.status_code == 200
    assert r.json()["parada"]["id"] == "p3"
    assert 60 <= r.json()["distancia_metros"] <= 85


def test_parada_mais_proxima_coordenada_invalida(api):
    r = api.get("/api/v1/paradas/proxima", params={"latitude": 200, "longitude": 0})
    assert r.status_code == 422
    assert _erro(r) == "DADOS_INVALIDOS"


def test_parada_mais_proxima_sem_parametros(api):
    r = api.get("/api/v1/paradas/proxima")
    assert r.status_code == 422
    assert _erro(r) == "DADOS_INVALIDOS"


def test_linhas_da_parada(api):
    r = api.get("/api/v1/paradas/p3/linhas")
    assert r.status_code == 200
    assert [linha["id"] for linha in r.json()] == ["linha-a", "linha-b"]


def test_linhas_da_parada_inexistente(api):
    r = api.get("/api/v1/paradas/zzz/linhas")
    assert r.status_code == 404
    assert _erro(r) == "PARADA_NAO_ENCONTRADA"


def test_rota_inexistente_usa_formato_padrao(api):
    r = api.get("/rota-que-nao-existe")
    assert r.status_code == 404
    assert _erro(r) == "NAO_ENCONTRADO"


def test_parada_mais_proxima_sem_paradas_cadastradas(cliente):
    r = cliente.get("/api/v1/paradas/proxima", params={"latitude": 0, "longitude": -51})
    assert r.status_code == 404
    assert _erro(r) == "PARADA_NAO_ENCONTRADA"
