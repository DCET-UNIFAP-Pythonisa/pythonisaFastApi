"""Modelos ORM do MER revisado (spec, seção 3.2)."""

from datetime import date, datetime, time
from uuid import uuid4

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pythonisa_api.db.base import Base


def _novo_id() -> str:
    return uuid4().hex


class Linha(Base):
    __tablename__ = "linha"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    codigo: Mapped[str | None] = mapped_column(String(20))
    nome: Mapped[str] = mapped_column(String(120))
    empresa: Mapped[str | None] = mapped_column(String(120))
    ativa: Mapped[bool] = mapped_column(default=True)

    itinerario: Mapped[list["RotaParada"]] = relationship(
        order_by="RotaParada.ordem", cascade="all, delete-orphan"
    )


class PadraoLetreiro(Base):
    __tablename__ = "padrao_letreiro"
    __table_args__ = (UniqueConstraint("id_linha", "padrao"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    id_linha: Mapped[str] = mapped_column(ForeignKey("linha.id"))
    padrao: Mapped[str] = mapped_column(String(200))
    prioridade: Mapped[int] = mapped_column(default=0)


class Parada(Base):
    __tablename__ = "parada"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    referencia: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float]
    longitude: Mapped[float]


class RotaParada(Base):
    __tablename__ = "rota_parada"
    __table_args__ = (CheckConstraint("sentido IN ('ida', 'volta')", name="ck_rota_sentido"),)

    id_linha: Mapped[str] = mapped_column(ForeignKey("linha.id"), primary_key=True)
    ordem: Mapped[int] = mapped_column(primary_key=True)
    id_parada: Mapped[str] = mapped_column(ForeignKey("parada.id"))
    sentido: Mapped[str] = mapped_column(String(5))
    minutos_programados: Mapped[int] = mapped_column(default=0)

    # selectin: carrega as paradas do itinerário numa consulta só (evita uma consulta por item).
    parada: Mapped[Parada] = relationship(lazy="selectin")


class HorarioProgramado(Base):
    __tablename__ = "horario_programado"
    __table_args__ = (
        UniqueConstraint("id_linha", "tipo_dia", "hora_partida"),
        CheckConstraint("tipo_dia IN ('util', 'sabado', 'domingo')", name="ck_horario_tipo_dia"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    id_linha: Mapped[str] = mapped_column(ForeignKey("linha.id"))
    hora_partida: Mapped[time]
    tipo_dia: Mapped[str] = mapped_column(String(7))


class Viagem(Base):
    __tablename__ = "viagem"
    __table_args__ = (CheckConstraint("origem IN ('simulado', 'ocr')", name="ck_viagem_origem"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_novo_id)
    id_linha: Mapped[str] = mapped_column(ForeignKey("linha.id"))
    id_horario: Mapped[int | None] = mapped_column(ForeignKey("horario_programado.id"))
    data: Mapped[date]
    origem: Mapped[str] = mapped_column(String(8))

    horario: Mapped[HorarioProgramado | None] = relationship()


class RegistroDeteccao(Base):
    __tablename__ = "registro_deteccao"
    __table_args__ = (
        CheckConstraint("origem IN ('simulado', 'ocr')", name="ck_registro_origem"),
        CheckConstraint(
            "confianca_ocr IS NULL OR (confianca_ocr >= 0 AND confianca_ocr <= 1)",
            name="ck_registro_confianca",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_novo_id)
    id_linha: Mapped[str] = mapped_column(ForeignKey("linha.id"))
    id_parada: Mapped[str] = mapped_column(ForeignKey("parada.id"))
    id_viagem: Mapped[str | None] = mapped_column(ForeignKey("viagem.id"), index=True)
    ordem_itinerario: Mapped[int | None]
    timestamp_passagem: Mapped[datetime] = mapped_column(index=True)
    origem: Mapped[str] = mapped_column(String(8))
    texto_letreiro: Mapped[str | None] = mapped_column(String(200))
    confianca_ocr: Mapped[float | None]
    recebido_em: Mapped[datetime]


class PrevisaoViagem(Base):
    __tablename__ = "previsao_viagem"
    __table_args__ = (
        CheckConstraint("fonte IN ('deteccao', 'programado')", name="ck_previsao_fonte"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_novo_id)
    id_registro_origem: Mapped[str | None] = mapped_column(ForeignKey("registro_deteccao.id"))
    id_linha: Mapped[str] = mapped_column(ForeignKey("linha.id"))
    id_parada_destino: Mapped[str] = mapped_column(ForeignKey("parada.id"))
    fonte: Mapped[str] = mapped_column(String(10))
    horario_programado: Mapped[datetime | None]
    horario_estimado_chegada: Mapped[datetime]
    minutos_restantes: Mapped[int]
    versao_modelo: Mapped[str] = mapped_column(String(80))
    criado_em: Mapped[datetime]
