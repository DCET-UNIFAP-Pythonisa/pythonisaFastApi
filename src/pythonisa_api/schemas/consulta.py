"""Formato JSON das respostas de consulta (contrato com o app)."""

from pydantic import BaseModel, ConfigDict


class _DoOrm(BaseModel):
    # Permite criar o schema direto de um objeto do SQLAlchemy (model_validate(linha)).
    model_config = ConfigDict(from_attributes=True)


class LinhaSaida(_DoOrm):
    id: str
    codigo: str | None
    nome: str
    empresa: str | None


class LinhaResumo(_DoOrm):
    id: str
    nome: str


class ParadaSaida(_DoOrm):
    id: str
    nome: str
    referencia: str | None
    latitude: float
    longitude: float


class ItemItinerario(_DoOrm):
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
