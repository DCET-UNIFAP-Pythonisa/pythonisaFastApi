from datetime import UTC, datetime

from pythonisa_api.tempo import para_aware, para_local_naive


def test_para_local_naive_converte_utc_para_belem():
    assert para_local_naive(datetime(2026, 11, 8, 12, 0, tzinfo=UTC)) == datetime(2026, 11, 8, 9, 0)


def test_para_local_naive_mantem_naive():
    assert para_local_naive(datetime(2026, 11, 8, 9, 0)) == datetime(2026, 11, 8, 9, 0)


def test_para_aware_anexa_offset_belem():
    assert para_aware(datetime(2026, 11, 8, 9, 0)).isoformat().endswith("-03:00")
