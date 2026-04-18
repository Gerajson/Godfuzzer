import textwrap

import pytest

from cryptogodfuzzer.config import load_config


def test_load_config_ok(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        textwrap.dedent(
            """
            log_level: DEBUG
            scanner:
              targets:
                - https://example.com/
            """
        ),
        encoding="utf-8",
    )
    cfg = load_config(cfg_file)
    assert cfg.log_level == "DEBUG"
    assert str(cfg.scanner.targets[0]).startswith("https://example.com")


def test_load_config_invalid(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("log_level: BAD\nscanner: {targets: ['https://example.com/']}\n", encoding="utf-8")
    with pytest.raises(Exception):
        load_config(cfg_file)
