from __future__ import annotations

from pathlib import Path

from lxml import etree

from planttoxmi.validation.result import (
    ValidationDiagnostic,
    ValidationReport,
    ValidationSeverity,
)
from planttoxmi.writer import UML_NS, XMI_ID, XMI_NS, XMI_VERSION


def validate_xmi_profile_file(path: Path, profile: str) -> ValidationReport:
    diagnostics: list[ValidationDiagnostic] = []
    try:
        root = etree.parse(str(path)).getroot()
    except etree.XMLSyntaxError as exc:
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

    errors = _validate_root(root)
    errors.extend(_validate_ids_and_references(root))
    errors.extend(_validate_uml_types(root))
    if profile == "ea" and root.find(f"{{{XMI_NS}}}Extension") is None:
        diagnostics.append(
            ValidationDiagnostic(
                code="XMI_PROFILE_WARNING",
                severity=ValidationSeverity.WARNING,
                message="EA profile XMI has no xmi:Extension block.",
                hint="Generate XMI with --profile ea for EA-friendly metadata.",
            )
        )

    if errors:
        diagnostics.extend(errors)
    else:
        diagnostics.append(
            ValidationDiagnostic(
                code="XMI_PROFILE_OK",
                severity=ValidationSeverity.INFO,
                message="XMI profile checks passed.",
                location=str(path),
            )
        )
    return ValidationReport(
        ok=not any(d.severity == ValidationSeverity.ERROR for d in diagnostics),
        profile=profile,
        diagnostics=diagnostics,
        artifact=path,
    )


def validate_xmi_profile_text(xmi: str, profile: str) -> ValidationReport:
    diagnostics: list[ValidationDiagnostic] = []
    try:
        root = etree.fromstring(xmi.encode("utf-8"))
    except etree.XMLSyntaxError as exc:
        diagnostics.append(
            ValidationDiagnostic(
                code="XML_PARSE_ERROR",
                severity=ValidationSeverity.ERROR,
                message="XML is not well-formed.",
                detail=str(exc),
            )
        )
        return ValidationReport(ok=False, profile=profile, diagnostics=diagnostics)

    errors = _validate_root(root)
    errors.extend(_validate_ids_and_references(root))
    errors.extend(_validate_uml_types(root))
    if profile == "ea" and root.find(f"{{{XMI_NS}}}Extension") is None:
        diagnostics.append(
            ValidationDiagnostic(
                code="XMI_PROFILE_WARNING",
                severity=ValidationSeverity.WARNING,
                message="EA profile XMI has no xmi:Extension block.",
            )
        )
    diagnostics.extend(errors)
    if not errors:
        diagnostics.append(
            ValidationDiagnostic(
                code="XMI_PROFILE_OK",
                severity=ValidationSeverity.INFO,
                message="XMI profile checks passed.",
            )
        )
    return ValidationReport(
        ok=not any(d.severity == ValidationSeverity.ERROR for d in diagnostics),
        profile=profile,
        diagnostics=diagnostics,
    )


def _validate_root(root: etree._Element) -> list[ValidationDiagnostic]:
    errors: list[ValidationDiagnostic] = []
    if root.tag != f"{{{XMI_NS}}}XMI":
        errors.append(
            ValidationDiagnostic(
                code="XMI_PROFILE_ERROR",
                severity=ValidationSeverity.ERROR,
                message="Root element must be xmi:XMI.",
            )
        )
    if root.get(XMI_VERSION) != "2.1":
        errors.append(
            ValidationDiagnostic(
                code="XMI_PROFILE_ERROR",
                severity=ValidationSeverity.ERROR,
                message="xmi:version must be 2.1.",
            )
        )

    model = root.find(f"{{{UML_NS}}}Model")
    if model is None:
        errors.append(
            ValidationDiagnostic(
                code="XMI_PROFILE_ERROR",
                severity=ValidationSeverity.ERROR,
                message="Document must contain uml:Model.",
            )
        )
    elif not model.get(XMI_ID):
        errors.append(
            ValidationDiagnostic(
                code="XMI_PROFILE_ERROR",
                severity=ValidationSeverity.ERROR,
                message="uml:Model must have xmi:id.",
            )
        )
    return errors


def _validate_ids_and_references(root: etree._Element) -> list[ValidationDiagnostic]:
    errors: list[ValidationDiagnostic] = []
    ids: set[str] = set()
    duplicates: set[str] = set()
    for element in root.iter():
        value = element.get(XMI_ID)
        if not value:
            continue
        if value in ids:
            duplicates.add(value)
        ids.add(value)

    for duplicate in sorted(duplicates):
        errors.append(
            ValidationDiagnostic(
                code="XMI_PROFILE_ERROR",
                severity=ValidationSeverity.ERROR,
                message=f"Duplicate xmi:id '{duplicate}'.",
            )
        )

    for element in root.iter():
        for attr in ("client", "supplier", "sendEvent", "receiveEvent", "annotatedElement"):
            value = element.get(attr)
            if not value:
                continue
            for ref in value.split():
                if ref not in ids:
                    errors.append(
                        ValidationDiagnostic(
                            code="XMI_PROFILE_ERROR",
                            severity=ValidationSeverity.ERROR,
                            message=f"Attribute {attr} references unknown xmi:id '{ref}'.",
                        )
                    )
    return errors


def _validate_uml_types(root: etree._Element) -> list[ValidationDiagnostic]:
    errors: list[ValidationDiagnostic] = []
    for node in root.xpath("//*[@xmi:type]", namespaces={"xmi": XMI_NS}):
        xmi_type = node.get(f"{{{XMI_NS}}}type")
        if xmi_type and not xmi_type.startswith("uml:"):
            errors.append(
                ValidationDiagnostic(
                    code="XMI_PROFILE_ERROR",
                    severity=ValidationSeverity.ERROR,
                    message=f"xmi:type '{xmi_type}' must use the uml namespace prefix.",
                )
            )
    return errors
