"""Менеджер прокси: ротация, health-check и выбраковка."""

from __future__ import annotations

import asyncio
import logging
from collections import deque

from .request_engine import RequestEngine


class ProxyManager:
    def __init__(self, initial_proxies: list[str] | None = None):
        self._log = logging.getLogger(self.__class__.__name__)
        self._proxies = deque(initial_proxies or [])
        self._dead: set[str] = set()
        self._lock = asyncio.Lock()

    async def refresh_from_sources(self, engine: RequestEngine, sources: list[str]) -> None:
        for source in sources:
            try:
                status, body, _ = await engine.request("GET", source)
                if status != 200:
                    continue
                for line in body.decode(errors="ignore").splitlines():
                    candidate = line.strip()
                    if candidate and candidate not in self._dead:
                        self._proxies.append(candidate)
            except Exception:
                self._log.exception("Failed to refresh proxies", extra={"ctx_source": source})

    async def healthcheck(self, engine: RequestEngine, url: str) -> None:
        async with self._lock:
            current = list(self._proxies)
            self._proxies.clear()
        alive: list[str] = []
        for proxy in current:
            try:
                status, _, _ = await engine.request("GET", url, proxy=f"http://{proxy}")
                if status < 400:
                    alive.append(proxy)
                else:
                    self._dead.add(proxy)
            except Exception:
                self._log.exception("Proxy failed healthcheck", extra={"ctx_proxy": proxy})
                self._dead.add(proxy)
        async with self._lock:
            self._proxies.extend(alive)

    async def next_proxy(self) -> str | None:
        async with self._lock:
            if not self._proxies:
                return None
            proxy = self._proxies[0]
            self._proxies.rotate(-1)
            return proxy
