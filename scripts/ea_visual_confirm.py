from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiagramResult:
    plantuml: Path
    xmi: Path
    diagram_name: str
    diagram_type: str
    image: Path
    objects: int
    links: int
    image_bytes: int


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import PlantUML diagrams into EA, export rendered diagram images, and write a visual confirmation report."
    )
    parser.add_argument("--template", required=True, help="Blank EA .qea/.eap repository template.")
    parser.add_argument("--input", required=True, help="PlantUML file or directory containing .puml/.plantuml files.")
    parser.add_argument("--output-dir", required=True, help="Directory for repository, XMI, images, and report.")
    parser.add_argument("--repository-name", default="visual-confirmation.qea")
    parser.add_argument("--image-format", choices=["png", "svg"], default="png")
    parser.add_argument("--keep-existing", action="store_true", help="Do not delete an existing output directory.")
    args = parser.parse_args()

    template = Path(args.template).resolve()
    input_path = Path(args.input).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not template.exists():
        raise SystemExit(f"Template repository not found: {template}")
    if not input_path.exists():
        raise SystemExit(f"Input path not found: {input_path}")
    if output_dir.exists() and not args.keep_existing:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    puml_files = _collect_puml_files(input_path)
    if not puml_files:
        raise SystemExit(f"No PlantUML files found under {input_path}")

    repository = output_dir / args.repository_name
    shutil.copy2(template, repository)
    xmi_dir = output_dir / "xmi"
    image_dir = output_dir / "images"
    xmi_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    results = _run_ea_workflow(
        repository=repository,
        puml_files=puml_files,
        xmi_dir=xmi_dir,
        image_dir=image_dir,
        image_format=args.image_format,
    )
    _write_report(output_dir, repository, results)

    payload = {
        "ok": True,
        "repository": str(repository),
        "report": str(output_dir / "visual-confirmation.md"),
        "images": [str(result.image) for result in results],
        "diagram_count": len(results),
    }
    print(json.dumps(payload, indent=2))


def _collect_puml_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted(
        [
            *input_path.rglob("*.puml"),
            *input_path.rglob("*.plantuml"),
        ]
    )


def _run_ea_workflow(
    repository: Path,
    puml_files: list[Path],
    xmi_dir: Path,
    image_dir: Path,
    image_format: str,
) -> list[DiagramResult]:
    try:
        import pythoncom
        import win32com.client
    except Exception as exc:
        raise SystemExit(f"pywin32 is required for EA visual confirmation: {exc!r}") from exc

    pythoncom.CoInitialize()
    ea = None
    try:
        ea = win32com.client.Dispatch("EA.Repository")
        if not ea.OpenFile(str(repository)):
            raise RuntimeError(f"EA could not open repository {repository}")
        project = ea.GetProjectInterface()
        root = ea.Models.GetAt(0)
        root_xml_guid = project.GUIDtoXML(root.PackageGUID)
        results: list[DiagramResult] = []

        for puml in puml_files:
            xmi = xmi_dir / f"{puml.stem}.xmi"
            _convert_to_xmi(puml, xmi)
            import_result = str(project.ImportPackageXMI(root_xml_guid, str(xmi), 1, 1) or "")
            if not _is_import_success(import_result):
                raise RuntimeError(f"EA import failed for {puml}: {import_result}")

            package = ea.GetPackageByGuid(import_result) if import_result.strip() else root.Packages.GetAt(root.Packages.Count - 1)
            diagram, object_count, link_count = _create_diagram(ea, package, puml)
            image = image_dir / f"{puml.stem}.{image_format}"
            image_type = 4 if image_format == "svg" else 1
            exported = project.PutDiagramImageToFile(diagram.DiagramGUID, str(image), image_type)
            if not exported or not image.exists() or image.stat().st_size == 0:
                raise RuntimeError(f"EA did not export a non-empty diagram image for {puml}")

            results.append(
                DiagramResult(
                    plantuml=puml,
                    xmi=xmi,
                    diagram_name=diagram.Name,
                    diagram_type=diagram.Type,
                    image=image,
                    objects=object_count,
                    links=link_count,
                    image_bytes=image.stat().st_size,
                )
            )
        return results
    finally:
        if ea is not None:
            try:
                ea.CloseFile()
            except Exception:
                pass
            try:
                ea.Exit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def _convert_to_xmi(puml: Path, xmi: Path) -> None:
    from planttoxmi.orchestrator import Orchestrator

    result = Orchestrator().convert(
        puml.read_text(encoding="utf-8"),
        profile="ea",
        source_name=str(puml),
    )
    xmi.write_text(result.xmi, encoding="utf-8")


