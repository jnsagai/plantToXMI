from __future__ import annotations

from abc import ABC, abstractmethod

from planttoxmi.ir import UMLModel
from planttoxmi.types import Diagnostic, InspectionResult, PlantToXMIError


class DiagramAgent(ABC):
    diagram_type: str
    supported_features: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, source: str, source_name: str = "plantuml") -> UMLModel:
        raise NotImplementedError

    def inspect(self, source: str) -> InspectionResult:
        return InspectionResult(
            diagram_type=self.diagram_type,
            supported=True,
            supported_features=self.supported_features,
        )


class UnsupportedDiagramAgent(DiagramAgent):
    def __init__(self, diagram_type: str) -> None:
        self.diagram_type = diagram_type

    def parse(self, source: str, source_name: str = "plantuml") -> UMLModel:
        raise PlantToXMIError(
            [
                Diagnostic(
                    rule_id="unsupported.diagram",
                    message=f"PlantUML diagram type '{self.diagram_type}' is registered but not implemented.",
                )
            ]
        )

    def inspect(self, source: str) -> InspectionResult:
        return InspectionResult(
            diagram_type=self.diagram_type,
            supported=False,
            unsupported_features=(self.diagram_type,),
            diagnostics=(
                Diagnostic(
                    rule_id="unsupported.diagram",
                    message=f"Diagram type '{self.diagram_type}' is not implemented in v1.",
                ),
            ),
        )
