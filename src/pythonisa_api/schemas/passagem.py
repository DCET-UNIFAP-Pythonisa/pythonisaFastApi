"""Contrato de POST /deteccoes: registro de passagem de um ônibus por uma parada."""

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_serializer

from pythonisa_api.tempo import para_aware


class PassagemEntrada(BaseModel):
    id_linha: str
    id_parada: str
    timestamp_passagem: AwareDatetime  # exige fuso (ex.: -03:00 ou Z)
    origem: Literal["simulado", "ocr"] = "simulado"
    id_viagem: str | None = None
    # Guardados para a futura integração com a Visão Computacional (sem regra no MVP).
    texto_letreiro: str | None = Field(default=None, max_length=200)
    confianca_ocr: float | None = Field(default=None, ge=0, le=1)


class PassagemSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    id_linha: str
    id_parada: str
    id_viagem: str | None
    ordem_itinerario: int | None
    timestamp_passagem: datetime
    origem: str

    @field_serializer("timestamp_passagem")
    def _com_fuso(self, valor: datetime) -> str:
        return para_aware(valor).isoformat()
