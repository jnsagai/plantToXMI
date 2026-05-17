from __future__ import annotations

import json
import subprocess
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from planttoxmi import convert_plantuml
from planttoxmi.cli import app
from planttoxmi.validation.ea_bridge import EaProbeResult, parse_probe_json, run_ea_import_probe
from planttoxmi.validation.ea_validator import EaValidationConfig, validate_with_ea

runner = CliRunner()


def _valid_xmi_file(tmp_path: Path) -> Path:
    result = convert_plantuml("@startuml\n[A] --> [B]\n@enduml\n", profile="ea")
    path = tmp_path / "component.xmi"
    path.write_text(result.xmi, encoding="utf-8")
    return path


def test_missing_template_skips_when_not_strict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Windows")

    result = validate_with_ea(
        tmp_path / "diagram.xmi",
        EaValidationConfig(template=tmp_path / "missing.qea", strict=False),
    )

    assert result.ok
    assert result.diagnostics[0].severity == "skipped"
    assert result.diagnostics[0].code == "EA_VALIDATION_SKIPPED_TEMPLATE_MISSING"


def test_missing_template_fails_when_strict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Windows")

    result = validate_with_ea(
        tmp_path / "diagram.xmi",
        EaValidationConfig(template=tmp_path / "missing.qea", strict=True),
    )

    assert not result.ok
    assert result.diagnostics[0].severity == "error"
    assert result.diagnostics[0].code == "EA_VALIDATION_SKIPPED_TEMPLATE_MISSING"


def test_non_windows_platform_skips_when_not_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("platform.system", lambda: "Linux")

    result = validate_with_ea(tmp_path / "diagram.xmi", EaValidationConfig(template=None))

    assert result.ok
    assert result.diagnostics[0].code == "EA_VALIDATION_SKIPPED_UNSUPPORTED_PLATFORM"


def test_probe_success_maps_to_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    template = tmp_path / "blank.qea"
    template.write_text("blank", encoding="utf-8")
    xmi = tmp_path / "diagram.xmi"
    xmi.write_text("<xmi/>", encoding="utf-8")
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr(
        "planttoxmi.validation.ea_validator.run_ea_import_probe",
        lambda **kwargs: EaProbeResult(
            returncode=0,
            payload={"ok": True, "stage": "import", "message": "EA import succeeded"},
            stdout="{}",
            stderr="",
        ),
    )

    result = validate_with_ea(xmi, EaValidationConfig(template=template))

    assert result.ok
    assert result.diagnostics[0].code == "EA_VALIDATION_OK"


def test_probe_import_failure_maps_to_import_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = tmp_path / "blank.qea"
    template.write_text("blank", encoding="utf-8")
    xmi = tmp_path / "diagram.xmi"
    xmi.write_text("<xmi/>", encoding="utf-8")
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr(
        "planttoxmi.validation.ea_validator.run_ea_import_probe",
        lambda **kwargs: EaProbeResult(
            returncode=20,
            payload={
                "ok": False,
                "stage": "import",
                "message": "EA import failed",
                "ea_error": "Package import caused error: broken",
            },
            stdout="{}",
            stderr="",
        ),
    )

    result = validate_with_ea(xmi, EaValidationConfig(template=template))

    assert not result.ok
    assert result.diagnostics[0].code == "EA_VALIDATION_FAILED_IMPORT"
    assert "broken" in (result.diagnostics[0].detail or "")


def test_com_unavailable_skips_when_not_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = tmp_path / "blank.qea"
    template.write_text("blank", encoding="utf-8")
    xmi = tmp_path / "diagram.xmi"
    xmi.write_text("<xmi/>", encoding="utf-8")
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr(
        "planttoxmi.validation.ea_validator.run_ea_import_probe",
        lambda **kwargs: EaProbeResult(
            returncode=11,
            payload={
                "ok": False,
                "stage": "com_create",
                "message": "Could not create EA.Repository COM object",
                "exception": "COM unavailable",
            },
            stdout="{}",
            stderr="",
        ),
    )

    result = validate_with_ea(xmi, EaValidationConfig(template=template, strict=False))

    assert result.ok
    assert result.diagnostics[0].severity == "skipped"
    assert result.diagnostics[0].code == "EA_VALIDATION_SKIPPED_COM_UNAVAILABLE"


