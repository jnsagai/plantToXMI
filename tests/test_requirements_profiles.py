from __future__ import annotations

from planttoxmi import convert_plantuml, validate_xmi


REQUIREMENTS = """@startuml
requirement "Safe state on watchdog fault" as REQ_WD {
  id = "REQ-SAFE-001"
  text = "The scheduler shall enter safe state after a watchdog fault."
}
class Scheduler
REQ_WD ..> Scheduler : <<satisfy>>
REQ_WD ..> Scheduler : <<verify>>
REQ_WD ..> Scheduler : <<refine>>
REQ_WD ..> Scheduler : <<trace>>
REQ_PARENT *-- REQ_WD
requirement "Parent safety goal" as REQ_PARENT {
  id = "REQ-SAFE"
  text = "The system shall preserve controllability."
}
@enduml
"""


def test_canonical_requirements_do_not_emit_native_uml_requirement() -> None:
    result = convert_plantuml(REQUIREMENTS, profile="canonical")

    assert result.diagram_type == "requirements"
    assert result.validation.ok
    assert "uml:Requirement" not in result.xmi
    assert 'xmi:type="uml:Class"' in result.xmi
    assert "Requirement; id=REQ-SAFE-001" in result.xmi
    assert 'xmi:type="uml:Constraint"' in result.xmi
    assert validate_xmi(result.xmi, profile="canonical").ok


def test_ea_requirements_use_requirement_extension_metadata() -> None:
    result = convert_plantuml(REQUIREMENTS, profile="ea")

    assert result.validation.ok
    assert "uml:Requirement" not in result.xmi
    assert 'extender="Enterprise Architect"' in result.xmi
    assert 'type="Requirement"' in result.xmi
    assert 'sType="Requirement"' in result.xmi
    assert 'name="id" value="REQ-SAFE-001"' in result.xmi
    assert 'name="text" value="The scheduler shall enter safe state after a watchdog fault."' in result.xmi


def test_sysml_requirements_apply_sysml_profile_and_relationships() -> None:
    result = convert_plantuml(REQUIREMENTS, profile="sysml")

    assert result.validation.ok
    assert "uml:Requirement" not in result.xmi
    assert "SysML:Requirement" in result.xmi
    assert 'id="REQ-SAFE-001"' in result.xmi
    assert 'text="The scheduler shall enter safe state after a watchdog fault."' in result.xmi
    assert 'name="requirement"' in result.xmi
    assert "SysML:Satisfy" in result.xmi
    assert "SysML:Verify" in result.xmi
    assert "SysML:Refine" in result.xmi
    assert "SysML:Trace" in result.xmi
    assert 'name="containment"' in result.xmi
    assert validate_xmi(result.xmi, profile="sysml").ok
