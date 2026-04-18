import asyncio

from cryptogodfuzzer.module_generator import ModuleGenerator


class DummyState:
    async def upsert_generated_module(self, *args, **kwargs):
        return None

    async def mark_module_crash(self, module_name: str, crash_limit: int = 3):
        return "active"


def test_module_build_and_run_isolated():
    async def _run():
        gen = ModuleGenerator(DummyState(), module_timeout_sec=2)
        module = gen.build_template("m1", "desc")
        result = await gen.run_isolated(module)
        assert result.startswith("MODULE_OK")

    asyncio.run(_run())
