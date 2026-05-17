from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ElementKind = Literal[
    "activity",
    "actor",
    "artifact",
    "class",
    "clock",
    "component",
    "constraint",
    "interface",
    "lifeline",
    "node",
    "object",
    "package",
    "participant",
    "port",
    "profile",
    "state",
    "stereotype",
    "usecase",
]
RequirementRelationshipKind = Literal["trace", "refine", "satisfy", "verify", "derive", "containment"]
RelationshipKind = Literal[
    "dependency",
    "association",
    "realization",
    "trace",
    "refine",
    "satisfy",
    "verify",
    "derive",
    "containment",
]
MessageKind = Literal["synchCall", "asynchCall", "reply", "createMessage", "deleteMessage"]


@dataclass(frozen=True)
class UMLElement:
    id: str
    name: str
    kind: ElementKind
    alias: str | None = None
    stereotypes: tuple[str, ...] = ()


@dataclass(frozen=True)
class UMLRelationship:
    id: str
    source: str
    target: str
    kind: RelationshipKind
    name: str | None = None
    stereotypes: tuple[str, ...] = ()


@dataclass(frozen=True)
class UMLRequirement:
    id: str
    name: str
    requirement_id: str | None = None
    text: str | None = None
    alias: str | None = None


@dataclass(frozen=True)
class UMLComment:
    id: str
    body: str
    annotated_element: str | None = None


@dataclass(frozen=True)
class UMLMessage:
    id: str
    source: str
    target: str
    name: str
    kind: MessageKind


@dataclass(frozen=True)
class UMLInteraction:
    id: str
    name: str
    lifelines: tuple[UMLElement, ...] = ()
    messages: tuple[UMLMessage, ...] = ()
    comments: tuple[UMLComment, ...] = ()


@dataclass(frozen=True)
class UMLModel:
    id: str
    name: str
    diagram_type: str
    elements: tuple[UMLElement, ...] = ()
    requirements: tuple[UMLRequirement, ...] = ()
    relationships: tuple[UMLRelationship, ...] = ()
    comments: tuple[UMLComment, ...] = ()
    interactions: tuple[UMLInteraction, ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)
