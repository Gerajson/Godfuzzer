"""Генератор модулей с проверкой синтаксиса и безопасным запуском."""

from __future__ import annotations

import ast
import concurrent.futures
import logging
from dataclasses import dataclass
from typing import Protocol


class StateLike(Protocol):
    async def upsert_generated_module(self, module_name: str, code: str, status: str) -> None: ...
    async def mark_module_crash(self, module_name: str, crash_limit: int = 3) -> str: ...


@dataclass(slots=True)
class GeneratedModule:
    name: str
    code: str


def _exec_module_code(code: str) -> str:
    namespace: dict[str, object] = {}
    exec(code, namespace, namespace)  # noqa: S102 - запускается в отдельном процессе
    runner = namespace.get("run")
    if callable(runner):
        return str(runner())
    return "NO_RUNNER"


class ModuleGenerator:
    def __init__(self, state: StateLike, module_timeout_sec: int = 10):
        self.state = state
        self.module_timeout_sec = module_timeout_sec
        self._log = logging.getLogger(self.__class__.__name__)

    def build_template(self, name: str, description: str) -> GeneratedModule:
        code = f'''"""Автогенерируемый безопасный модуль {name}."""

def run():
    # В шаблоне используется только безопасная симуляция без атакующей логики.
    return "MODULE_OK:{description}"
'''
        ast.parse(code)
        return GeneratedModule(name=name, code=code)

    async def persist(self, module: GeneratedModule) -> None:
        await self.state.upsert_generated_module(module.name, module.code, "active")

    async def run_isolated(self, module: GeneratedModule) -> str:
        with concurrent.futures.ProcessPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_exec_module_code, module.code)
            try:
                return future.result(timeout=self.module_timeout_sec)
            except Exception:
                self._log.exception("Generated module crashed", extra={"ctx_module": module.name})
                status = await self.state.mark_module_crash(module.name)
                raise RuntimeError(f"module_status={status}")
