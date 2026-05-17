from __future__ import annotations

from planttoxmi.agents.base import DiagramAgent, UnsupportedDiagramAgent
from planttoxmi.agents.component import ComponentAgent
from planttoxmi.agents.sequence import SequenceAgent
from planttoxmi.agents.simple import (
    CommunicationAgent,
    InteractionOverviewAgent,
    SimpleElementAgent,
    TimingAgent,
)

ALL_DIAGRAM_TYPES = (
    "activity",
    "class",
    "communication",
    "composite",
    "component",
    "deployment",
    "interaction_overview",
    "object",
    "package",
    "profile",
    "requirements",
    "sequence",
    "state",
    "timing",
    "usecase",
    "unknown",
)


def build_registry() -> dict[str, DiagramAgent]:
    registry: dict[str, DiagramAgent] = {
        "activity": SimpleElementAgent("activity", "activity", ("actions", "control flow")),
        "class": SimpleElementAgent("class", "class", ("classes", "associations")),
        "communication": CommunicationAgent(),
        "composite": SimpleElementAgent("composite", "class", ("structured classifiers", "parts", "ports")),
        "component": ComponentAgent(),
        "deployment": SimpleElementAgent("deployment", "node", ("nodes", "artifacts", "deployment links")),
        "interaction_overview": InteractionOverviewAgent(),
        "object": SimpleElementAgent("object", "object", ("objects", "links", "slots")),
        "package": SimpleElementAgent("package", "package", ("packages", "dependencies")),
        "profile": SimpleElementAgent("profile", "profile", ("profiles", "stereotypes", "metaclasses")),
        "requirements": SimpleElementAgent(
            "requirements",
            "class",
            (
                "requirements",
                "id/text properties",
                "trace/refine/satisfy/verify/derive relationships",
                "containment",
            ),
        ),
        "sequence": SequenceAgent(),
        "state": SimpleElementAgent("state", "state", ("states", "transitions")),
        "timing": TimingAgent(),
        "usecase": SimpleElementAgent("usecase", "usecase", ("actors", "use cases", "associations")),
    }
    for diagram_type in ALL_DIAGRAM_TYPES:
        registry.setdefault(diagram_type, UnsupportedDiagramAgent(diagram_type))
    return registry
