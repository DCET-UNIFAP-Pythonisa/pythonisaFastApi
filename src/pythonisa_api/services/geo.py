"""Cálculos geográficos simples."""

from math import asin, cos, radians, sin, sqrt

RAIO_TERRA_M = 6_371_000


def haversine_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta (grande círculo) entre dois pontos, em metros."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * RAIO_TERRA_M * asin(sqrt(a))
