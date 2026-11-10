import pytest

from pythonisa_api.services.geo import haversine_metros


def test_haversine_um_centesimo_de_grau_no_equador():
    assert haversine_metros(0, -51, 0, -51.009) == pytest.approx(1000.75, abs=0.5)


def test_haversine_mesmo_ponto_e_zero():
    assert haversine_metros(0.03, -51.06, 0.03, -51.06) == 0
