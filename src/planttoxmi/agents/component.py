from __future__ import annotations

import re

from planttoxmi.agents.base import DiagramAgent
from planttoxmi.ids import stable_id
from planttoxmi.ir import UMLElement, UMLComment, UMLModel, UMLRelationship
from planttoxmi.types import Diagnostic, PlantToXMIError

DECLARATION_RE = re.compile(
    r'^(?P<kind>component|interface)?\s*(?:\[(?P<bracket>[^\]]+)\]|"(?P<quoted>[^"]+)"|(?P<name>[A-Za-z_][\w.-]*))'
    r'(?:\s+(?:as|<<[^>]+>>\s+as)\s+(?P<alias>[A-Za-z_][\w-]*))?'
    r'(?:\s*<<(?P<stereo>[^>]+)>>)?\s*$',
    re.IGNORECASE,
)
RELATIONSHIP_RE = re.compile(
    r'^(?P<src>"[^"]+"|\[[^\]]+\]|[A-Za-z_][\w-]*)\s+'
    r'(?P<arrow>[.ox<|]*[-.]+[.ox>|]*|[.ox<|]+[-.]+[.ox>|]*)\s+'
    r'(?P<tgt>"[^"]+"|\[[^\]]+\]|[A-Za-z_][\w-]*)'
    r'(?:\s*:\s*(?P<label>.+))?$',
)
NOTE_RE = re.compile(r"^note\s+(?:(?:left|right|top|bottom)\s+of\s+(?P<target>[A-Za-z_][\w-]*))?.*$", re.I)


class ComponentAgent(DiagramAgent):
    diagram_type = "component"
    supported_features = (
        "components",
        "interfaces",
        "aliases",
        "dependencies",
        "associations",
        "notes",
        "stereotypes",
    )

    def parse(self, source: str, source_name: str = "plantuml") -> UMLModel:
        elements: dict[str, UMLElement] = {}
        relationships: list[UMLRelationship] = []
        comments: list[UMLComment] = []
        diagnostics: list[Diagnostic] = []
        note_target: str | None = None
        note_lines: list[str] = []

        for line_number, raw in enumerate(source.splitlines(), start=1):
            line = raw.strip()
            lower = line.lower()
            if (
                not line
                or line.startswith("'")
                or lower in {"@startuml", "@enduml"}
                or lower.startswith(("title ", "skinparam ", "left to right direction"))
            ):
                continue
            if note_lines:
                if line.lower() == "end note":
                    annotated = self._resolve_key(note_target, elements) if note_target else None
                    comments.append(
                        UMLComment(
                            id=stable_id(source_name, "comment", line_number, "\n".join(note_lines)),
                            body="\n".join(note_lines).strip(),
                            annotated_element=annotated,
                        )
                    )
                    note_lines = []
                    note_target = None
                else:
                    note_lines.append(line)
                continue
            note_match = NOTE_RE.match(line)
            if note_match:
                if ":" in line:
                    body = line.split(":", 1)[1].strip()
                    annotated = self._resolve_key(note_match.group("target"), elements)
                    comments.append(
                        UMLComment(
                            id=stable_id(source_name, "comment", line_number, body),
                            body=body,
                            annotated_element=annotated,
                        )
                    )
                else:
                    note_target = note_match.group("target")
                    note_lines = []
                continue
            rel_match = RELATIONSHIP_RE.match(line)
            if rel_match:
                src = self._ensure_element(rel_match.group("src"), elements, source_name)
                tgt = self._ensure_element(rel_match.group("tgt"), elements, source_name)
                kind = "realization" if "|>" in rel_match.group("arrow") else "dependency"
                if "--" in rel_match.group("arrow") and ">" not in rel_match.group("arrow"):
                    kind = "association"
                relationships.append(
                    UMLRelationship(
                        id=stable_id(source_name, "relationship", len(relationships), src, tgt),
                        source=src,
                        target=tgt,
                        kind=kind,
                        name=(rel_match.group("label") or "").strip() or None,
                    )
                )
                continue
            decl_match = DECLARATION_RE.match(line)
            if decl_match:
                key, element = self._element_from_declaration(decl_match, source_name)
                if key in elements:
                    diagnostics.append(
                        Diagnostic(
                            rule_id="parse.duplicate_alias",
                            message=f"Duplicate component alias/name '{key}'.",
                            line=line_number,
                        )
                    )
                elements[key] = element
                elements[element.name] = element
                continue
            if line in {"{", "}"} or line.lower().startswith(("package ", "folder ", "frame ")):
                continue
            diagnostics.append(
                Diagnostic(
                    rule_id="parse.unsupported_construct",
                    message=f"Unsupported component diagram syntax: {line}",
                    line=line_number,
                )
            )

        if note_lines:
            diagnostics.append(
                Diagnostic(rule_id="parse.unclosed_note", message="A component note was not closed.")
            )
        if diagnostics:
            raise PlantToXMIError(diagnostics)

        unique_elements = {element.id: element for element in elements.values()}
        return UMLModel(
            id=stable_id(source_name, "model", "component"),
            name="PlantUML Component Model",
            diagram_type="component",
            elements=tuple(unique_elements.values()),
            relationships=tuple(relationships),
            comments=tuple(comments),
        )

    def _element_from_declaration(self, match: re.Match[str], source_name: str) -> tuple[str, UMLElement]:
        name = (match.group("bracket") or match.group("quoted") or match.group("name") or "").strip()
        kind = "interface" if (match.group("kind") or "").lower() == "interface" else "component"
        alias = match.group("alias") or name
        stereotypes = tuple(
            item.strip() for item in (match.group("stereo") or "").split(",") if item.strip()
        )
        element = UMLElement(
            id=stable_id(source_name, kind, alias),
            name=name,
            kind=kind,
            alias=alias,
            stereotypes=stereotypes,
        )
        return alias, element

    def _clean_ref(self, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().strip("[]").strip('"')

    def _resolve_key(self, value: str | None, elements: dict[str, UMLElement]) -> str | None:
        key = self._clean_ref(value)
        if not key:
            return None
        return elements.get(key, next((e for e in elements.values() if e.name == key), None)).id

    def _ensure_element(
        self, value: str, elements: dict[str, UMLElement], source_name: str
    ) -> str:
        key = self._clean_ref(value) or value
        found = elements.get(key) or next((e for e in elements.values() if e.name == key), None)
        if found:
            return found.id
        element = UMLElement(
            id=stable_id(source_name, "component", key),
            name=key,
            kind="component",
            alias=key,
        )
        elements[key] = element
        return element.id
