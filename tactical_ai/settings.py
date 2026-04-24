"""Configuración cargada desde variables de entorno (pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "production", "test"] = Field(
        default="development",
        validation_alias="ENVIRONMENT",
    )
    cors_origins: str = Field(
        default="",
        description="Orígenes CORS separados por coma; vacío en dev permite *",
        validation_alias="CORS_ORIGINS",
    )
    api_keys: str = Field(
        default="",
        description="Claves API separadas por coma (Authorization: Bearer <key> o X-API-Key)",
        validation_alias="TACTICAL_AI_API_KEYS",
    )
    enable_mobile_ws_routes: bool = Field(
        default=False,
        validation_alias="ENABLE_MOBILE_WS_ROUTES",
    )
    enable_game_intelligence: bool = Field(
        default=False,
        validation_alias="ENABLE_GAME_INTELLIGENCE",
    )
    rate_limit_default: str = Field(
        default="120/minute",
        validation_alias="RATE_LIMIT_DEFAULT",
    )
    max_json_body_bytes: int = Field(
        default=1_048_576,
        validation_alias="MAX_JSON_BODY_BYTES",
        description="Tamaño máximo aproximado del cuerpo JSON (1 MiB)",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw:
            return []
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def api_key_list(self) -> list[str]:
        raw = self.api_keys.strip()
        if not raw:
            return []
        return [k.strip() for k in raw.split(",") if k.strip()]

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_env(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower().strip()
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
