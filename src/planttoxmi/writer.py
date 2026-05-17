from __future__ import annotations

from lxml import etree

from planttoxmi.ids import stable_id
from planttoxmi.ir import UMLComment, UMLElement, UMLModel, UMLRelationship, UMLRequirement
from planttoxmi.types import OutputProfile

XMI_NS = "http://www.omg.org/spec/XMI/20110701"
UML_NS = "http://www.eclipse.org/uml2/2.1.0/UML"
SYSML_NS = "http://www.omg.org/spec/SysML/20100301/SysML"
XMI_TYPE = f"{{{XMI_NS}}}type"
XMI_ID = f"{{{XMI_NS}}}id"
XMI_IDREF = f"{{{XMI_NS}}}idref"
XMI_VERSION = f"{{{XMI_NS}}}version"


def serialize_xmi(model: UMLModel, profile: OutputProfile = "canonical") -> str:
    root = etree.Element(
        f"{{{XMI_NS}}}XMI",
        nsmap=_namespace_map(profile),
    )
    root.set(XMI_VERSION, "2.1")
    documentation = etree.SubElement(root, f"{{{XMI_NS}}}Documentation")
    documentation.set("exporter", "planttoxmi")
    documentation.set("exporterVersion", "0.1.0")
    documentation.set("profile", profile)

    uml_model = etree.SubElement(root, f"{{{UML_NS}}}Model")
    uml_model.set(XMI_ID, model.id)
    uml_model.set("name", model.name)

    for element in model.elements:
        _write_packaged_element(uml_model, element)
    for requirement in model.requirements:
        _write_requirement(uml_model, requirement, profile)
    for relationship in model.relationships:
        _write_relationship(uml_model, relationship)
    for comment in model.comments:
        _write_comment(uml_model, comment)
    for interaction in model.interactions:
        interaction_el = etree.SubElement(uml_model, "packagedElement")
        interaction_el.set(XMI_TYPE, "uml:Interaction")
        interaction_el.set(XMI_ID, interaction.id)
        interaction_el.set("name", interaction.name)
        for lifeline in interaction.lifelines:
            line = etree.SubElement(interaction_el, "lifeline")
            line.set(XMI_ID, lifeline.id)
            line.set("name", lifeline.name)
            if lifeline.kind == "actor":
                line.set("represents", lifeline.id)
        for message in interaction.messages:
            msg = etree.SubElement(interaction_el, "message")
            msg.set(XMI_ID, message.id)
            msg.set("name", message.name)
            msg.set("messageSort", message.kind)
            msg.set("sendEvent", message.source)
            msg.set("receiveEvent", message.target)
        for comment in interaction.comments:
            _write_comment(interaction_el, comment)

    if profile == "sysml":
        _write_sysml_profile_application(uml_model)
        for requirement in model.requirements:
            _write_sysml_requirement_application(root, requirement)
        for relationship in model.relationships:
            _write_sysml_relationship_application(root, relationship)

    if profile == "ea":
        extension = etree.SubElement(root, f"{{{XMI_NS}}}Extension")
        extension.set("extender", "Enterprise Architect")
        extension.set("extenderID", "planttoxmi")
        etree.SubElement(extension, "profiles").set("xmiProfile", "EA-friendly")
        _write_ea_requirements_extension(extension, model.requirements)

    return etree.tostring(root, encoding="unicode", pretty_print=True, xml_declaration=False)


def _namespace_map(profile: OutputProfile) -> dict[str, str]:
    nsmap = {"xmi": XMI_NS, "uml": UML_NS}
    if profile == "sysml":
        nsmap["SysML"] = SYSML_NS
    return nsmap


def _write_packaged_element(parent: etree._Element, element: UMLElement) -> None:
    node = etree.SubElement(parent, "packagedElement")
    node.set(
        XMI_TYPE,
        {
            "activity": "uml:Activity",
            "component": "uml:Component",
            "artifact": "uml:Artifact",
            "class": "uml:Class",
            "clock": "uml:Class",
            "constraint": "uml:Constraint",
            "interface": "uml:Interface",
            "actor": "uml:Actor",
            "lifeline": "uml:Class",
            "node": "uml:Node",
            "object": "uml:InstanceSpecification",
            "package": "uml:Package",
            "participant": "uml:Class",
            "port": "uml:Port",
            "profile": "uml:Profile",
            "state": "uml:State",
            "stereotype": "uml:Stereotype",
            "usecase": "uml:UseCase",
        }[element.kind],
    )
    node.set(XMI_ID, element.id)
    node.set("name", element.name)
    _write_stereotypes(node, element.stereotypes)


