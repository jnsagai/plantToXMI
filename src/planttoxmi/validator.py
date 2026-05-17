from __future__ import annotations

from planttoxmi.types import Diagnostic, OutputProfile, ValidationResult
from planttoxmi.validation.result import ValidationSeverity
from planttoxmi.validation.xmi_profile_validator import validate_xmi_profile_text

def validate_xmi_document(xmi: str, profile: OutputProfile = "canonical") -> ValidationResult:
    result = validate_xmi_profile_text(xmi, profile=profile)
    errors = [
        Diagnostic(rule_id=_legacy_rule_id(d.code, d.message), message=d.detail or d.message)
        for d in result.diagnostics
        if d.severity == ValidationSeverity.ERROR
    ]
    warnings = [
        Diagnostic(
            rule_id=_legacy_rule_id(d.code, d.message),
            message=d.message,
            severity="warning",
        )
        for d in result.diagnostics
        if d.severity == ValidationSeverity.WARNING
    ]
    return ValidationResult(ok=not errors, errors=tuple(errors), warnings=tuple(warnings))


def _legacy_rule_id(code: str, message: str) -> str:
    if code == "XML_PARSE_ERROR":
        return "xml.syntax"
    if "Root element" in message:
        return "xmi.root"
    if "xmi:version" in message:
        return "xmi.version"
    if "uml:Model" in message:
        return "uml.model"
    if "Duplicate xmi:id" in message:
        return "xmi.duplicate_id"
    if "references unknown" in message:
        return "xmi.dangling_reference"
    if "xmi:type" in message:
        return "uml.type"
    if code == "XMI_PROFILE_WARNING":
        return "ea.extension_missing"
    return code.lower()
