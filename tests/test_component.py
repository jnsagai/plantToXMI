from planttoxmi import convert_plantuml, inspect_plantuml, validate_xmi


COMPONENT = """@startuml
component "Web App" as Web <<service>>
interface API
[Database] as DB
Web --> API : uses
Web --> DB : stores
note right of Web: public frontend
@enduml
"""


def test_component_conversion_canonical_is_valid() -> None:
    result = convert_plantuml(COMPONENT, profile="canonical")

    assert result.diagram_type == "component"
    assert result.validation.ok
    assert 'xmi:version="2.1"' in result.xmi
    assert 'uml:Component' in result.xmi
    assert 'uml:Interface' in result.xmi
    assert validate_xmi(result.xmi).ok


def test_component_ea_profile_adds_extension() -> None:
    result = convert_plantuml(COMPONENT, profile="ea")

    assert 'extender="Enterprise Architect"' in result.xmi
    assert validate_xmi(result.xmi, profile="ea").ok


def test_component_inspection() -> None:
    result = inspect_plantuml(COMPONENT)

    assert result.diagram_type == "component"
    assert result.supported


def test_component_conversion_accepts_utf8_bom() -> None:
    result = convert_plantuml("\ufeff" + COMPONENT)

    assert result.validation.ok


def test_component_interface_alias_does_not_create_placeholder() -> None:
    result = convert_plantuml(
        """@startuml
interface EventsAPI as I1
[Web] --> I1 : uses
@enduml
""",
        profile="ea",
    )

    assert 'name="EventsAPI"' in result.xmi
    assert 'name="I1"' not in result.xmi
