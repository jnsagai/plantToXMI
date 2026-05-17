from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Annotated

import typer

from planttoxmi.orchestrator import Orchestrator
from planttoxmi.sample_generator import generate_sample_diagrams
from planttoxmi.types import OutputProfile, PlantToXMIError
from planttoxmi.validation.ea_validator import config_from_env, validate_with_ea
from planttoxmi.validation.profiles import validate_xmi_file
from planttoxmi.validation.result import (
    ValidationDiagnostic,
    ValidationReport,
    ValidationSeverity,
)

app = typer.Typer(help="Convert PlantUML diagrams to deterministic XMI 2.1.")
VERSION = "0.1.0"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"planttoxmi {VERSION}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the planttoxmi version.", callback=_version_callback),
    ] = False,
) -> None:
    pass


def _print_diagnostics(diagnostics: tuple) -> None:
    for diagnostic in diagnostics:
        location = f" line {diagnostic.line}:" if diagnostic.line else ":"
        typer.echo(f"{diagnostic.severity.upper()} {diagnostic.rule_id}{location} {diagnostic.message}")


@app.command()
def inspect(input_file: Annotated[Path, typer.Argument(exists=True, readable=True)]) -> None:
    result = Orchestrator().inspect(input_file.read_text(encoding="utf-8"))
    typer.echo(f"diagram_type={result.diagram_type}")
    typer.echo(f"supported={str(result.supported).lower()}")
    if result.supported_features:
        typer.echo("supported_features=" + ",".join(result.supported_features))
    if result.unsupported_features:
        typer.echo("unsupported_features=" + ",".join(result.unsupported_features))
    _print_diagnostics(result.diagnostics)
    if not result.supported:
        raise typer.Exit(2)


@app.command()
def convert(
    input_file: Annotated[Path, typer.Argument(exists=True, readable=True)],
    output: Annotated[Path, typer.Option("--output", "-o")],
    profile: Annotated[OutputProfile, typer.Option("--profile")] = "canonical",
) -> None:
    source = input_file.read_text(encoding="utf-8")
    try:
        result = Orchestrator().convert(source, profile=profile, source_name=str(input_file))
    except PlantToXMIError as exc:
        _print_diagnostics(exc.diagnostics)
        raise typer.Exit(1) from exc
    output.write_text(result.xmi, encoding="utf-8")
    _print_diagnostics(result.warnings)
    typer.echo(f"Wrote {output}")


