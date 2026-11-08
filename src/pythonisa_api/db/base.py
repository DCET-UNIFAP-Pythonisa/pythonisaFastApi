"""Engine, sessão e criação de tabelas (SQLAlchemy 2, síncrono)."""

from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def criar_engine(url: str) -> Engine:
    url_obj = make_url(url)
    eh_sqlite = url_obj.get_backend_name() == "sqlite"
    if eh_sqlite and url_obj.database and url_obj.database != ":memory:":
        Path(url_obj.database).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url)

    if eh_sqlite:
        # SQLite vem com chaves estrangeiras desligadas por padrão.
        @event.listens_for(engine, "connect")
        def _ligar_fk(conexao_dbapi, _registro):
            cursor = conexao_dbapi.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def criar_fabrica_sessao(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def criar_tabelas(engine: Engine) -> None:
    from pythonisa_api.db import models  # noqa: F401  (registra os modelos no metadata)

    Base.metadata.create_all(engine)
