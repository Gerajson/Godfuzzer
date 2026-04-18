"""Фаззер параметров с ограничениями по числу тестов."""

from __future__ import annotations

import itertools


class Fuzzer:
    def __init__(self, per_endpoint_tests: int = 50):
        self.per_endpoint_tests = per_endpoint_tests

    def mutate(self, base: dict[str, str]) -> list[dict[str, str]]:
        seeds = {
            "": "",
            "long": "A" * 1024,
            "unicode": "тест🔥",
            "sql": "' OR '1'='1",
            "xml": "<!DOCTYPE x [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>",
            "float": "1.00000099",
            "neg": "-1",
        }
        mutated: list[dict[str, str]] = []
        for key, value in base.items():
            for _, payload in seeds.items():
                candidate = dict(base)
                candidate[key] = payload if payload else value
                mutated.append(candidate)
                if len(mutated) >= self.per_endpoint_tests:
                    return mutated
        return mutated

    def endpoint_plan(self, endpoints: list[str]) -> list[tuple[str, int]]:
        return list(itertools.islice(((ep, self.per_endpoint_tests) for ep in endpoints), len(endpoints)))
