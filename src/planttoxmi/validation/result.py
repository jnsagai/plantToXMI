from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ValidationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ValidationDiagnostic:
    code: str
    severity: ValidationSeverity
    message: str
    detail: str | None = None
    location: str | None = None
    hint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    profile: str
    diagnostics: list[ValidationDiagnostic]
    artifact: Path | None = None

    @property
    def has_errors(self) -> bool:
        return any(diagnostic.severity == ValidationSeverity.ERROR for diagnostic in self.diagnostics)

    @property
    def is_skipped_only(self) -> bool:
        return bool(self.diagnostics) and all(
            diagnostic.severity in {ValidationSeverity.INFO, ValidationSeverity.SKIPPED}
            for diagnostic in self.diagnostics
        )
