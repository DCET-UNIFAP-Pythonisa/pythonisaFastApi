"""Contrato de GET /previsoes (spec, seção 12)."""

from datetime import datetime

from pydantic import BaseModel, field_serializer

from pythonisa_api.schemas.consulta import LinhaResumo
from pythonisa_api.tempo import para_aware


class ParadaResumo(BaseModel):
    id: str
    nome: str


class PrevisaoSaida(BaseModel):
    linha: LinhaResumo
    parada: ParadaResumo
    situacao: str
    horario_programado: datetime | None
    horario_previsto: datetime | None
    minutos_restantes: int | None
    diferenca_minutos: int | None
    versao_modelo: str | None
    gerado_em: datetime

    @field_serializer("horario_programado", "horario_previsto", "gerado_em")
    def _com_fuso(self, valor: datetime | None) -> str | None:
        return para_aware(valor).isoformat() if valor else None
