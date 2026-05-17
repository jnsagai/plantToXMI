from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

DiagramKind = Literal["component", "sequence"]
Complexity = Literal["simple", "medium", "complex"]


@dataclass(frozen=True)
class SampleDiagram:
    name: str
    diagram_type: DiagramKind
    complexity: Complexity
    source: str


COMPONENT_NAMES = (
    "WebApp",
    "AuthService",
    "BillingService",
    "CatalogService",
    "NotificationService",
    "AuditLog",
    "Database",
    "MessageBus",
    "SearchIndex",
    "AdminPortal",
)
INTERFACE_NAMES = ("PublicAPI", "AuthAPI", "BillingAPI", "CatalogAPI", "EventsAPI")
MESSAGE_NAMES = ("request", "validate", "authorize", "persist", "publish", "notify", "query", "reply")


def generate_sample_diagrams(seed: int = 7) -> tuple[SampleDiagram, ...]:
    rng = random.Random(seed)
    samples: list[SampleDiagram] = []
    for complexity in ("simple", "medium", "complex"):
        samples.append(_component_sample(rng, complexity))
        samples.append(_sequence_sample(rng, complexity))
    return tuple(samples)


def _component_sample(rng: random.Random, complexity: Complexity) -> SampleDiagram:
    counts = {"simple": (2, 1, 1), "medium": (4, 2, 4), "complex": (7, 3, 9)}
    component_count, interface_count, relationship_count = counts[complexity]
    components = rng.sample(COMPONENT_NAMES, component_count)
    interfaces = rng.sample(INTERFACE_NAMES, interface_count)
    lines = ["@startuml"]

    for index, component in enumerate(components, start=1):
        stereotype = " <<service>>" if index % 2 == 0 else ""
        lines.append(f'component "{_title(component)}" as C{index}{stereotype}')
    for index, interface in enumerate(interfaces, start=1):
        lines.append(f"interface {interface} as I{index}")

    endpoints = [f"C{i}" for i in range(1, component_count + 1)] + [
        f"I{i}" for i in range(1, interface_count + 1)
    ]
    for index in range(relationship_count):
        source, target = rng.sample(endpoints, 2)
        label = rng.choice(("uses", "calls", "publishes", "reads", "syncs"))
        arrow = rng.choice(("-->", "..>", "--"))
        lines.append(f"{source} {arrow} {target} : {label}")
        if complexity == "complex" and index % 3 == 2:
            lines.append(f"note right of {source}: generated checkpoint {index + 1}")

    lines.append("@enduml")
    return SampleDiagram(
        name=f"component_{complexity}.puml",
        diagram_type="component",
        complexity=complexity,
        source="\n".join(lines) + "\n",
    )


def _sequence_sample(rng: random.Random, complexity: Complexity) -> SampleDiagram:
    counts = {"simple": (2, 2), "medium": (4, 6), "complex": (6, 12)}
    participant_count, message_count = counts[complexity]
    names = rng.sample(COMPONENT_NAMES, participant_count)
    aliases = [f"P{i}" for i in range(1, participant_count + 1)]
    lines = ["@startuml", f'actor "{_title(names[0])} User" as {aliases[0]}']
    for alias, name in zip(aliases[1:], names[1:], strict=True):
        lines.append(f'participant "{_title(name)}" as {alias}')

    for index in range(message_count):
        source, target = rng.sample(aliases, 2)
        arrow = rng.choice(("->", "->>", "-->"))
        message = rng.choice(MESSAGE_NAMES)
        lines.append(f"{source} {arrow} {target} : {message} {index + 1}")
        if complexity in {"medium", "complex"} and index == 1:
            lines.append(f"note over {target}: generated branch context")
        if complexity == "complex" and index == 3:
            lines.append("alt happy path")
        if complexity == "complex" and index == 7:
            lines.append("else fallback")
        if complexity == "complex" and index == 10:
            lines.append("end")

    lines.append("@enduml")
    return SampleDiagram(
        name=f"sequence_{complexity}.puml",
        diagram_type="sequence",
        complexity=complexity,
        source="\n".join(lines) + "\n",
    )


def _title(value: str) -> str:
    output = []
    for index, char in enumerate(value):
        if index and char.isupper() and value[index - 1].islower():
            output.append(" ")
        output.append(char)
    return "".join(output)
