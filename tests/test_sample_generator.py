from pathlib import Path

from typer.testing import CliRunner

from planttoxmi import convert_plantuml, inspect_plantuml
from planttoxmi.cli import app
from planttoxmi.sample_generator import generate_sample_diagrams

runner = CliRunner()


def test_generated_samples_are_supported_and_convertible() -> None:
    samples = generate_sample_diagrams(seed=11)

    assert len(samples) == 6
    for sample in samples:
        inspection = inspect_plantuml(sample.source)
        result = convert_plantuml(sample.source, profile="canonical")

        assert inspection.supported
        assert result.validation.ok


def test_generate_samples_cli_writes_diagrams(tmp_path: Path) -> None:
    result = runner.invoke(app, ["generate-samples", "-o", str(tmp_path), "--seed", "3"])

    assert result.exit_code == 0
    assert len(list(tmp_path.glob("*.puml"))) == 6
    assert (tmp_path / "component_simple.puml").exists()
    assert (tmp_path / "sequence_complex.puml").exists()