def _is_import_success(value: str) -> bool:
    stripped = value.strip()
    if stripped == "":
        return True
    if len(stripped) == 38 and stripped.startswith("{") and stripped.endswith("}"):
        return all(char in "0123456789abcdefABCDEF-" for char in stripped[1:-1])
    return False


def _create_diagram(ea, package, puml: Path):
    diagram_type = _ea_diagram_type_for_puml(puml) or _detect_diagram_type(package)
    if not diagram_type:
        raise RuntimeError(f"Could not infer EA diagram type for imported package {package.Name}")
    diagram = package.Diagrams.AddNew(_unique_diagram_name(package, puml.stem), diagram_type)
    diagram.Update()
    if diagram_type == "Sequence":
        object_count, link_count = _add_sequence_objects_and_links(package, diagram, puml)
    elif diagram_type == "Requirements":
        object_count, link_count = _add_requirement_objects_and_links(package, diagram, puml)
    else:
        object_count, link_count = _add_generic_objects_and_links(package, diagram, puml)
    diagram.Update()
    package.Update()
    ea.ReloadDiagram(diagram.DiagramID)
    return diagram, object_count, link_count


def _ea_diagram_type_for_puml(puml: Path) -> str:
    from planttoxmi.orchestrator import Orchestrator

    diagram_type = Orchestrator().inspect(puml.read_text(encoding="utf-8")).diagram_type
    return {
        "activity": "Activity",
        "class": "Class",
        "communication": "Communication",
        "component": "Component",
        "composite": "CompositeStructure",
        "deployment": "Deployment",
        "interaction_overview": "InteractionOverview",
        "object": "Object",
        "package": "Package",
        "profile": "Profile",
        "requirements": "Requirements",
        "sequence": "Sequence",
        "state": "Statechart",
        "timing": "Timing",
        "usecase": "Use Case",
    }.get(diagram_type, "")


def _detect_diagram_type(package) -> str:
    for index in range(package.Elements.Count):
        element = package.Elements.GetAt(index)
        if element.Type == "Interaction":
            return "Sequence"
    for index in range(package.Elements.Count):
        element = package.Elements.GetAt(index)
        if element.Type in {"Component", "Interface", "Class"}:
            return "Component"
    return ""


def _unique_diagram_name(package, base_name: str) -> str:
    existing = {package.Diagrams.GetAt(index).Name.lower() for index in range(package.Diagrams.Count)}
    candidate = base_name or "PlantUML Import"
    suffix = 2
    while candidate.lower() in existing:
        candidate = f"{base_name} {suffix}"
        suffix += 1
    return candidate


