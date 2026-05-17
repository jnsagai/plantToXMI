from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from planttoxmi.validation.ea_bridge import run_ea_import_probe
from planttoxmi.validation.result import (
    ValidationDiagnostic,
    ValidationReport,
    ValidationSeverity,
)


@dataclass(frozen=True)
class EaValidationConfig:
    template: Path | None
    strict: bool = False
    keep_temp: bool = False
    import_diagrams: bool = True
    strip_guids: bool = True
    timeout_seconds: int = 120


def config_from_env(
    template: Path | None = None,
    strict: bool | None = None,
    keep_temp: bool = False,
    import_diagrams: bool = True,
    strip_guids: bool = True,
    timeout_seconds: int | None = None,
) -> EaValidationConfig:
    return EaValidationConfig(
        template=template or _path_from_env("PLANTTOXMI_EA_TEMPLATE"),
        strict=_bool_from_env("PLANTTOXMI_EA_STRICT", False) if strict is None else strict,
        keep_temp=keep_temp,
        import_diagrams=import_diagrams,
        strip_guids=strip_guids,
        timeout_seconds=timeout_seconds
        if timeout_seconds is not None
        else _int_from_env("PLANTTOXMI_EA_TIMEOUT", 120),
    )


def validate_with_ea(xmi_path: Path, config: EaValidationConfig) -> ValidationReport:
    if platform.system() != "Windows":
        return _skip_or_error(
            code="EA_VALIDATION_SKIPPED_UNSUPPORTED_PLATFORM",
            message="EA import validation requires Windows.",
            strict=config.strict,
            xmi_path=xmi_path,
            hint="Run this validation on Windows with Sparx Enterprise Architect installed.",
        )

    if config.template is None or not config.template.exists():
        return _skip_or_error(
            code="EA_VALIDATION_SKIPPED_TEMPLATE_MISSING",
            message="EA validation template repository is missing.",
            strict=config.strict,
            xmi_path=xmi_path,
            hint="Pass --ea-template PATH or set PLANTTOXMI_EA_TEMPLATE.",
            metadata={"template": str(config.template) if config.template else None},
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="planttoxmi-ea-"))
    temp_repo = temp_dir / f"validation{config.template.suffix}"
    try:
        shutil.copy2(config.template, temp_repo)
        probe = run_ea_import_probe(
            repository=temp_repo,
            xmi=xmi_path,
            import_diagrams=config.import_diagrams,
            strip_guids=config.strip_guids,
            timeout_seconds=config.timeout_seconds,
        )
        payload = probe.payload
        if probe.returncode == 0 and payload.get("ok") is True:
            return ValidationReport(
                ok=True,
                profile="ea",
                artifact=xmi_path,
                diagnostics=[
                    ValidationDiagnostic(
                        code="EA_VALIDATION_OK",
                        severity=ValidationSeverity.INFO,
                        message="EA import validation passed.",
                        metadata=_repository_metadata(temp_repo, config.keep_temp),
                    )
                ],
            )

        diagnostic_code = _map_probe_failure_code(payload)
        severity = (
            ValidationSeverity.SKIPPED
            if diagnostic_code == "EA_VALIDATION_SKIPPED_COM_UNAVAILABLE" and not config.strict
            else ValidationSeverity.ERROR
        )
        return ValidationReport(
            ok=severity == ValidationSeverity.SKIPPED,
            profile="ea",
            artifact=xmi_path,
            diagnostics=[
                ValidationDiagnostic(
                    code=diagnostic_code,
                    severity=severity,
                    message=payload.get("message", "EA import validation failed."),
                    detail=payload.get("ea_error") or payload.get("exception") or probe.stderr,
                    hint=_hint_for_probe_failure(payload),
                    metadata={
                        "returncode": probe.returncode,
                        "stage": payload.get("stage"),
                        **_repository_metadata(temp_repo, config.keep_temp),
                    },
                )
            ],
        )
    except subprocess.TimeoutExpired:
        return ValidationReport(
            ok=False,
            profile="ea",
            artifact=xmi_path,
            diagnostics=[
                ValidationDiagnostic(
                    code="EA_VALIDATION_FAILED_TIMEOUT",
                    severity=ValidationSeverity.ERROR,
                    message="EA import validation timed out.",
                    hint="Increase --ea-timeout or inspect the XMI manually in EA.",
                    metadata={"timeout_seconds": config.timeout_seconds},
                )
            ],
        )
    except Exception as exc:
        return ValidationReport(
            ok=False,
            profile="ea",
            artifact=xmi_path,
            diagnostics=[
                ValidationDiagnostic(
                    code="EA_VALIDATION_FAILED_EXCEPTION",
                    severity=ValidationSeverity.ERROR,
                    message="EA import validation failed before invoking EA.",
                    detail=repr(exc),
                )
            ],
        )
    finally:
        if not config.keep_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)


def _skip_or_error(
    code: str,
    message: str,
    strict: bool,
    xmi_path: Path,
    hint: str,
    metadata: dict | None = None,
) -> ValidationReport:
    severity = ValidationSeverity.ERROR if strict else ValidationSeverity.SKIPPED
    strict_message = message if not strict else message + " Strict mode requires EA validation."
    return ValidationReport(
        ok=not strict,
        profile="ea",
        artifact=xmi_path,
        diagnostics=[
            ValidationDiagnostic(
                code=code,
                severity=severity,
                message=strict_message,
                hint=hint,
                metadata=metadata or {},
            )
        ],
    )


def _path_from_env(name: str) -> Path | None:
    value = os.getenv(name)
    return Path(value) if value else None


def _bool_from_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _map_probe_failure_code(payload: dict) -> str:
    stage = payload.get("stage")
    if stage in {"com_import", "com_create"}:
        return "EA_VALIDATION_SKIPPED_COM_UNAVAILABLE"
    if stage == "open_repository":
        return "EA_VALIDATION_FAILED_OPEN_REPOSITORY"
    if stage == "root_model":
        return "EA_VALIDATION_FAILED_NO_ROOT_MODEL"
    if stage == "import":
        return "EA_VALIDATION_FAILED_IMPORT"
    if stage == "probe_output":
        return "EA_VALIDATION_FAILED_EXCEPTION"
    return "EA_VALIDATION_FAILED_EXCEPTION"


def _hint_for_probe_failure(payload: dict) -> str | None:
    stage = payload.get("stage")
    if stage in {"com_import", "com_create"}:
        return "Install EA, ensure pywin32 is installed, and re-register EA if needed."
    if stage == "open_repository":
        return "Check that the template repository is valid and not locked."
    if stage == "root_model":
        return "Create a blank EA repository with at least one root model package."
    if stage == "import":
        return "Open the kept temporary repository in EA and inspect the XMI import log."
    return None


def _repository_metadata(temp_repo: Path, keep_temp: bool) -> dict[str, str | None]:
    return {"temporary_repository": str(temp_repo) if keep_temp else None}
