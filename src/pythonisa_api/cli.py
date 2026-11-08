"""Comandos de manutenção: `python -m pythonisa_api.cli <comando>`."""

import argparse
import sys

from pythonisa_api.config import Settings
from pythonisa_api.db.base import criar_engine, criar_tabelas


def _init_db(settings: Settings) -> int:
    engine = criar_engine(settings.database_url)
    try:
        criar_tabelas(engine)
    finally:
        engine.dispose()
    print(f"Tabelas criadas em {settings.database_url}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pythonisa_api.cli")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("init-db", help="cria as tabelas do banco")

    args = parser.parse_args(argv)
    settings = Settings()
    if args.comando == "init-db":
        return _init_db(settings)
    return 1


if __name__ == "__main__":
    sys.exit(main())
