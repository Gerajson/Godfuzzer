"""SQLite-хранилище состояния сканирования."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiosqlite


class StateManager:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._log = logging.getLogger(self.__class__.__name__)

    async def init(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS scan_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT NOT NULL,
                    target TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS generated_modules (
                    module_name TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    crash_count INTEGER NOT NULL DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            await db.commit()

    async def set_state(self, key: str, value: Any) -> None:
        encoded = json.dumps(value, ensure_ascii=False)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO scan_state(key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                (key, encoded),
            )
            await db.commit()

    async def get_state(self, key: str, default: Any = None) -> Any:
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute("SELECT value FROM scan_state WHERE key = ?", (key,))
            row = await cur.fetchone()
        return json.loads(row[0]) if row else default

    async def add_finding(self, module_name: str, target: str, severity: str, details: dict[str, Any]) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO findings(module_name, target, severity, details) VALUES (?, ?, ?, ?)",
                (module_name, target, severity, json.dumps(details, ensure_ascii=False)),
            )
            await db.commit()

    async def upsert_generated_module(self, module_name: str, code: str, status: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO generated_modules(module_name, code, status, crash_count, updated_at)
                VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
                ON CONFLICT(module_name)
                DO UPDATE SET code = excluded.code, status = excluded.status, updated_at = CURRENT_TIMESTAMP
                """,
                (module_name, code, status),
            )
            await db.commit()

    async def mark_module_crash(self, module_name: str, crash_limit: int = 3) -> str:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO generated_modules(module_name, code, status, crash_count, updated_at)
                VALUES (?, '', 'active', 1, CURRENT_TIMESTAMP)
                ON CONFLICT(module_name)
                DO UPDATE SET crash_count = crash_count + 1, updated_at = CURRENT_TIMESTAMP
                """,
                (module_name,),
            )
            cur = await db.execute("SELECT crash_count FROM generated_modules WHERE module_name = ?", (module_name,))
            crash_count = (await cur.fetchone())[0]
            status = "broken" if crash_count >= crash_limit else "active"
            await db.execute(
                "UPDATE generated_modules SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE module_name = ?",
                (status, module_name),
            )
            await db.commit()
        self._log.warning("Module crash tracked", extra={"ctx_module": module_name, "ctx_status": status})
        return status