def _add_generic_objects_and_links(package, diagram, puml: Path) -> tuple[int, int]:
    from planttoxmi.agents.registry import build_registry
    from planttoxmi.detector import detect_diagram_type

    source = puml.read_text(encoding="utf-8")
    diagram_type = detect_diagram_type(source)
    model = build_registry()[diagram_type].parse(source, source_name=str(puml))
    ea_by_name = _existing_elements_by_name(package)
    nodes = []
    model_nodes = [*model.elements, *model.requirements]
    for element in model_nodes:
        ea_element = ea_by_name.get(element.name) or ea_by_name.get(element.alias or "")
        if ea_element is None:
            ea_element = _create_ea_element(package, element.name, getattr(element, "kind", "requirement"))
            ea_by_name[element.name] = ea_element
            if element.alias:
                ea_by_name[element.alias] = ea_element
        nodes.append(ea_element)

    columns = max(2, min(4, math.ceil(math.sqrt(max(len(nodes), 1)))))
    for index, element in enumerate(nodes):
        column = index % columns
        row = index // columns
        _add_diagram_object(diagram, element.ElementID, 40 + column * 230, 40 + row * 150, 150, 80)
    created_links = _add_model_connectors(model, ea_by_name, diagram)
    created_links += _add_existing_connectors(package, diagram)
    return len(nodes), created_links or diagram.DiagramLinks.Count


def _add_requirement_objects_and_links(package, diagram, puml: Path) -> tuple[int, int]:
    from planttoxmi.agents.registry import build_registry

    source = puml.read_text(encoding="utf-8")
    model = build_registry()["requirements"].parse(source, source_name=str(puml))
    if model.elements or any(relationship.kind != "containment" for relationship in model.relationships):
        return _add_generic_objects_and_links(package, diagram, puml)

    ea_by_name = _existing_elements_by_name(package)
    requirement_by_id = {requirement.id: requirement for requirement in model.requirements}
    ea_by_id = {}

    for requirement in model.requirements:
        ea_element = ea_by_name.get(requirement.name) or ea_by_name.get(requirement.alias or "")
        if ea_element is None or getattr(ea_element, "Type", "") != "Requirement":
            ea_element = _create_ea_element(package, requirement.name, "requirement")
        _configure_ea_requirement(ea_element, requirement)
        ea_by_name[requirement.name] = ea_element
        if requirement.alias:
            ea_by_name[requirement.alias] = ea_element
        ea_by_id[requirement.id] = ea_element

    _remove_imported_requirement_placeholders(package, model.requirements)

    containment = [
        relationship
        for relationship in model.relationships
        if relationship.kind == "containment"
        and relationship.source in requirement_by_id
        and relationship.target in requirement_by_id
    ]
    levels = _requirement_levels(model.requirements, containment)
    for level, requirements in sorted(levels.items()):
        count = len(requirements)
        for index, requirement in enumerate(requirements):
            element = ea_by_id[requirement.id]
            left = 60 + index * 310 + max(0, 4 - count) * 130
            top = 40 + level * 170
            _add_diagram_object(diagram, element.ElementID, left, top, 260, 110)

    created_links = 0
    for relationship in containment:
        src = ea_by_id.get(relationship.source)
        tgt = ea_by_id.get(relationship.target)
        if src is None or tgt is None:
            continue
        try:
            connector = src.Connectors.AddNew("", "Aggregation")
            connector.SupplierID = tgt.ElementID
            connector.Direction = "Source -> Destination"
            try:
                connector.ClientEnd.Aggregation = 1
            except Exception:
                pass
            connector.Update()
            src.Connectors.Refresh()
            link = diagram.DiagramLinks.AddNew("", "")
            link.ConnectorID = connector.ConnectorID
            link.Update()
            created_links += 1
        except Exception:
            pass
    return len(model.requirements), created_links or diagram.DiagramLinks.Count


def _remove_imported_requirement_placeholders(package, requirements) -> None:
    requirement_names = {requirement.name for requirement in requirements}
    requirement_aliases = {requirement.alias for requirement in requirements if requirement.alias}
    for index in range(package.Elements.Count - 1, -1, -1):
        element = package.Elements.GetAt(index)
        if element.Type == "Requirement":
            continue
        if element.Name in requirement_names or element.Name in requirement_aliases:
            package.Elements.DeleteAt(index, False)
    package.Elements.Refresh()


