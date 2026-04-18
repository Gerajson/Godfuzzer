"""AsyncCore: управление жизненным циклом, обработка исключений и graceful shutdown."""

from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable


class AsyncCore:
    def __init__(self) -> None:
        self._stop_event = asyncio.Event()
        self._log = logging.getLogger(self.__class__.__name__)

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()

        def _request_stop() -> None:
            self._log.warning("Получен сигнал остановки")
            self._stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _request_stop)
            except NotImplementedError:
                self._log.warning("Signal handlers unsupported on this platform")

        def _loop_exception_handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
            self._log.error("Global loop exception", extra={"ctx_context": str(context)}, exc_info=context.get("exception"))

        loop.set_exception_handler(_loop_exception_handler)

    async def run(self, runner: Callable[[asyncio.Event], Awaitable[None]]) -> None:
        self._install_signal_handlers()
        await runner(self._stop_event)
