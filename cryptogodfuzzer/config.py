"""Загрузка и строгая валидация конфигурации без тяжёлых бинарных зависимостей."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _is_valid_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https", "ws", "wss"} and bool(parsed.netloc)
    except Exception:
        return False


def _to_float(value: Any, name: str) -> float:
    try:
        return float(value)
    except Exception as exc:
        raise ValueError(f"{name}: ожидается число") from exc


def _to_int(value: Any, name: str) -> int:
    try:
        return int(value)
    except Exception as exc:
        raise ValueError(f"{name}: ожидается целое число") from exc


@dataclass(slots=True)
class RetryConfig:
    max_attempts: int = 5
    base_delay: float = 0.5
    max_delay: float = 20.0

    def validate(self) -> None:
        self.max_attempts = _to_int(self.max_attempts, "retry.max_attempts")
        self.base_delay = _to_float(self.base_delay, "retry.base_delay")
        self.max_delay = _to_float(self.max_delay, "retry.max_delay")
        if not (1 <= self.max_attempts <= 20):
            raise ValueError("retry.max_attempts должен быть в диапазоне [1,20]")
        if not (0.05 <= self.base_delay <= 30.0):
            raise ValueError("retry.base_delay должен быть в диапазоне [0.05,30.0]")
        if not (0.5 <= self.max_delay <= 120.0):
            raise ValueError("retry.max_delay должен быть в диапазоне [0.5,120.0]")


@dataclass(slots=True)
class LimitsConfig:
    max_concurrency: int = 25
    max_response_bytes: int = 1_000_000
    per_endpoint_tests: int = 50

    def validate(self) -> None:
        self.max_concurrency = _to_int(self.max_concurrency, "limits.max_concurrency")
        self.max_response_bytes = _to_int(self.max_response_bytes, "limits.max_response_bytes")
        self.per_endpoint_tests = _to_int(self.per_endpoint_tests, "limits.per_endpoint_tests")
        if not (1 <= self.max_concurrency <= 500):
            raise ValueError("limits.max_concurrency должен быть в диапазоне [1,500]")
        if not (1024 <= self.max_response_bytes <= 50_000_000):
            raise ValueError("limits.max_response_bytes должен быть в диапазоне [1024,50000000]")
        if not (1 <= self.per_endpoint_tests <= 10_000):
            raise ValueError("limits.per_endpoint_tests должен быть в диапазоне [1,10000]")


@dataclass(slots=True)
class ProxyConfig:
    enabled: bool = False
    sources: list[str] = field(default_factory=list)
    healthcheck_url: str | None = None

    def validate(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("proxy.enabled должен быть bool")
        for src in self.sources:
            if not _is_valid_http_url(src):
                raise ValueError(f"proxy.sources содержит невалидный URL: {src}")
        if self.healthcheck_url and not _is_valid_http_url(self.healthcheck_url):
            raise ValueError("proxy.healthcheck_url невалидный URL")


@dataclass(slots=True)
class ModuleConfig:
    enabled_modules: list[str] = field(default_factory=list)
    module_timeout_sec: int = 10

    def validate(self) -> None:
        self.module_timeout_sec = _to_int(self.module_timeout_sec, "modules.module_timeout_sec")
        if not (1 <= self.module_timeout_sec <= 300):
            raise ValueError("modules.module_timeout_sec должен быть в диапазоне [1,300]")


@dataclass(slots=True)
class ScannerConfig:
    targets: list[str]
    websocket_targets: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.targets:
            raise ValueError("scanner.targets не должен быть пустым")
        for url in self.targets:
            if not _is_valid_http_url(url):
                raise ValueError(f"scanner.targets содержит невалидный URL: {url}")
        for url in self.websocket_targets:
            if not _is_valid_http_url(url):
                raise ValueError(f"scanner.websocket_targets содержит невалидный URL: {url}")


@dataclass(slots=True)
class AppConfig:
    log_level: str = "INFO"
    sqlite_path: str = "cryptogodfuzzer.db"
    retry: RetryConfig = field(default_factory=RetryConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    modules: ModuleConfig = field(default_factory=ModuleConfig)
    scanner: ScannerConfig | None = None

    def validate(self) -> None:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        self.log_level = str(self.log_level).upper()
        if self.log_level not in allowed:
            raise ValueError(f"log_level должен быть одним из: {sorted(allowed)}")
        if not self.scanner:
            raise ValueError("scanner обязателен")
        self.retry.validate()
        self.limits.validate()
        self.proxy.validate()
        self.modules.validate()
        self.scanner.validate()


def _parse_value(raw: str) -> Any:
    value = raw.strip()
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _load_minimal_yaml(text: str) -> dict[str, Any]:
    # Минимальный парсер YAML-подмножества: словари/списки/скаляры по отступам.
    lines = [ln.rstrip("\n") for ln in text.splitlines()]
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError("Некорректная структура списка в YAML")
            parent.append(_parse_value(content[2:]))
            continue

        if ":" not in content:
            raise ValueError(f"Некорректная YAML-строка: {content}")

        key, raw_value = content.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if raw_value == "":
            lookahead = ""
            j = i
            while j < len(lines):
                la = lines[j].strip()
                if la and not la.startswith("#"):
                    lookahead = la
                    break
                j += 1
            new_container: Any = [] if lookahead.startswith("- ") else {}
            if isinstance(parent, dict):
                parent[key] = new_container
            else:
                raise ValueError("Ожидался словарь для вложенного ключа")
            stack.append((indent, new_container))
        else:
            if isinstance(parent, dict):
                parent[key] = _parse_value(raw_value)
            else:
                raise ValueError("Ожидался словарь для scalar key:value")

    return root


def load_config(path: str | Path) -> AppConfig:
    raw_text = Path(path).read_text(encoding="utf-8")
    data = _load_minimal_yaml(raw_text)

    retry = RetryConfig(**(data.get("retry") or {}))
    limits = LimitsConfig(**(data.get("limits") or {}))
    proxy = ProxyConfig(**(data.get("proxy") or {}))
    modules = ModuleConfig(**(data.get("modules") or {}))
    scanner_raw = data.get("scanner") or {}
    scanner = ScannerConfig(
        targets=list(scanner_raw.get("targets") or []),
        websocket_targets=list(scanner_raw.get("websocket_targets") or []),
    )
    cfg = AppConfig(
        log_level=data.get("log_level", "INFO"),
        sqlite_path=data.get("sqlite_path", "cryptogodfuzzer.db"),
        retry=retry,
        limits=limits,
        proxy=proxy,
        modules=modules,
        scanner=scanner,
    )
    cfg.validate()
    return cfg