def _requirement_levels(requirements, containment) -> dict[int, list[object]]:
    by_id = {requirement.id: requirement for requirement in requirements}
    children_by_parent: dict[str, list[str]] = {}
    child_ids = set()
    for relationship in containment:
        children_by_parent.setdefault(relationship.source, []).append(relationship.target)
        child_ids.add(relationship.target)

    roots = [requirement.id for requirement in requirements if requirement.id not in child_ids]
    if not roots:
        roots = [requirement.id for requirement in requirements]
    levels: dict[int, list[object]] = {}
    visited = set()
    frontier = [(root, 0) for root in roots]
    while frontier:
        requirement_id, level = frontier.pop(0)
        if requirement_id in visited:
            continue
        visited.add(requirement_id)
        requirement = by_id.get(requirement_id)
        if requirement is None:
            continue
        levels.setdefault(level, []).append(requirement)
        for child_id in children_by_parent.get(requirement_id, []):
            frontier.append((child_id, level + 1))
    for requirement in requirements:
        if requirement.id not in visited:
            levels.setdefault(0, []).append(requirement)
    return levels


def _existing_elements_by_name(package) -> dict[str, object]:
    elements = {}
    for index in range(package.Elements.Count):
        element = package.Elements.GetAt(index)
        elements[element.Name] = element
    return elements


def _create_ea_element(package, name: str, kind: str):
    ea_type = {
        "activity": "Activity",
        "actor": "Actor",
        "artifact": "Artifact",
        "class": "Class",
        "clock": "Class",
        "component": "Component",
        "constraint": "Constraint",
        "interface": "Interface",
        "lifeline": "Class",
        "node": "Node",
        "object": "Object",
        "package": "Package",
        "participant": "Class",
        "port": "Port",
        "profile": "Class",
        "requirement": "Requirement",
        "state": "State",
        "stereotype": "Class",
        "usecase": "UseCase",
    }.get(kind, "Class")
    element = package.Elements.AddNew(name, ea_type)
    element.Update()
    package.Elements.Refresh()
    return element


def _configure_ea_requirement(element, requirement) -> None:
    try:
        element.Name = (
            f"{requirement.requirement_id} {requirement.name}"
            if requirement.requirement_id and not requirement.name.startswith(requirement.requirement_id)
            else requirement.name
        )
        element.Notes = requirement.text or ""
        element.Stereotype = "requirement"
        element.Update()
    except Exception:
        pass


def _add_model_connectors(model, ea_by_name: dict[str, object], diagram) -> int:
    ir_by_id = {element.id: element for element in [*model.elements, *model.requirements]}
    created = 0
    for relationship in model.relationships:
        src_ir = ir_by_id.get(relationship.source)
        tgt_ir = ir_by_id.get(relationship.target)
        if src_ir is None or tgt_ir is None:
            continue
        src = ea_by_name.get(src_ir.name) or ea_by_name.get(src_ir.alias or "")
        tgt = ea_by_name.get(tgt_ir.name) or ea_by_name.get(tgt_ir.alias or "")
        if src is None or tgt is None:
            continue
        connector_type = "Association" if relationship.kind in {"association", "containment"} else "Dependency"
        try:
            connector = src.Connectors.AddNew(relationship.name or "", connector_type)
            connector.SupplierID = tgt.ElementID
            connector.Direction = "Source -> Destination"
            connector.Update()
            src.Connectors.Refresh()
            link = diagram.DiagramLinks.AddNew("", "")
            link.ConnectorID = connector.ConnectorID
            link.Update()
            created += 1
        except Exception:
            pass
    return created


def _add_existing_connectors(package, diagram) -> int:
    created = 0
    seen: set[int] = set()
    for index in range(package.Elements.Count):
        element = package.Elements.GetAt(index)
        for connector_index in range(element.Connectors.Count):
            connector = element.Connectors.GetAt(connector_index)
            if connector.ConnectorID in seen:
                continue
            seen.add(connector.ConnectorID)
            try:
                link = diagram.DiagramLinks.AddNew("", "")
                link.ConnectorID = connector.ConnectorID
                link.Update()
                created += 1
            except Exception:
                pass
    return created


