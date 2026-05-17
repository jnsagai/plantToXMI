from __future__ import annotations

from pathlib import Path

from planttoxmi.validation.result import ValidationReport
from planttoxmi.validation.xmi_profile_validator import validate_xmi_profile_file
from planttoxmi.validation.xml_validator import validate_xml_file


def validate_xmi_file(path: Path, profile: str) -> ValidationReport:
    xml_result = validate_xml_file(path, profile=profile)
    if not xml_result.ok:
        return xml_result

    profile_result = validate_xmi_profile_file(path, profile=profile)
    diagnostics = [*xml_result.diagnostics, *profile_result.diagnostics]
    return ValidationReport(
        ok=profile_result.ok,
        profile=profile,
        diagnostics=diagnostics,
        artifact=path,
    )