def _write_requirement(parent: etree._Element, requirement: UMLRequirement, profile: OutputProfile) -> None:
    node = etree.SubElement(parent, "packagedElement")
    node.set(XMI_TYPE, "uml:Class")
    node.set(XMI_ID, requirement.id)
    node.set("name", requirement.name)
    if profile in {"ea", "sysml"}:
        _write_stereotypes(node, ("requirement",))
    if profile == "sysml":
        _write_requirement_attribute(node, requirement, "id", requirement.requirement_id or requirement.name)
        _write_requirement_attribute(node, requirement, "text", requirement.text or "")
    else:
        comment_body = _requirement_comment(requirement)
        _write_comment(
            node,
            UMLComment(
                id=stable_id(requirement.id, "requirement_comment"),
                body=comment_body,
                annotated_element=requirement.id,
            ),
        )
        constraint = etree.SubElement(node, "ownedRule")
        constraint.set(XMI_TYPE, "uml:Constraint")
        constraint.set(XMI_ID, stable_id(requirement.id, "requirement_constraint"))
        constraint.set("name", requirement.requirement_id or requirement.name)
        specification = etree.SubElement(constraint, "specification")
        specification.set(XMI_TYPE, "uml:OpaqueExpression")
        specification.set(XMI_ID, stable_id(requirement.id, "requirement_constraint_spec"))
        specification.set("body", requirement.text or "")


def _write_requirement_attribute(
    parent: etree._Element,
    requirement: UMLRequirement,
    name: str,
    value: str,
) -> None:
    attribute = etree.SubElement(parent, "ownedAttribute")
    attribute.set(XMI_ID, stable_id(requirement.id, "attribute", name))
    attribute.set("name", name)
    default = etree.SubElement(attribute, "defaultValue")
    default.set(XMI_TYPE, "uml:LiteralString")
    default.set(XMI_ID, stable_id(requirement.id, "attribute", name, "value"))
    default.set("value", value)


def _requirement_comment(requirement: UMLRequirement) -> str:
    parts = ["Requirement"]
    if requirement.requirement_id:
        parts.append(f"id={requirement.requirement_id}")
    if requirement.text:
        parts.append(f"text={requirement.text}")
    return "; ".join(parts)


def _write_relationship(parent: etree._Element, relationship: UMLRelationship) -> None:
    rel = etree.SubElement(parent, "packagedElement")
    uml_type = {
        "association": "uml:Association",
        "dependency": "uml:Dependency",
        "realization": "uml:Realization",
        "trace": "uml:Dependency",
        "refine": "uml:Dependency",
        "satisfy": "uml:Dependency",
        "verify": "uml:Dependency",
        "derive": "uml:Dependency",
        "containment": "uml:Association",
    }[relationship.kind]
    rel.set(XMI_TYPE, uml_type)
    rel.set(XMI_ID, relationship.id)
    if relationship.name:
        rel.set("name", relationship.name)
    rel.set("client", relationship.source)
    rel.set("supplier", relationship.target)
    _write_stereotypes(rel, relationship.stereotypes)


def _write_stereotypes(parent: etree._Element, stereotypes: tuple[str, ...]) -> None:
    for stereotype in stereotypes:
        child = etree.SubElement(parent, "appliedStereotype")
        child.set("name", stereotype)


def _write_comment(parent: etree._Element, comment: UMLComment) -> None:
    node = etree.SubElement(parent, "ownedComment")
    node.set(XMI_ID, comment.id)
    node.set("body", comment.body)
    if comment.annotated_element:
        node.set("annotatedElement", comment.annotated_element)


def _write_sysml_profile_application(uml_model: etree._Element) -> None:
    application = etree.SubElement(uml_model, "profileApplication")
    application.set(XMI_ID, stable_id(uml_model.get(XMI_ID, "model"), "sysml_profile_application"))
    applied_profile = etree.SubElement(application, "appliedProfile")
    applied_profile.set("href", "http://www.omg.org/spec/SysML/20100301/SysML.profile.uml#SysML")


def _write_sysml_requirement_application(root: etree._Element, requirement: UMLRequirement) -> None:
    node = etree.SubElement(root, f"{{{SYSML_NS}}}Requirement")
    node.set(XMI_ID, stable_id(requirement.id, "sysml_requirement"))
    node.set("base_Class", requirement.id)
    node.set("id", requirement.requirement_id or requirement.name)
    node.set("text", requirement.text or "")


def _write_sysml_relationship_application(root: etree._Element, relationship: UMLRelationship) -> None:
    names = {
        "trace": "Trace",
        "refine": "Refine",
        "satisfy": "Satisfy",
        "verify": "Verify",
        "derive": "DeriveReqt",
    }
    name = names.get(relationship.kind)
    if not name:
        return
    node = etree.SubElement(root, f"{{{SYSML_NS}}}{name}")
    node.set(XMI_ID, stable_id(relationship.id, "sysml", relationship.kind))
    node.set("base_Dependency", relationship.id)


def _write_ea_requirements_extension(
    extension: etree._Element,
    requirements: tuple[UMLRequirement, ...],
) -> None:
    if not requirements:
        return
    elements = etree.SubElement(extension, "elements")
    for requirement in requirements:
        element = etree.SubElement(elements, "element")
        element.set(XMI_ID, stable_id(requirement.id, "ea_element"))
        element.set(XMI_IDREF, requirement.id)
        element.set("name", requirement.name)
        element.set("type", "Requirement")
        element.set("stereotype", "requirement")
        properties = etree.SubElement(element, "properties")
        properties.set("sType", "Requirement")
        tags = etree.SubElement(element, "taggedValues")
        if requirement.requirement_id:
            tag = etree.SubElement(tags, "tag")
            tag.set("name", "id")
            tag.set("value", requirement.requirement_id)
        if requirement.text:
            tag = etree.SubElement(tags, "tag")
            tag.set("name", "text")
            tag.set("value", requirement.text)