def test_com_unavailable_fails_when_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = tmp_path / "blank.qea"
    template.write_text("blank", encoding="utf-8")
    xmi = tmp_path / "diagram.xmi"
    xmi.write_text("<xmi/>", encoding="utf-8")
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr(
        "planttoxmi.validation.ea_validator.run_ea_import_probe",
        lambda **kwargs: EaProbeResult(
            returncode=11,
            payload={
                "ok": False,
                "stage": "com_create",
                "message": "Could not create EA.Repository COM object",
                "exception": "COM unavailable",
            },
            stdout="{}",
            stderr="",
        ),
    )

    result = validate_with_ea(xmi, EaValidationConfig(template=template, strict=True))

    assert not result.ok
    assert result.diagnostics[0].severity == "error"
    assert result.diagnostics[0].code == "EA_VALIDATION_SKIPPED_COM_UNAVAILABLE"


def test_probe_timeout_maps_to_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    template = tmp_path / "blank.qea"
    template.write_text("blank", encoding="utf-8")
    xmi = tmp_path / "diagram.xmi"
    xmi.write_text("<xmi/>", encoding="utf-8")
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr(
        "planttoxmi.validation.ea_validator.run_ea_import_probe",
        Mock(side_effect=subprocess.TimeoutExpired(cmd="ea", timeout=1)),
    )

    result = validate_with_ea(xmi, EaValidationConfig(template=template, timeout_seconds=1))

    assert not result.ok
    assert result.diagnostics[0].code == "EA_VALIDATION_FAILED_TIMEOUT"


def test_invalid_probe_json_maps_to_exception() -> None:
    payload = parse_probe_json("not json")

    assert payload["stage"] == "probe_output"
    assert payload["ok"] is False


def test_probe_treats_guid_return_as_success() -> None:
    probe_path = Path(__file__).resolve().parents[1] / "scripts" / "ea_import_probe.py"
    spec = importlib.util.spec_from_file_location("ea_import_probe", probe_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._is_import_success("{4B83F762-0A05-4142-BA5A-BD00E7526378}")
    assert module._is_import_success("")
    assert not module._is_import_success("Package import caused error: broken")


def test_bridge_timeout_terminates_only_new_ea_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []
    killed = False

    def fake_run(command: list[str], **kwargs):
        nonlocal killed
        calls.append(command)
        if command[0] == "tasklist" and len(calls) == 1:
            return subprocess.CompletedProcess(command, 0, '"EA.exe","111","Console"\n', "")
        if command[0] == "tasklist":
            if killed:
                return subprocess.CompletedProcess(command, 0, '"EA.exe","111","Console"\n', "")
            return subprocess.CompletedProcess(
                command, 0, '"EA.exe","111","Console"\n"EA.exe","222","Console"\n', ""
            )
        if command[0] == "taskkill":
            killed = True
            return subprocess.CompletedProcess(command, 0, "", "")
        raise subprocess.TimeoutExpired(cmd=command, timeout=1)

    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr("planttoxmi.validation.ea_bridge.subprocess.run", fake_run)

    with pytest.raises(subprocess.TimeoutExpired):
        run_ea_import_probe(
            repository=tmp_path / "blank.qea",
            xmi=tmp_path / "diagram.xmi",
            import_diagrams=True,
            strip_guids=True,
            timeout_seconds=1,
        )

    assert ["taskkill", "/PID", "222", "/T", "/F"] in calls
    assert ["taskkill", "/PID", "111", "/T", "/F"] not in calls


def test_cli_json_output_includes_diagnostics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    xmi = _valid_xmi_file(tmp_path)
    monkeypatch.setattr("platform.system", lambda: "Windows")

    result = runner.invoke(app, ["validate", str(xmi), "--profile", "ea", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["diagnostics"][-1]["code"] == "EA_VALIDATION_SKIPPED_TEMPLATE_MISSING"


def test_cli_invalid_xml_stops_before_ea(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    xmi = tmp_path / "invalid.xml"
    xmi.write_text("<xmi:XMI>", encoding="utf-8")
    ea_probe = Mock()
    monkeypatch.setattr("planttoxmi.validation.ea_validator.run_ea_import_probe", ea_probe)

    result = runner.invoke(app, ["validate", str(xmi), "--profile", "ea"])

    assert result.exit_code == 2
    assert "XML is not well-formed" in result.stdout
    ea_probe.assert_not_called()


def test_keep_temp_reports_temporary_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    template = tmp_path / "blank.qea"
    template.write_text("blank", encoding="utf-8")
    xmi = tmp_path / "diagram.xmi"
    xmi.write_text("<xmi/>", encoding="utf-8")
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr(
        "planttoxmi.validation.ea_validator.run_ea_import_probe",
        lambda **kwargs: EaProbeResult(
            returncode=0,
            payload={"ok": True, "stage": "import", "message": "EA import succeeded"},
            stdout="{}",
            stderr="",
        ),
    )

    result = validate_with_ea(xmi, EaValidationConfig(template=template, keep_temp=True))

    temp_repo = result.diagnostics[0].metadata["temporary_repository"]
    assert temp_repo
    assert Path(temp_repo).exists()
