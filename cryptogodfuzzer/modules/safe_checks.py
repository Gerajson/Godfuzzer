"""Набор безопасных проверок (без эксплуатации/вредоносных действий)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SafeCheckResult:
    module: str
    risk: str
    details: str


def websocket_resilience_check() -> SafeCheckResult:
    return SafeCheckResult(
        module="websocket_split_brain_sim",
        risk="MEDIUM",
        details="Только проверка reconnection/идемпотентности отмены ордеров в тестовой среде.",
    )


def cache_header_reflection_check() -> SafeCheckResult:
    return SafeCheckResult(
        module="cache_header_injection_check",
        risk="MEDIUM",
        details="Проверяется отражение заголовков в ответе и кэш-политика без poisoning-эксплуатации.",
    )


def precision_mismatch_check() -> SafeCheckResult:
    return SafeCheckResult(
        module="precision_mismatch_check",
        risk="HIGH",
        details="Сверка сумм в запросе/ответе для выявления ошибок округления.",
    )
