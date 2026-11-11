from datetime import time

import pytest

from pythonisa_api.db.models import RotaParada, Viagem

URL = "/api/v1/deteccoes"


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


def test_primeira_parada_cria_viagem(api):
    r = api.post(URL, json=_passagem("p1", "06:01"))
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["ordem_itinerario"] == 1
    assert corpo["id_viagem"] is not None
    assert corpo["origem"] == "simulado"


# Grade do seed mini: dia útil 06:00, 06:30, 07:00; sábado 06:00; domingo sem grade.
@pytest.mark.parametrize(
    "data, hora, esperado",
    [
        ("2026-11-09", "06:01", (time(6, 0), "util")),  # segunda-feira
        ("2026-11-09", "07:15", (time(7, 0), "util")),  # exatamente 15 min: ainda vale
        ("2026-11-09", "07:16", None),  # 16 min depois da última partida
        ("2026-11-14", "06:05", (time(6, 0), "sabado")),
        ("2026-11-15", "06:00", None),  # domingo não usa a grade de sábado
    ],
)
def test_viagem_ligada_ao_horario_mais_proximo(api, sessao, data, hora, esperado):
    r = api.post(URL, json=_passagem("p1", hora, data=data))
    assert r.status_code == 201
    assert _horario_da_viagem(sessao, r.json()["id_viagem"]) == esperado


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
    assert "timestamp_passagem" in r.json()["erro"]["mensagem"]


def test_id_viagem_inexistente(api):
    r = api.post(URL, json=_passagem("p2", "06:05", id_viagem="nao-existe"))
    assert r.status_code == 422
    assert r.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


def test_id_viagem_de_outra_linha(api):
    viagem_linha_b = api.post(URL, json=_passagem("p5", "06:01", id_linha="linha-b"))
    id_viagem = viagem_linha_b.json()["id_viagem"]
    r = api.post(URL, json=_passagem("p2", "06:05", id_viagem=id_viagem))
    assert r.status_code == 422
    assert r.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


def test_timestamp_em_utc_e_devolvido_no_horario_de_macapa(api):
    corpo = _passagem("p1", "06:01")
    corpo["timestamp_passagem"] = "2026-11-09T09:01:00Z"
    r = api.post(URL, json=corpo)
    assert r.json()["timestamp_passagem"] == "2026-11-09T06:01:00-03:00"


def test_parada_repetida_no_itinerario_usa_ordem_seguinte_da_viagem(api, sessao):
    # p2 aparece duas vezes no itinerário da linha-a: na ordem 2 (ida) e na ordem 5 (volta).
    sessao.add(RotaParada(id_linha="linha-a", ordem=5, id_parada="p2", sentido="volta"))
    sessao.commit()
    id_viagem = api.post(URL, json=_passagem("p1", "06:01")).json()["id_viagem"]

    def ordem(id_parada, hora):
        r = api.post(URL, json=_passagem(id_parada, hora, id_viagem=id_viagem))
        assert r.status_code == 201
        assert r.json()["id_viagem"] == id_viagem
        return r.json()["ordem_itinerario"]

    assert ordem("p2", "06:05") == 2  # primeira ocorrência depois da ordem 1
    assert ordem("p4", "06:15") == 4
    assert ordem("p2", "06:20") == 5  # depois da ordem 4, só resta a ocorrência da volta
