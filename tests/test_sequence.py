from planttoxmi import convert_plantuml, inspect_plantuml


SEQUENCE = """@startuml
actor User as U
participant "API Gateway" as API
participant Service
U -> API : request
API -> Service : process
Service --> API : result
API --> U : response
@enduml
"""


def test_sequence_conversion_is_valid() -> None:
    result = convert_plantuml(SEQUENCE)

    assert result.diagram_type == "sequence"
    assert result.validation.ok
    assert "uml:Interaction" in result.xmi
    assert "messageSort" in result.xmi


def test_sequence_aliases_and_async_messages() -> None:
    result = convert_plantuml(
        """@startuml
actor User as U
participant API
U ->> API : async request
@enduml
"""
    )

    assert 'name="User"' in result.xmi
    assert 'name="API"' in result.xmi
    assert 'messageSort="asynchCall"' in result.xmi


def test_sequence_inspection() -> None:
    result = inspect_plantuml(SEQUENCE)

    assert result.diagram_type == "sequence"
    assert result.supported
