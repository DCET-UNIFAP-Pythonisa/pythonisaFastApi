from sqlalchemy import create_engine, inspect

from pythonisa_api import cli

TABELAS = {
    "linha",
    "padrao_letreiro",
    "parada",
    "rota_parada",
    "horario_programado",
    "viagem",
    "registro_deteccao",
    "previsao_viagem",
}


def test_init_db_cria_tabelas(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'sub' / 'cli.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    assert cli.main(["init-db"]) == 0
    engine = create_engine(url)
    try:
        assert TABELAS <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_seed_carrega_os_dados(tmp_path, monkeypatch, capsys):
    url = f"sqlite:///{tmp_path / 'cli.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    assert cli.main(["init-db"]) == 0
    assert cli.main(["seed"]) == 0
    saida = capsys.readouterr().out
    assert "Seed carregado" in saida
    engine = create_engine(url)
    try:
        with engine.connect() as conexao:
            total = conexao.exec_driver_sql("SELECT COUNT(*) FROM linha").scalar()
        assert total > 0
    finally:
        engine.dispose()


def test_seed_sem_init_db_mostra_erro(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'vazio.db'}")
    assert cli.main(["seed"]) == 1
    assert "init-db" in capsys.readouterr().err
