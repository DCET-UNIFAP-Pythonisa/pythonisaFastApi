"""Comandos de manutenção: `python -m pythonisa_api.cli <comando>`."""

import argparse
import sys

from pythonisa_api.config import Settings
from pythonisa_api.db.base import criar_engine, criar_fabrica_sessao, criar_tabelas
from pythonisa_api.seed.carregar import ErroSeed, carregar_seed


def _init_db(settings: Settings) -> int:
    engine = criar_engine(settings.database_url)
    try:
        criar_tabelas(engine)
    finally:
        engine.dispose()
    print(f"Tabelas criadas em {settings.database_url}")
    return 0


def _seed(settings: Settings) -> int:
    engine = criar_engine(settings.database_url)
    try:
        with criar_fabrica_sessao(engine)() as sessao:
            resumo = carregar_seed(sessao)
    except ErroSeed as erro:
        print(f"Erro no seed: {erro}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    print(
        f"Seed carregado: linhas={resumo.linhas} paradas={resumo.paradas} "
        f"itinerario={resumo.itens_itinerario} horarios={resumo.horarios} "
        f"padroes_letreiro={resumo.padroes}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pythonisa_api.cli")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("init-db", help="cria as tabelas do banco")
    sub.add_parser("seed", help="carrega linhas, paradas, itinerários, grade e letreiros")

    args = parser.parse_args(argv)
    settings = Settings()
    if args.comando == "init-db":
        return _init_db(settings)
    if args.comando == "seed":
        return _seed(settings)
    return 1


if __name__ == "__main__":
    sys.exit(main())
