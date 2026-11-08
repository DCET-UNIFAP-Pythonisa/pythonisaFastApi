"""Convenções de tempo.

Todo datetime é persistido como *naive em horário local* de Macapá (America/Belem,
UTC-3 fixo, sem horário de verão). A conversão para datetime com offset acontece
apenas na borda da API.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Belem")


def para_local_naive(dt: datetime) -> datetime:
    """Datetime aware → horário local sem tz. Naive é considerado já local."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(FUSO).replace(tzinfo=None)


def para_aware(dt: datetime) -> datetime:
    """Datetime naive local → datetime com offset -03:00."""
    return dt.replace(tzinfo=FUSO)


def agora_local() -> datetime:
    return datetime.now(FUSO).replace(tzinfo=None)
