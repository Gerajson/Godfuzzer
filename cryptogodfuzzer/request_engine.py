"""Надёжный сетевой движок с retry, лимитами и поддержкой WebSocket."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import AsyncIterator

import aiohttp

from .config import AppConfig


class RequestEngine:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self._log = logging.getLogger(self.__class__.__name__)
        self._session: aiohttp.ClientSession | None = None
        self._sem = asyncio.Semaphore(cfg.limits.max_concurrency)

    async def start(self) -> None:
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=self.cfg.limits.max_concurrency, ssl=False)
        self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)

    async def close(self) -> None:
        if self._session:
            await self._session.close()

    async def request(self, method: str, url: str, **kwargs) -> tuple[int, bytes, dict[str, str]]:
        if not self._session:
            raise RuntimeError("RequestEngine не запущен")

        for attempt in range(1, self.cfg.retry.max_attempts + 1):
            try:
                async with self._sem:
                    async with self._session.request(method, url, **kwargs) as resp:
                        raw = await resp.content.read(self.cfg.limits.max_response_bytes + 1)
                        if len(raw) > self.cfg.limits.max_response_bytes:
                            raise ValueError("Размер ответа превысил лимит")
                        if resp.status in {429, 500, 502, 503, 504}:
                            raise aiohttp.ClientResponseError(
                                request_info=resp.request_info,
                                history=tuple(resp.history),
                                status=resp.status,
                                message="Retryable status",
                            )
                        return resp.status, raw, dict(resp.headers)
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                self._log.exception(
                    "Request failed",
                    extra={"ctx_url": url, "ctx_attempt": attempt},
                )
                if attempt >= self.cfg.retry.max_attempts:
                    raise
                delay = min(
                    self.cfg.retry.max_delay,
                    self.cfg.retry.base_delay * (2 ** (attempt - 1)) + random.random() * 0.2,
                )
                await asyncio.sleep(delay)
        raise RuntimeError("Недостижимое состояние retry")

    async def ws_stream(self, url: str, payload: dict | None = None) -> AsyncIterator[aiohttp.WSMessage]:
        if not self._session:
            raise RuntimeError("RequestEngine не запущен")
        while True:
            try:
                async with self._session.ws_connect(url, heartbeat=20, receive_timeout=30) as ws:
                    if payload:
                        await ws.send_json(payload)
                    async for msg in ws:
                        yield msg
                    self._log.warning("WS stream closed", extra={"ctx_url": url})
            except (aiohttp.ClientError, asyncio.TimeoutError):
                self._log.exception("WS error, reconnecting", extra={"ctx_url": url})
                await asyncio.sleep(1.5)
