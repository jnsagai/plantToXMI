from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

OutputProfile = Literal["canonical", "ea", "sysml"]


@dataclass(frozen=True)
class Diagnostic:
    rule_id: str
    message: str
    line: int | None = None
    severity: Literal["error", "warning"] = "error"


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[Diagnostic, ...] = ()
    warnings: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class ConversionResult:
    xmi: str
    diagram_type: str
    profile: OutputProfile
    warnings: tuple[Diagnostic, ...]
    validation: ValidationResult


@dataclass(frozen=True)
class InspectionResult:
    diagram_type: str
    supported: bool
    supported_features: tuple[str, ...] = ()
    unsupported_features: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = field(default_factory=tuple)


class PlantToXMIError(Exception):
    def __init__(self, diagnostics: list[Diagnostic] | tuple[Diagnostic, ...]) -> None:
        self.diagnostics = tuple(diagnostics)
        message = "; ".join(d.message for d in self.diagnostics) or "PlantUML conversion failed"
        super().__init__(message)
