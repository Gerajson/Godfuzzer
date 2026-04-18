"""Детектор аномалий по эвристикам с белыми списками."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AnomalyThresholds:
    latency_spike_ms: float = 500.0
    negative_balance_delta: float = -0.000001
    balance_jump_ratio: float = 1.5


class AnomalyDetector:
    def __init__(self, thresholds: AnomalyThresholds | None = None):
        self.thresholds = thresholds or AnomalyThresholds()

    def detect(
        self,
        baseline_latency_ms: float,
        current_latency_ms: float,
        before_balance: float,
        after_balance: float,
        legit_variations: set[str] | None = None,
        variation_tag: str | None = None,
    ) -> list[str]:
        anomalies: list[str] = []
        legit_variations = legit_variations or set()

        if variation_tag and variation_tag in legit_variations:
            return anomalies

        if current_latency_ms - baseline_latency_ms > self.thresholds.latency_spike_ms:
            anomalies.append("LATENCY_SPIKE")

        delta = after_balance - before_balance
        if delta < self.thresholds.negative_balance_delta:
            anomalies.append("NEGATIVE_BALANCE_DELTA")

        if before_balance > 0 and (after_balance / before_balance) > self.thresholds.balance_jump_ratio:
            anomalies.append("ABNORMAL_BALANCE_JUMP")

        return anomalies
