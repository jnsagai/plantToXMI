from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_script() -> ModuleType:
    script = Path(__file__).resolve().parents[1] / "scripts" / "ea_visual_confirm.py"
    spec = importlib.util.spec_from_file_location("ea_visual_confirm", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["ea_visual_confirm"] = module
    spec.loader.exec_module(module)
    return module


def test_message_order_uses_trailing_number() -> None:
    module = _load_script()

    assert module._message_order("publish 1") == 1
    assert module._message_order("authorize 12") == 12
    assert module._message_order("no number") == 999_999


def test_import_success_accepts_empty_or_guid() -> None:
    module = _load_script()

    assert module._is_import_success("")
    assert module._is_import_success("{4B83F762-0A05-4142-BA5A-BD00E7526378}")
    assert not module._is_import_success("Package import caused error: broken")
