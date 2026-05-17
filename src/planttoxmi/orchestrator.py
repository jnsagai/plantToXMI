from __future__ import annotations

from planttoxmi.agents.registry import build_registry
from planttoxmi.detector import detect_diagram_type, inspect_source
from planttoxmi.types import ConversionResult, Diagnostic, InspectionResult, OutputProfile, PlantToXMIError
from planttoxmi.validator import validate_xmi_document
from planttoxmi.writer import serialize_xmi


class Orchestrator:
    def __init__(self) -> None:
        self.registry = build_registry()

    def inspect(self, source: str) -> InspectionResult:
        source = source.lstrip("\ufeff")
        diagram_type = detect_diagram_type(source)
        agent = self.registry.get(diagram_type)
        if agent is None:
            return inspect_source(source)
        return agent.inspect(source)

    def convert(
        self,
        source: str,
        profile: OutputProfile = "canonical",
        source_name: str = "plantuml",
    ) -> ConversionResult:
        source = source.lstrip("\ufeff")
        if profile not in {"canonical", "ea", "sysml"}:
            raise PlantToXMIError(
                [
                    Diagnostic(
                        rule_id="profile.invalid",
                        message=f"Unsupported output profile '{profile}'.",
                    )
                ]
            )
        diagram_type = detect_diagram_type(source)
        agent = self.registry.get(diagram_type)
        if agent is None:
            raise PlantToXMIError(
                [
                    Diagnostic(
                        rule_id="unsupported.diagram",
                        message=f"Unsupported PlantUML diagram type '{diagram_type}'.",
                    )
                ]
            )
        model = agent.parse(source, source_name=source_name)
        xmi = serialize_xmi(model, profile=profile)
        validation = validate_xmi_document(xmi, profile=profile)
        if not validation.ok:
            raise PlantToXMIError(validation.errors)
        warnings = tuple(
            Diagnostic(rule_id="mapping.warning", message=warning, severity="warning")
            for warning in model.warnings
        ) + validation.warnings
        return ConversionResult(
            xmi=xmi,
            diagram_type=diagram_type,
            profile=profile,
            warnings=warnings,
            validation=validation,
        )