def _add_sequence_objects_and_links(package, diagram, puml: Path) -> tuple[int, int]:
    from planttoxmi.agents.sequence import SequenceAgent

    model = SequenceAgent().parse(puml.read_text(encoding="utf-8"), source_name=str(puml))
    interaction = model.interactions[0]
    ir_lifelines = {lifeline.id: lifeline for lifeline in interaction.lifelines}

    ea_lifelines_by_name = {}
    for index in range(package.Elements.Count):
        ea_interaction = package.Elements.GetAt(index)
        if ea_interaction.Type != "Interaction":
            continue
        for child_index in range(ea_interaction.Elements.Count):
            lifeline = ea_interaction.Elements.GetAt(child_index)
            if lifeline.Type not in {"Sequence", "Actor", "Object"}:
                continue
            ea_lifelines_by_name[lifeline.Name] = lifeline

    ordered_lifelines = [
        ea_lifelines_by_name[lifeline.name]
        for lifeline in interaction.lifelines
        if lifeline.name in ea_lifelines_by_name
    ]
    for index, lifeline in enumerate(ordered_lifelines):
        _add_diagram_object(diagram, lifeline.ElementID, 40 + index * 145, 30, 112, 420)

    created_links = 0
    for sequence, message in enumerate(interaction.messages, start=1):
        source_ir = ir_lifelines.get(message.source)
        target_ir = ir_lifelines.get(message.target)
        if source_ir is None or target_ir is None:
            continue
        source = ea_lifelines_by_name.get(source_ir.name)
        target = ea_lifelines_by_name.get(target_ir.name)
        if source is None or target is None:
            continue

        connector = source.Connectors.AddNew(message.name, "Sequence")
        connector.SupplierID = target.ElementID
        connector.Direction = "Source -> Destination"
        try:
            connector.SequenceNo = sequence
        except Exception:
            pass
        connector.Update()
        source.Connectors.Refresh()

        link = diagram.DiagramLinks.AddNew("", "")
        link.ConnectorID = connector.ConnectorID
        link.Geometry = "EDGE=3;"
        link.Update()
        created_links += 1
    return len(ordered_lifelines), created_links


def _message_order(name: str) -> int:
    tail = (name or "").split()[-1:]
    if tail and tail[0].isdigit():
        return int(tail[0])
    return 999_999


def _add_diagram_object(diagram, element_id: int, left: int, top: int, width: int, height: int) -> None:
    ea_top = -top
    ea_bottom = -(top + height)
    diagram_object = diagram.DiagramObjects.AddNew(
        f"l={left};r={left + width};t={ea_top};b={ea_bottom};",
        "",
    )
    diagram_object.ElementID = element_id
    diagram_object.Update()


def _write_report(output_dir: Path, repository: Path, results: list[DiagramResult]) -> None:
    lines = [
        "# EA Visual Confirmation Report",
        "",
        f"Repository: `{repository}`",
        "",
        "| PlantUML | Diagram | Type | Objects | Links | Image | Size |",
        "| --- | --- | --- | ---: | ---: | --- | ---: |",
    ]
    for result in results:
        image_rel = result.image.relative_to(output_dir).as_posix()
        lines.append(
            f"| `{result.plantuml.name}` | {result.diagram_name} | {result.diagram_type} | "
            f"{result.objects} | {result.links} | [{result.image.name}]({image_rel}) | {result.image_bytes} |"
        )
    lines.append("")
    for result in results:
        image_rel = result.image.relative_to(output_dir).as_posix()
        lines.extend([f"## {result.diagram_name}", "", f"![{result.diagram_name}]({image_rel})", ""])
    (output_dir / "visual-confirmation.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
