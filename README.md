# CryptoGodFuzzer (Safe Authorized Audit Edition)

> Важно: этот проект реализует **безопасный** каркас для авторизованного аудита отказоустойчивости и логики.
> Активная эксплуатация уязвимостей и вредоносные сценарии намеренно не реализованы.

## Быстрый запуск (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m cryptogodfuzzer.main
```

## Быстрый запуск (Linux/macOS bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m cryptogodfuzzer.main
```

## Совместимость по Python

- Рекомендуется Python **3.11–3.13**.
- Python 3.14 может требовать новее версии библиотек, если у пакетов ещё нет готовых wheel.

## Что есть внутри

- AsyncCore с graceful shutdown и глобальным exception handler.
- RequestEngine на aiohttp с retry + exponential backoff.
- ProxyManager с health-check и выбраковкой мёртвых прокси.
- StateManager на SQLite (`scan_state`, `findings`, `generated_modules`).
- ModuleGenerator с `ast.parse()` и запуском в `ProcessPoolExecutor` с таймаутом.
- Базовые pytest автотесты.

## Надёжность

Проект рассчитан на слабый VPS и нестабильную сеть: есть ретраи, лимиты соединений, лимит размера ответов, полное логирование исключений с трассировкой и сохранение прогресса.

## Download marker

- Commit prepared for direct ZIP download by commit hash.
