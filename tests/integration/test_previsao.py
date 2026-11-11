URL = "/api/v1/previsoes"


def _prever(api, id_parada, agora, id_linha="linha-a"):
    params = {"id_linha": id_linha, "id_parada": id_parada}
    if agora is not None:
        params["agora"] = agora
    return api.get(URL, params=params)


def _erro(resposta):
    return resposta.json()["erro"]["codigo"]


# Seed mini, linha-a: dia útil 06:00, 06:30, 07:00; minutos programados p1..p4 = 0, 4, 8, 12.


def test_proxima_partida_ainda_por_vir(api):
    r = _prever(api, "p3", "2026-11-09T06:10:00-03:00")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["horario_programado"] == "2026-11-09T06:38:00-03:00"
    assert corpo["horario_previsto"] == "2026-11-09T06:38:00-03:00"
    assert corpo["minutos_restantes"] == 28
    assert corpo["diferenca_minutos"] == 0
    assert corpo["situacao"] == "no_horario"
    assert corpo["versao_modelo"] is None
    assert corpo["gerado_em"] == "2026-11-09T06:10:00-03:00"
    assert corpo["linha"] == {"id": "linha-a", "nome": "Linha A"}
    assert corpo["parada"]["id"] == "p3"


def test_agora_em_utc(api):
    em_utc = _prever(api, "p3", "2026-11-09T09:10:00Z").json()
    local = _prever(api, "p3", "2026-11-09T06:10:00-03:00").json()
    assert local["horario_programado"] == "2026-11-09T06:38:00-03:00"
    assert em_utc == local


def test_sabado_usa_grade_de_sabado(api):
    r = _prever(api, "p2", "2026-11-14T05:50:00-03:00")
    assert r.json()["horario_programado"] == "2026-11-14T06:04:00-03:00"


def test_sem_servico_depois_da_ultima_partida(api):
    corpo = _prever(api, "p3", "2026-11-09T07:30:00-03:00").json()
    assert corpo["situacao"] == "sem_servico"
    for campo in (
        "horario_programado",
        "horario_previsto",
        "minutos_restantes",
        "diferenca_minutos",
    ):
        assert corpo[campo] is None


def test_domingo_sem_grade(api):
    corpo = _prever(api, "p3", "2026-11-15T06:00:00-03:00").json()
    assert corpo["situacao"] == "sem_servico"


def test_parada_fora_da_linha(api):
    r = _prever(api, "p5", "2026-11-09T06:10:00-03:00")
    assert r.status_code == 422
    assert _erro(r) == "PARADA_FORA_DA_LINHA"


def test_linha_inexistente(api):
    r = _prever(api, "p3", "2026-11-09T06:10:00-03:00", id_linha="xyz")
    assert r.status_code == 404
    assert _erro(r) == "LINHA_NAO_ENCONTRADA"


def test_agora_sem_fuso(api):
    r = _prever(api, "p3", "2026-11-09T06:10:00")
    assert r.status_code == 422
    assert _erro(r) == "DADOS_INVALIDOS"


def test_sem_agora_usa_relogio(api):
    assert _prever(api, "p3", None).status_code == 200
