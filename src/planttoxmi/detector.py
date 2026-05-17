from __future__ import annotations

import re

from planttoxmi.types import InspectionResult

SUPPORTED = {"component", "sequence"}

PLACEHOLDER_TYPES = {
    "activity",
    "class",
    "communication",
    "composite",
    "deployment",
    "interaction_overview",
    "object",
    "package",
    "profile",
    "state",
    "timing",
    "usecase",
    "requirements",
}


def strip_comments(source: str) -> list[str]:
    return [
        line.strip().lstrip("\ufeff")
        for line in source.splitlines()
        if line.strip().lstrip("\ufeff") and not line.strip().lstrip("\ufeff").startswith("'")
    ]


def detect_diagram_type(source: str) -> str:
    lines = strip_comments(source)
    body = "\n".join(lines).lower()
    if re.search(r"\brequirement\b|\bderive(?:reqt)?\b|\bsatisfy\b|\bverify\b|\brefine\b|\btrace\b", body):
        return "requirements"
    if re.search(r"\bprofile\b|\bstereotype\b|\bmetaclass\b", body):
        return "profile"
    if re.search(r"\binteraction overview\b|\bref\s+[\w\"[].*\b(sequence|interaction)\b", body):
        return "interaction_overview"
    if re.search(r"\b(robust|concise|binary|clock)\s+\"?[^\n]+?\b(as\b|is\b)", body):
        return "timing"
    if re.search(r"\b(usecase|use case)\b", body):
        return "usecase"
    if re.search(r"\bobject\s+[\w\"{]", body) and re.search(r":\s*\d+(?:\.\d+)*\.?\s+\w", body):
        return "communication"
    if re.search(r"\bobject\s+[\w\"{]", body):
        return "object"
    if re.search(r"(?m)^\s*state\b|\[\*\]\s*-->", body):
        return "state"
    if re.search(r"\bstart\b|\bstop\b|\bif\b.*\bthen\b|:\s*[^;]+;", body):
        return "activity"
    if re.search(r"\bpackage\s+[\w\"{]", body):
        return "package"
    if re.search(r"\b(port|part)\s+[\w\"]|\bstructuredclassifier\b", body):
        return "composite"
    if re.search(r"\b(component|interface)\s+[\w\"[]", body) or re.search(r"\[[^\]]+\]", body):
        return "component"
    if re.search(r"\b(actor|participant|boundary|control|entity|database|collections|queue)\b", body):
        return "sequence"
    if re.search(r"[-.ox]*>\s*[:\w\"[]", body) and ":" in body:
        return "sequence"
    if re.search(r"\b(class|abstract class|enum)\b", body):
        return "class"
    if re.search(r"\bnode\b|\bcloud\b|\bdatabase\b", body):
        return "deployment"
    if re.search(r"\([^)]+\)", body):
        return "usecase"
    return "unknown"


def inspect_source(source: str) -> InspectionResult:
    diagram_type = detect_diagram_type(source)
    if diagram_type == "component":
        return InspectionResult(
            diagram_type=diagram_type,
            supported=True,
            supported_features=(
                "components",
                "interfaces",
                "aliases",
                "dependencies",
                "associations",
                "notes",
                "stereotypes",
            ),
        )
    if diagram_type == "sequence":
        return InspectionResult(
            diagram_type=diagram_type,
            supported=True,
            supported_features=(
                "participants",
                "actors",
                "messages",
                "create/destroy",
                "return messages",
                "notes",
                "group warnings",
            ),
        )
    if diagram_type == "requirements":
        return InspectionResult(
            diagram_type=diagram_type,
            supported=True,
            supported_features=(
                "requirements",
                "id/text properties",
                "trace/refine/satisfy/verify/derive relationships",
                "containment",
            ),
        )
    return InspectionResult(
        diagram_type=diagram_type,
        supported=False,
        unsupported_features=(diagram_type if diagram_type != "unknown" else "unrecognized",),
    )
