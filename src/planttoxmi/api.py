from __future__ import annotations

from planttoxmi.orchestrator import Orchestrator
from planttoxmi.types import ConversionResult, InspectionResult, OutputProfile, ValidationResult
from planttoxmi.validator import validate_xmi_document


def convert_plantuml(source: str, profile: OutputProfile = "canonical") -> ConversionResult:
    return Orchestrator().convert(source, profile=profile)


def validate_xmi(xmi: str, profile: OutputProfile = "canonical") -> ValidationResult:
    return validate_xmi_document(xmi, profile=profile)


def inspect_plantuml(source: str) -> InspectionResult:
    return Orchestrator().inspect(source)
