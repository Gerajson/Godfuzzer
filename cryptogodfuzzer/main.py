"""Точка входа CryptoGodFuzzer (безопасный режим для авторизованного аудита)."""

from __future__ import annotations

import asyncio
import logging
import time

from .anomaly_detector import AnomalyDetector
from .async_core import AsyncCore
from .config import load_config
from .fuzzer import Fuzzer
from .learner import Learner
from .logging_utils import setup_logging
from .module_generator import ModuleGenerator
from .proxy_manager import ProxyManager
from .request_engine import RequestEngine
from .state_manager import StateManager


async def app_runner(stop_event: asyncio.Event, config_path: str = "config.yaml") -> None:
    cfg = load_config(config_path)
    setup_logging(cfg.log_level)
    log = logging.getLogger("main")

    state = StateManager(cfg.sqlite_path)
    await state.init()
    await state.set_state("last_start_ts", time.time())

    engine = RequestEngine(cfg)
    await engine.start()
    proxy_manager = ProxyManager()
    detector = AnomalyDetector()
    fuzzer = Fuzzer(cfg.limits.per_endpoint_tests)
    learner = Learner()
    generator = ModuleGenerator(state, cfg.modules.module_timeout_sec)

    try:
        if cfg.proxy.enabled and cfg.proxy.sources:
            await proxy_manager.refresh_from_sources(engine, [str(x) for x in cfg.proxy.sources])
            if cfg.proxy.healthcheck_url:
                await proxy_manager.healthcheck(engine, str(cfg.proxy.healthcheck_url))

        for target in cfg.scanner.targets:
            if stop_event.is_set():
                break
            status, body, _ = await engine.request("GET", str(target))
            anomalies = detector.detect(50, 50 + (len(body) % 800), 1.0, 1.0)
            learner.observe(anomalies)
            await state.set_state("last_target", str(target))
            if anomalies:
                await state.add_finding("baseline_probe", str(target), "INFO", {"anomalies": anomalies, "status": status})

            for payload in fuzzer.mutate({"sample": "value"}):
                if stop_event.is_set():
                    break
                await state.set_state("last_payload", payload)

        module = generator.build_template("generated_safety_module", "безопасная симуляция")
        await generator.persist(module)
        result = await generator.run_isolated(module)
        log.info("Generated module result", extra={"ctx_result": result})
        await state.set_state("recommendations", learner.recommend_scope_expansion())
    except Exception:
        log.exception("Fatal error in app_runner")
        raise
    finally:
        await engine.close()
        await state.set_state("last_stop_ts", time.time())


def main() -> None:
    core = AsyncCore()
    asyncio.run(core.run(lambda stop_event: app_runner(stop_event, "config.yaml")))


if __name__ == "__main__":
    main()
