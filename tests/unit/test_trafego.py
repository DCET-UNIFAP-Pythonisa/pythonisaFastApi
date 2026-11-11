from datetime import time

import pytest

from pythonisa_api.simulador.historico import fator_dia, fator_horario


@pytest.mark.parametrize(
    "hora, esperado",
    [
        (time(6, 29), 0.85),
        (time(6, 30), 1.3),  # início do pico da manhã
        (time(7, 0), 1.3),
        (time(8, 30), 0.85),  # fim do pico (exclusivo)
        (time(12, 0), 1.3),
        (time(18, 0), 1.3),
        (time(10, 0), 0.85),
    ],
)
def test_fator_horario(hora, esperado):
    assert fator_horario(hora) == esperado


def test_fator_dia():
    assert (fator_dia("util"), fator_dia("sabado"), fator_dia("domingo")) == (1.0, 0.9, 0.8)
