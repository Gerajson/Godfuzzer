"""Простой модуль обучения на паттернах найденных аномалий."""

from __future__ import annotations

from collections import Counter


class Learner:
    def __init__(self) -> None:
        self._patterns = Counter()

    def observe(self, anomalies: list[str]) -> None:
        self._patterns.update(anomalies)

    def recommend_scope_expansion(self) -> list[str]:
        recommendations: list[str] = []
        if self._patterns.get("LATENCY_SPIKE", 0) >= 3:
            recommendations.append("Добавить тесты на деградацию сети и таймауты")
        if self._patterns.get("NEGATIVE_BALANCE_DELTA", 0) >= 1:
            recommendations.append("Приоритизировать проверки консистентности баланса")
        if self._patterns.get("ABNORMAL_BALANCE_JUMP", 0) >= 1:
            recommendations.append("Проверить округления и BigInt во внутренних переводах")
        return recommendations
