from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from planttoxmi.validation.result import (
    ValidationDiagnostic,
    ValidationReport,
    ValidationSeverity,
)


def validate_xml_file(path: Path, profile: str) -> ValidationReport:
    diagnostics: list[ValidationDiagnostic] = []
    try:
        ET.parse(path)
    except ET.ParseError as exc:
        diagnostics.append(
            ValidationDiagnostic(
                code="XML_PARSE_ERROR",
                severity=ValidationSeverity.ERROR,
                message="XML is not well-formed.",
                detail=str(exc),
                location=str(path),
            )
        )
        return ValidationReport(ok=False, profile=profile, diagnostics=diagnostics, artifact=path)

    diagnostics.append(
        ValidationDiagnostic(
            code="XML_WELL_FORMED_OK",
            severity=ValidationSeverity.INFO,
            message="XML well-formed.",
            location=str(path),
        )
    )
    return ValidationReport(ok=True, profile=profile, diagnostics=diagnostics, artifact=path)
