from datetime import date

from sqlalchemy import func, select

from pythonisa_api import cli
from pythonisa_api.db.models import RegistroDeteccao, Viagem
from pythonisa_api.simulador.historico import simular_historico

# Segunda 2026-11-09 e terça 2026-11-10: 3 partidas por linha;
# linha-a tem 4 paradas e linha-b 3 → (3×4 + 3×3) × 2 dias = 42 passagens.
ATE, DIAS = date(2026, 11, 11), 2


def _contar(sessao, modelo):
    return sessao.scalar(select(func.count()).select_from(modelo))


def test_grava_uma_passagem_por_parada_de_cada_viagem(sessao_com_seed_mini):
    sessao = sessao_com_seed_mini
    assert simular_historico(sessao, ate=ATE, dias=DIAS) == 42
    assert _contar(sessao, RegistroDeteccao) == 42
    assert _contar(sessao, Viagem) == 12


def test_viagens_em_ordem_e_ligadas_a_grade(sessao_com_seed_mini):
    sessao = sessao_com_seed_mini
    simular_historico(sessao, ate=ATE, dias=DIAS)
    for viagem in sessao.scalars(select(Viagem)):
        assert viagem.id_horario is not None
        assert viagem.origem == "simulado"
        registros = sessao.scalars(
            select(RegistroDeteccao)
            .where(RegistroDeteccao.id_viagem == viagem.id)
            .order_by(RegistroDeteccao.ordem_itinerario)
        ).all()
        assert [r.ordem_itinerario for r in registros] == list(range(1, len(registros) + 1))
        horarios = [r.timestamp_passagem for r in registros]
        assert horarios == sorted(horarios)
        assert all(r.origem == "simulado" for r in registros)


def test_rodar_de_novo_nao_duplica(sessao_com_seed_mini):
    sessao = sessao_com_seed_mini
    simular_historico(sessao, ate=ATE, dias=DIAS)
    assert simular_historico(sessao, ate=ATE, dias=DIAS) == 0
    assert _contar(sessao, RegistroDeteccao) == 42


def test_cli_simular_historico(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    assert cli.main(["init-db"]) == 0
    assert cli.main(["seed"]) == 0
    assert cli.main(["simular-historico", "--dias", "1"]) == 0
    assert "Histórico simulado" in capsys.readouterr().out
