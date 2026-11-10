"""Cálculos geográficos simples."""

from collections.abc import Sequence
from math import asin, cos, radians, sin, sqrt

from pythonisa_api.db.models import Parada
from pythonisa_api.erros import NenhumaParadaCadastrada

RAIO_TERRA_M = 6_371_000


def haversine_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta (grande círculo) entre dois pontos, em metros."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * RAIO_TERRA_M * asin(sqrt(a))


def parada_mais_proxima(
    paradas: Sequence[Parada], latitude: float, longitude: float
) -> tuple[Parada, float]:
    """Devolve (parada, distância em metros) da parada mais próxima do ponto."""
    if not paradas:
        raise NenhumaParadaCadastrada()
    distancias = (
        (parada, haversine_metros(latitude, longitude, parada.latitude, parada.longitude))
        for parada in paradas
    )
    return min(distancias, key=lambda par: par[1])
