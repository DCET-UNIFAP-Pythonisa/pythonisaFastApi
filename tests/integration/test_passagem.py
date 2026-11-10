from datetime import time

import pytest

from pythonisa_api.db.models import Viagem

URL = "/api/v1/deteccoes"


@pytest.fixture
def api(cliente, sessao_com_seed_mini):
    return cliente


def _passagem(id_parada, horario, data="2026-11-09", **extra):
    return {
        "id_linha": "linha-a",
        "id_parada": id_parada,
        "timestamp_passagem": f"{data}T{horario}:00-03:00",
        **extra,
    }


def _horario_da_viagem(sessao, id_viagem):
    viagem = sessao.get(Viagem, id_viagem)
    return (viagem.horario.hora_partida, viagem.horario.tipo_dia) if viagem.horario else None


def test_primeira_parada_cria_viagem_ligada_ao_horario(api, sessao):
    r = api.post(URL, json=_passagem("p1", "06:01"))
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["ordem_itinerario"] == 1
    assert corpo["id_viagem"] is not None
    assert corpo["origem"] == "simulado"
    assert _horario_da_viagem(sessao, corpo["id_viagem"]) == (time(6, 0), "util")


def test_primeira_parada_fora_da_grade_cria_viagem_sem_horario(api, sessao):
    r = api.post(URL, json=_passagem("p1", "08:00"))
    assert r.status_code == 201
    assert _horario_da_viagem(sessao, r.json()["id_viagem"]) is None


def test_sabado_usa_grade_de_sabado(api, sessao):
    r = api.post(URL, json=_passagem("p1", "06:05", data="2026-11-14"))
    assert _horario_da_viagem(sessao, r.json()["id_viagem"]) == (time(6, 0), "sabado")


def test_parada_seguinte_com_id_viagem(api):
    id_viagem = api.post(URL, json=_passagem("p1", "06:01")).json()["id_viagem"]
    r = api.post(URL, json=_passagem("p2", "06:05", id_viagem=id_viagem))
    assert r.status_code == 201
    assert r.json()["id_viagem"] == id_viagem
    assert r.json()["ordem_itinerario"] == 2


def test_parada_seguinte_sem_id_viagem(api):
    r = api.post(URL, json=_passagem("p2", "06:05"))
    assert r.status_code == 201
    assert r.json()["id_viagem"] is None
    assert r.json()["ordem_itinerario"] == 2


def test_parada_fora_da_linha(api):
    r = api.post(URL, json=_passagem("p5", "06:05"))
    assert r.status_code == 422
    assert r.json()["erro"]["codigo"] == "PARADA_FORA_DA_LINHA"


def test_linha_inexistente(api):
    r = api.post(URL, json=_passagem("p1", "06:01", id_linha="xyz"))
    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "LINHA_NAO_ENCONTRADA"


def test_parada_inexistente(api):
    r = api.post(URL, json=_passagem("zzz", "06:01"))
    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "PARADA_NAO_ENCONTRADA"


def test_timestamp_sem_fuso_rejeitado(api):
    corpo = _passagem("p1", "06:01")
    corpo["timestamp_passagem"] = "2026-11-09T06:01:00"
    r = api.post(URL, json=corpo)
    assert r.status_code == 422
    assert r.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


def test_id_viagem_inexistente(api):
    r = api.post(URL, json=_passagem("p2", "06:05", id_viagem="nao-existe"))
    assert r.status_code == 422
    assert r.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


def test_timestamp_em_utc_e_devolvido_no_horario_de_macapa(api):
    corpo = _passagem("p1", "06:01")
    corpo["timestamp_passagem"] = "2026-11-09T09:01:00Z"
    r = api.post(URL, json=corpo)
    assert r.json()["timestamp_passagem"] == "2026-11-09T06:01:00-03:00"
