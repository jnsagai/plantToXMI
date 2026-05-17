from pathlib import Path
import json

from typer.testing import CliRunner

from planttoxmi import convert_plantuml, validate_xmi
from planttoxmi.cli import app
runner = CliRunner()


def test_validator_rejects_bad_xml() -> None:
    result = validate_xmi("<xmi:XMI>")

    assert not result.ok
    assert result.errors[0].rule_id == "xml.syntax"


def test_class_diagram_converts_to_valid_xmi() -> None:
    result = convert_plantuml("@startuml\nclass Foo\n@enduml")

    assert result.diagram_type == "class"
    assert result.validation.ok


def test_cli_convert_validate_and_inspect(tmp_path: Path) -> None:
    source = tmp_path / "component.puml"
    output = tmp_path / "component.xmi"
    source.write_text("@startuml\n[A] --> [B]\n@enduml\n", encoding="utf-8")

    inspect_result = runner.invoke(app, ["inspect", str(source)])
    assert inspect_result.exit_code == 0
    assert "diagram_type=component" in inspect_result.stdout

    convert_result = runner.invoke(app, ["convert", str(source), "-o", str(output)])
    assert convert_result.exit_code == 0
    assert output.exists()

    validate_result = runner.invoke(app, ["validate", str(output)])
    assert validate_result.exit_code == 0
    assert "XMI is valid." in validate_result.stdout


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "planttoxmi 0.1.0" in result.stdout


def test_cli_doctor_json() -> None:
    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["version"] == "0.1.0"
    assert payload["checks"][0]["name"] == "runtime_startup"
