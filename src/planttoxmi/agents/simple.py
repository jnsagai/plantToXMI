from __future__ import annotations

import re

from planttoxmi.agents.base import DiagramAgent
from planttoxmi.ids import stable_id
from planttoxmi.ir import UMLElement, UMLInteraction, UMLMessage, UMLModel, UMLRelationship, UMLRequirement

DECL_RE = re.compile(
    r'^(?P<kind>abstract class|actor|class|enum|object|package|node|artifact|usecase|state|profile|stereotype|metaclass|'
    r'port|part|robust|concise|binary|clock|requirement)\s+'
    r'(?:"(?P<quoted>[^"]+)"|(?P<name>[A-Za-z_][\w.-]*))(?:\s+as\s+(?P<alias>[A-Za-z_][\w-]*))?',
    re.I,
)
REL_RE = re.compile(
    r'^(?P<src>"[^"]+"|[A-Za-z_][\w.-]*)\s+'
    r'(?P<arrow>[.ox<|*#]*[-.]+[.ox>|*#]*)\s+'
    r'(?P<tgt>"[^"]+"|[A-Za-z_][\w.-]*)'
    r'(?:\s*:\s*(?P<label>.+))?$',
)
COMM_RE = re.compile(
    r'^(?P<src>"[^"]+"|[A-Za-z_][\w.-]*)\s+[-.]+>\s+'
    r'(?P<tgt>"[^"]+"|[A-Za-z_][\w.-]*)\s*:\s*(?P<order>\d+(?:\.\d+)*\.?)\s*(?P<label>.*)$',
    re.I,
)
ACTIVITY_RE = re.compile(r"^:\s*(?P<name>[^;]+);$")
STATE_TRANSITION_RE = re.compile(
    r'^(?P<src>\[\*\]|[A-Za-z_][\w.-]*)\s+[-.]+>\s+(?P<tgt>\[\*\]|[A-Za-z_][\w.-]*)(?:\s*:\s*(?P<label>.+))?$'
)
TIMING_STATE_RE = re.compile(r"^@(?P<time>\d+)\s*$|^(?P<target>[A-Za-z_][\w.-]*)\s+is\s+(?P<state>[A-Za-z_][\w.-]*)$", re.I)
REQUIREMENT_PROPERTY_RE = re.compile(r"^(?P<key>id|text)\s*[=:]\s*(?P<value>.+?);?$", re.I)
RELATIONSHIP_STEREOTYPE_RE = re.compile(r"<<\s*(?P<name>trace|refine|satisfy|verify|derive(?:reqt)?|contain(?:ment)?)\s*>>", re.I)
RELATIONSHIP_WORD_RE = re.compile(r"\b(trace|refine|satisfy|verify|derive(?:reqt)?|contain(?:ment)?)\b", re.I)


