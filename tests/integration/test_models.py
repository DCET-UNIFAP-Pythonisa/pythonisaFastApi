import pytest
from sqlalchemy.exc import IntegrityError

from pythonisa_api.db.models import Linha, Parada, RegistroDeteccao, RotaParada


def _linha_e_paradas(sessao):
    sessao.add(Linha(id="linha-a", nome="Linha A"))
    for i in range(1, 4):
        sessao.add(Parada(id=f"p{i}", nome=f"Parada {i}", latitude=0.0, longitude=-51.0))
    sessao.flush()


def test_fk_ativa(sessao):
    sessao.add(Parada(id="p1", nome="P1", latitude=0.0, longitude=-51.0))
    sessao.add(RotaParada(id_linha="nao-existe", ordem=1, id_parada="p1", sentido="ida"))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_pk_rota_parada_linha_ordem(sessao):
    _linha_e_paradas(sessao)
    sessao.add(RotaParada(id_linha="linha-a", ordem=1, id_parada="p1", sentido="ida"))
    sessao.flush()
    sessao.add(RotaParada(id_linha="linha-a", ordem=1, id_parada="p2", sentido="ida"))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_mesma_parada_duas_vezes_na_linha_permitido(sessao):
    _linha_e_paradas(sessao)
    sessao.add(RotaParada(id_linha="linha-a", ordem=1, id_parada="p1", sentido="ida"))
    sessao.add(RotaParada(id_linha="linha-a", ordem=5, id_parada="p1", sentido="volta"))
    sessao.flush()


def test_sentido_invalido(sessao):
    _linha_e_paradas(sessao)
    sessao.add(RotaParada(id_linha="linha-a", ordem=1, id_parada="p1", sentido="norte"))
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_confianca_fora_do_intervalo(sessao):
    from datetime import datetime

    _linha_e_paradas(sessao)
    sessao.add(
        RegistroDeteccao(
            id_linha="linha-a",
            id_parada="p1",
            timestamp_passagem=datetime(2026, 11, 9, 6, 1),
            origem="ocr",
            confianca_ocr=1.5,
            recebido_em=datetime(2026, 11, 9, 6, 1),
        )
    )
    with pytest.raises(IntegrityError):
        sessao.flush()


def test_itinerario_ordenado(sessao):
    _linha_e_paradas(sessao)
    for ordem, parada in [(3, "p3"), (1, "p1"), (2, "p2")]:
        sessao.add(RotaParada(id_linha="linha-a", ordem=ordem, id_parada=parada, sentido="ida"))
    sessao.commit()
    sessao.expire_all()
    linha = sessao.get(Linha, "linha-a")
    assert [r.ordem for r in linha.itinerario] == [1, 2, 3]
