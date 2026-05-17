from pathlib import Path

from planttoxmi import convert_plantuml, inspect_plantuml, validate_xmi
ROOT = Path(__file__).resolve().parents[1] / "examples" / "safety-rtos" / "diagrams"


def test_safety_rtos_importable_diagrams_convert_to_ea_xmi() -> None:
    diagrams = sorted((ROOT / "importable").glob("*.puml"))
    expected_types = {
        "architecture_components.puml": "component",
        "application_integration_components.puml": "component",
        "developer_use_cases.puml": "usecase",
        "ecu_deployment.puml": "deployment",
        "fault_containment_sequence.puml": "sequence",
        "fault_triage_communication.puml": "communication",
        "kernel_classes.puml": "class",
        "kernel_composite_structure.puml": "composite",
        "kernel_services_components.puml": "component",
        "periodic_scheduling_sequence.puml": "sequence",
        "platform_services_components.puml": "component",
        "runtime_snapshot_object.puml": "object",
        "safety_architecture_packages.puml": "package",
        "safety_requirement_traceability.puml": "requirements",
        "safety_requirements.puml": "requirements",
        "safety_profile.puml": "profile",
        "safety_services_components.puml": "component",
        "scheduler_activity.puml": "activity",
        "scheduler_timing.puml": "timing",
        "startup_interaction_overview.puml": "interaction_overview",
        "startup_sequence.puml": "sequence",
        "task_lifecycle_state.puml": "state",
        "watchdog_recovery_sequence.puml": "sequence",
    }

    assert len(diagrams) == 23
    for diagram in diagrams:
        source = diagram.read_text(encoding="utf-8")
        inspection = inspect_plantuml(source)
        result = convert_plantuml(source, profile="ea")

        assert inspection.supported, diagram.name
        assert inspection.diagram_type == expected_types[diagram.name]
        assert result.diagram_type == expected_types[diagram.name]
        assert result.validation.ok, diagram.name
        assert validate_xmi(result.xmi, profile="ea").ok, diagram.name
