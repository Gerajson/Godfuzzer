"""Загрузка и строгая валидация конфигурации."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator


class RetryConfig(BaseModel):
    max_attempts: int = Field(default=5, ge=1, le=20)
    base_delay: float = Field(default=0.5, ge=0.05, le=30.0)
    max_delay: float = Field(default=20.0, ge=0.5, le=120.0)


class LimitsConfig(BaseModel):
    max_concurrency: int = Field(default=25, ge=1, le=500)
    max_response_bytes: int = Field(default=1_000_000, ge=1024, le=50_000_000)
    per_endpoint_tests: int = Field(default=50, ge=1, le=10_000)


class ProxyConfig(BaseModel):
    enabled: bool = False
    sources: list[HttpUrl] = Field(default_factory=list)
    healthcheck_url: HttpUrl | None = None


class ModuleConfig(BaseModel):
    enabled_modules: list[str] = Field(default_factory=list)
    module_timeout_sec: int = Field(default=10, ge=1, le=300)


class ScannerConfig(BaseModel):
    targets: list[HttpUrl]
    websocket_targets: list[HttpUrl] = Field(default_factory=list)


class AppConfig(BaseModel):
    log_level: str = "INFO"
    sqlite_path: str = "cryptogodfuzzer.db"
    retry: RetryConfig = Field(default_factory=RetryConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    modules: ModuleConfig = Field(default_factory=ModuleConfig)
    scanner: ScannerConfig

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"log_level должен быть одним из: {sorted(allowed)}")
        return upper


def load_config(path: str | Path) -> AppConfig:
    raw: dict[str, Any] = {}
    with Path(path).open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    try:
        return AppConfig.model_validate(raw)
    except ValidationError:
        raise
