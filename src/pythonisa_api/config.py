"""Configuração da aplicação, lida de variáveis de ambiente ou do arquivo .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///data/pythonisa.db"
    cors_origins: list[str] = ["*"]
    caminho_modelo: str = "data/modelo.joblib"