class SimpleElementAgent(DiagramAgent):
    def __init__(
        self,
        diagram_type: str,
        default_kind: str,
        features: tuple[str, ...],
    ) -> None:
        self.diagram_type = diagram_type
        self.default_kind = default_kind
        self.supported_features = features

    def parse(self, source: str, source_name: str = "plantuml") -> UMLModel:
        elements: dict[str, UMLElement] = {}
        requirements: dict[str, UMLRequirement] = {}
        relationships: list[UMLRelationship] = []
        last_time = ""
        current_requirement: str | None = None

        for raw in source.splitlines():
            line = raw.strip()
            lower = line.lower()
            if line == "}":
                current_requirement = None
                continue
            if (
                not line
                or line.startswith("'")
                or lower in {"@startuml", "@enduml", "{"}
                or lower.startswith(("title ", "skinparam ", "left to right direction"))
                or line == "else (no)"
                or line == "endif"
            ):
                continue
            if current_requirement and self.diagram_type == "requirements":
                prop = REQUIREMENT_PROPERTY_RE.match(line)
                if prop:
                    self._set_requirement_property(
                        requirements,
                        current_requirement,
                        prop.group("key"),
                        prop.group("value"),
                    )
                continue
            if lower in {"start", "stop"}:
                self._ensure(line, "activity", elements, source_name)
                continue
            if lower.startswith(("if ", "else ", "endif")):
                self._ensure(line.strip(";"), "activity", elements, source_name)
                continue

            activity = ACTIVITY_RE.match(line)
            if activity:
                self._ensure(activity.group("name"), "activity", elements, source_name)
                continue

            timing = TIMING_STATE_RE.match(line)
            if timing and self.diagram_type == "timing":
                if timing.group("time"):
                    last_time = timing.group("time")
                elif timing.group("target") and timing.group("state"):
                    source_id = self._ensure(timing.group("target"), "lifeline", elements, source_name)
                    state_id = self._ensure(
                        f"{timing.group('target')}@{last_time}:{timing.group('state')}",
                        "state",
                        elements,
                        source_name,
                    )
                    relationships.append(self._relationship(source_name, relationships, source_id, state_id, "stateAt"))
                continue

            comm = COMM_RE.match(line)
            if comm:
                src = self._ensure_ref(comm.group("src"), elements, requirements, source_name)
                tgt = self._ensure_ref(comm.group("tgt"), elements, requirements, source_name)
                relationships.append(
                    self._relationship(
                        source_name,
                        relationships,
                        src,
                        tgt,
                        f"{comm.group('order')} {comm.group('label')}".strip(),
                    )
                )
                continue

            rel = REL_RE.match(line)
            if rel:
                if self.diagram_type == "requirements" and "*" in rel.group("arrow"):
                    src = self._ensure_requirement(rel.group("src"), requirements, source_name, alias=self._clean(rel.group("src")))
                    tgt = self._ensure_requirement(rel.group("tgt"), requirements, source_name, alias=self._clean(rel.group("tgt")))
                else:
                    src = self._ensure_ref(rel.group("src"), elements, requirements, source_name)
                    tgt = self._ensure_ref(rel.group("tgt"), elements, requirements, source_name)
                relationships.append(
                    self._relationship(
                        source_name,
                        relationships,
                        src,
                        tgt,
                        (rel.group("label") or "").strip() or None,
                        rel.group("arrow"),
                        src in {req.id for req in requirements.values()},
                        tgt in {req.id for req in requirements.values()},
                    )
                )
                continue

            state_transition = STATE_TRANSITION_RE.match(line)
            if state_transition:
                src = self._ensure(state_transition.group("src"), "state", elements, source_name)
                tgt = self._ensure(state_transition.group("tgt"), "state", elements, source_name)
                relationships.append(
                    self._relationship(
                        source_name,
                        relationships,
                        src,
                        tgt,
                        (state_transition.group("label") or "").strip() or None,
                    )
                )
                continue

            decl = DECL_RE.match(line)
            if decl:
                kind = self._kind_from_decl(decl.group("kind"))
                name = decl.group("quoted") or decl.group("name") or ""
                alias = decl.group("alias") or name
                if kind == "requirement" or (
                    self.diagram_type == "requirements" and "<<" in line and "requirement" in lower
                ):
                    current_requirement = self._ensure_requirement(name, requirements, source_name, alias=alias)
                    if "{" not in line:
                        current_requirement = None
                else:
                    self._ensure(name, kind, elements, source_name, alias=alias)
                continue

            if ":" in line and self.diagram_type in {"class", "object", "composite", "profile"}:
                continue

        if self.diagram_type in {"activity", "interaction_overview"}:
            relationships.extend(self._flow_relationships(source_name, tuple(elements.values()), relationships))

        return UMLModel(
            id=stable_id(source_name, "model", self.diagram_type),
            name=f"PlantUML {self.diagram_type.replace('_', ' ').title()} Model",
            diagram_type=self.diagram_type,
            elements=tuple({element.id: element for element in elements.values()}.values()),
            requirements=tuple({requirement.id: requirement for requirement in requirements.values()}.values()),
            relationships=tuple(relationships),
        )

    def _kind_from_decl(self, kind: str) -> str:
        normalized = kind.lower()
        if normalized in {"abstract class", "enum", "metaclass", "part"}:
            return "class"
        if normalized in {"robust", "concise", "binary"}:
            return "lifeline"
        if normalized == "clock":
            return "clock"
        if normalized == "requirement":
            return "requirement"
        return normalized

    def _clean(self, value: str) -> str:
        return value.strip().strip('"')

    def _ensure_ref(
        self,
        value: str,
        elements: dict[str, UMLElement],
        requirements: dict[str, UMLRequirement],
        source_name: str,
    ) -> str:
        key = self._clean(value)
        element = elements.get(key)
        if element:
            return element.id
        requirement = requirements.get(key)
        if requirement:
            return requirement.id
        return self._ensure(key, self.default_kind, elements, source_name)

    def _ensure(
        self,
        name: str,
        kind: str,
        elements: dict[str, UMLElement],
        source_name: str,
        alias: str | None = None,
    ) -> str:
        clean_name = self._clean(name)
        key = alias or clean_name
        element = elements.get(key)
        if element:
            return element.id
        element = UMLElement(
            id=stable_id(source_name, kind, key),
            name=clean_name,
            kind=kind,  # type: ignore[arg-type]
            alias=key,
        )
        elements[key] = element
        elements[clean_name] = element
        return element.id

    def _ensure_requirement(
        self,
        name: str,
        requirements: dict[str, UMLRequirement],
        source_name: str,
        alias: str | None = None,
    ) -> str:
        clean_name = self._clean(name)
        key = alias or clean_name
        requirement = requirements.get(key)
        if requirement:
            if requirement.name == key and clean_name != key:
                updated = UMLRequirement(
                    id=requirement.id,
                    name=clean_name,
                    requirement_id=requirement.requirement_id,
                    text=requirement.text,
                    alias=requirement.alias,
                )
                for lookup_key, existing in tuple(requirements.items()):
                    if existing.id == requirement.id:
                        requirements[lookup_key] = updated
            return requirement.id
        requirement = UMLRequirement(
            id=stable_id(source_name, "requirement", key),
            name=clean_name,
            alias=key,
        )
        requirements[key] = requirement
        requirements[clean_name] = requirement
        return requirement.id

    def _set_requirement_property(
        self,
        requirements: dict[str, UMLRequirement],
        requirement_id: str,
        key: str,
        value: str,
    ) -> None:
        clean_value = self._clean(value.rstrip(";"))
        for lookup_key, requirement in tuple(requirements.items()):
            if requirement.id != requirement_id:
                continue
            updated = (
                UMLRequirement(
                    id=requirement.id,
                    name=requirement.name,
                    requirement_id=clean_value,
                    text=requirement.text,
                    alias=requirement.alias,
                )
                if key.lower() == "id"
                else UMLRequirement(
                    id=requirement.id,
                    name=requirement.name,
                    requirement_id=requirement.requirement_id,
                    text=clean_value,
                    alias=requirement.alias,
                )
            )
            requirements[lookup_key] = updated

    def _relationship(
        self,
        source_name: str,
        relationships: list[UMLRelationship],
        src: str,
        tgt: str,
        label: str | None,
        arrow: str = "",
        source_is_requirement: bool = False,
        target_is_requirement: bool = False,
    ) -> UMLRelationship:
        kind, stereotypes, clean_label = self._relationship_kind(label, arrow, source_is_requirement, target_is_requirement)
        return UMLRelationship(
            id=stable_id(source_name, "relationship", len(relationships), src, tgt, label or ""),
            source=src,
            target=tgt,
            kind=kind,
            name=clean_label,
            stereotypes=stereotypes,
        )

    def _relationship_kind(
        self,
        label: str | None,
        arrow: str,
        source_is_requirement: bool,
        target_is_requirement: bool,
    ) -> tuple[str, tuple[str, ...], str | None]:
        if self.diagram_type != "requirements":
            return "association", (), label
        raw_label = label or ""
        match = RELATIONSHIP_STEREOTYPE_RE.search(raw_label) or RELATIONSHIP_WORD_RE.search(raw_label)
        if match:
            name = match.group("name") if "name" in match.groupdict() else match.group(1)
            kind = self._normalize_requirement_relationship(name)
            clean_label = RELATIONSHIP_STEREOTYPE_RE.sub("", raw_label).strip() or None
            return kind, (kind,), clean_label
        if "*" in arrow and source_is_requirement and target_is_requirement:
            return "containment", ("containment",), label
        return "trace", ("trace",), label

    def _normalize_requirement_relationship(self, value: str) -> str:
        normalized = value.lower()
        if normalized in {"derivereqt", "derive"}:
            return "derive"
        if normalized in {"contain", "containment"}:
            return "containment"
        return normalized

    def _flow_relationships(
        self,
        source_name: str,
        elements: tuple[UMLElement, ...],
        existing: list[UMLRelationship],
    ) -> list[UMLRelationship]:
        flows: list[UMLRelationship] = []
        for index, (src, tgt) in enumerate(zip(elements, elements[1:]), start=len(existing)):
            flows.append(
                UMLRelationship(
                    id=stable_id(source_name, "flow", index, src.id, tgt.id),
                    source=src.id,
                    target=tgt.id,
                    kind="dependency",
                    name="flow",
                )
            )
        return flows


class CommunicationAgent(SimpleElementAgent):
    def __init__(self) -> None:
        super().__init__("communication", "object", ("objects", "numbered messages", "links"))


class InteractionOverviewAgent(SimpleElementAgent):
    def __init__(self) -> None:
        super().__init__("interaction_overview", "activity", ("interaction references", "control flow"))


class TimingAgent(SimpleElementAgent):
    def __init__(self) -> None:
        super().__init__("timing", "lifeline", ("lifelines", "time states"))
