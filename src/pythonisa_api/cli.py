"""Comandos de manutenção: `python -m pythonisa_api.cli <comando>`."""

import argparse
import sys

from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from pythonisa_api.config import Settings
from pythonisa_api.db.base import criar_engine, criar_fabrica_sessao, criar_tabelas
from pythonisa_api.seed.carregar import ErroSeed, carregar_seed


def _init_db(engine: Engine) -> int:
    criar_tabelas(engine)
    print(f"Tabelas criadas em {engine.url}")
    return 0


def _seed(engine: Engine) -> int:
    try:
        with criar_fabrica_sessao(engine)() as sessao:
            resumo = carregar_seed(sessao)
    except ErroSeed as erro:
        print(f"Erro no seed: {erro}", file=sys.stderr)
        return 1
    except OperationalError as erro:
        # Ex.: "no such table" (falta o init-db) ou "database is locked" (outro programa
        # com o banco aberto). Mostra a causa real em vez de adivinhar.
        print(
            f"Erro no banco: {erro.orig}. Se as tabelas ainda não existem, rode o init-db antes.",
            file=sys.stderr,
        )
        return 1
    print(
        f"Seed carregado: linhas={resumo.linhas} paradas={resumo.paradas} "
        f"itinerario={resumo.itens_itinerario} horarios={resumo.horarios} "
        f"padroes_letreiro={resumo.padroes}"
    )
    return 0


COMANDOS = {"init-db": _init_db, "seed": _seed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pythonisa_api.cli")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("init-db", help="cria as tabelas do banco")
    sub.add_parser("seed", help="carrega linhas, paradas, itinerários, grade e letreiros")
    args = parser.parse_args(argv)

    engine = criar_engine(Settings().database_url)
    try:
        return COMANDOS[args.comando](engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
