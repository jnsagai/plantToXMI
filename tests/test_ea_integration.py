from __future__ import annotations

import os
import platform
from pathlib import Path

import pytest

from planttoxmi import convert_plantuml
from planttoxmi.validation.ea_validator import EaValidationConfig, validate_with_ea

pytestmark = pytest.mark.ea


@pytest.mark.skipif(platform.system() != "Windows", reason="EA automation requires Windows")
@pytest.mark.skipif(os.getenv("PLANTTOXMI_RUN_EA_TESTS") != "1", reason="EA tests are opt-in")
def test_ea_imports_generated_component_sample(tmp_path: Path) -> None:
    template = os.getenv("PLANTTOXMI_EA_TEMPLATE")
    if not template or not Path(template).exists():
        pytest.skip("PLANTTOXMI_EA_TEMPLATE must point to a blank EA repository")

    conversion = convert_plantuml("@startuml\n[A] --> [B]\n@enduml\n", profile="ea")
    xmi = tmp_path / "component.xmi"
    xmi.write_text(conversion.xmi, encoding="utf-8")

    result = validate_with_ea(xmi, EaValidationConfig(template=Path(template), strict=True))

    assert result.ok
