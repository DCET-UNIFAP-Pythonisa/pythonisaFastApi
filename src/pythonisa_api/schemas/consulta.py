"""Formato JSON das respostas de consulta (contrato com o app)."""

from pydantic import BaseModel


class LinhaSaida(BaseModel):
    id: str
    codigo: str | None
    nome: str
    empresa: str | None


class LinhaResumo(BaseModel):
    id: str
    nome: str


class ParadaSaida(BaseModel):
    id: str
    nome: str
    referencia: str | None
    latitude: float
    longitude: float


class ItemItinerario(BaseModel):
    ordem: int
    sentido: str
    minutos_programados: int
    parada: ParadaSaida


class ItinerarioSaida(BaseModel):
    linha: LinhaResumo
    itinerario: list[ItemItinerario]


class ParadaProximaSaida(BaseModel):
    parada: ParadaSaida
    distancia_metros: int