@app.command()
def validate(
    input_file: Annotated[Path, typer.Argument(exists=True, readable=True)],
    profile: Annotated[OutputProfile, typer.Option("--profile")] = "canonical",
    ea_template: Annotated[
        Path | None,
        typer.Option("--ea-template", help="Blank EA repository used as the import target."),
    ] = None,
    ea_keep_temp: Annotated[
        bool,
        typer.Option("--ea-keep-temp", help="Keep the temporary EA repository for debugging."),
    ] = False,
    ea_import_diagrams: Annotated[
        bool,
        typer.Option(
            "--ea-import-diagrams/--ea-no-import-diagrams",
            help="Ask EA to import diagrams when running EA validation.",
        ),
    ] = True,
    ea_strip_guids: Annotated[
        bool,
        typer.Option(
            "--ea-strip-guids/--ea-keep-guids",
            help="Ask EA to strip GUIDs during import.",
        ),
    ] = True,
    ea_strict: Annotated[
        bool | None,
        typer.Option("--ea-strict", help="Treat unavailable EA automation as a validation failure."),
    ] = None,
    ea_timeout: Annotated[
        int | None,
        typer.Option("--ea-timeout", help="EA validation subprocess timeout in seconds."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable validation diagnostics."),
    ] = False,
) -> None:
    result = _validate_file_for_cli(
        input_file=input_file,
        profile=profile,
        ea_template=ea_template,
        ea_keep_temp=ea_keep_temp,
        ea_import_diagrams=ea_import_diagrams,
        ea_strip_guids=ea_strip_guids,
        ea_strict=ea_strict,
        ea_timeout=ea_timeout,
    )
    if json_output:
        typer.echo(json.dumps(_report_to_json(result), indent=2))
    else:
        _print_validation_report(result)
        if result.ok and profile == "canonical":
            typer.echo("XMI is valid.")
    raise typer.Exit(_exit_code_for_validation(result))


@app.command("generate-samples")
def generate_samples(
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o")] = Path("examples/generated"),
    seed: Annotated[int, typer.Option("--seed")] = 7,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for sample in generate_sample_diagrams(seed=seed):
        path = output_dir / sample.name
        path.write_text(sample.source, encoding="utf-8")
        typer.echo(f"Wrote {path} ({sample.diagram_type}, {sample.complexity})")


@app.command()
def doctor(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable runtime diagnostics."),
    ] = False,
) -> None:
    checks = [
        {
            "name": "runtime_startup",
            "ok": True,
            "severity": "info",
            "message": "planttoxmi runtime started.",
        },
        {
            "name": "ea_validation_backend",
            "ok": False,
            "severity": "warning",
            "message": "EA COM validation backend is optional and environment-dependent.",
        },
    ]
    payload = {"ok": True, "version": VERSION, "checks": checks}
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return
    typer.echo(f"planttoxmi {VERSION}")
    for check in checks:
        status = "OK" if check["ok"] else check["severity"].upper()
        typer.echo(f"{status}: {check['name']} - {check['message']}")


def _validate_file_for_cli(
    input_file: Path,
    profile: OutputProfile,
    ea_template: Path | None,
    ea_keep_temp: bool,
    ea_import_diagrams: bool,
    ea_strip_guids: bool,
    ea_strict: bool | None,
    ea_timeout: int | None,
) -> ValidationReport:
    base_result = validate_xmi_file(input_file, profile=profile)
    if profile != "ea" or not base_result.ok:
        return base_result

    config = config_from_env(
        template=ea_template,
        strict=ea_strict,
        keep_temp=ea_keep_temp,
        import_diagrams=ea_import_diagrams,
        strip_guids=ea_strip_guids,
        timeout_seconds=ea_timeout,
    )
    ea_result = validate_with_ea(input_file, config)
    return ValidationReport(
        ok=base_result.ok and ea_result.ok,
        profile=profile,
        diagnostics=[*base_result.diagnostics, *ea_result.diagnostics],
        artifact=input_file,
    )


def _print_validation_report(result: ValidationReport) -> None:
    for diagnostic in result.diagnostics:
        prefix = _human_prefix(diagnostic)
        typer.echo(f"{prefix}: {diagnostic.message}")
        if diagnostic.detail:
            typer.echo("")
            typer.echo("EA reported:" if diagnostic.code.startswith("EA_") else "Detail:")
            typer.echo(diagnostic.detail)
        if diagnostic.hint:
            typer.echo(f"Hint: {diagnostic.hint}")
        temp_repo = diagnostic.metadata.get("temporary_repository")
        if temp_repo:
            typer.echo(f"Temporary repository: {temp_repo}")


def _human_prefix(diagnostic: ValidationDiagnostic) -> str:
    if diagnostic.severity == ValidationSeverity.INFO:
        return "OK"
    if diagnostic.severity == ValidationSeverity.WARNING:
        return "WARN"
    if diagnostic.severity == ValidationSeverity.SKIPPED:
        return "SKIP"
    return "FAIL"


def _exit_code_for_validation(result: ValidationReport) -> int:
    if result.ok:
        return 0
    if any(
        diagnostic.severity == ValidationSeverity.ERROR
        and diagnostic.code
        in {
            "EA_VALIDATION_SKIPPED_UNSUPPORTED_PLATFORM",
            "EA_VALIDATION_SKIPPED_TEMPLATE_MISSING",
            "EA_VALIDATION_SKIPPED_COM_UNAVAILABLE",
        }
        for diagnostic in result.diagnostics
    ):
        return 3
    return 2


def _report_to_json(result: ValidationReport) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "profile": result.profile,
        "artifact": str(result.artifact) if result.artifact else None,
        "diagnostics": [_diagnostic_to_json(diagnostic) for diagnostic in result.diagnostics],
    }


def _diagnostic_to_json(diagnostic: ValidationDiagnostic) -> dict[str, Any]:
    payload = asdict(diagnostic)
    payload["severity"] = _json_value(diagnostic.severity)
    payload["metadata"] = {
        key: _json_value(value) for key, value in diagnostic.metadata.items() if value is not None
    }
    return payload


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    return value
