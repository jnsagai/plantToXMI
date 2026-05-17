from __future__ import annotations

import re

from planttoxmi.agents.base import DiagramAgent
from planttoxmi.ids import stable_id
from planttoxmi.ir import UMLElement, UMLComment, UMLInteraction, UMLMessage, UMLModel
from planttoxmi.types import Diagnostic, PlantToXMIError

PARTICIPANT_RE = re.compile(
    r'^(?P<kind>actor|participant|boundary|control|entity|database|collections|queue)\s+'
    r'(?:"(?P<quoted>[^"]+)"|(?P<name>[A-Za-z_][\w.-]*))(?:\s+as\s+(?P<alias>[A-Za-z_][\w-]*))?',
    re.I,
)
MESSAGE_RE = re.compile(
    r'^(?P<src>[A-Za-z_][\w-]*)\s*(?P<arrow>[-.]+(?:>>?|x)|(?:<<|<)[-.]+)\s*'
    r'(?P<tgt>[A-Za-z_][\w-]*)(?:\s*:\s*(?P<label>.*))?$'
)
NOTE_RE = re.compile(r"^note\s+(?:over|left of|right of)\s+(?P<target>[A-Za-z_][\w-]*)?.*$", re.I)


class SequenceAgent(DiagramAgent):
    diagram_type = "sequence"
    supported_features = (
        "participants",
        "actors",
        "messages",
        "create/destroy",
        "return messages",
        "notes",
        "group warnings",
    )

    def parse(self, source: str, source_name: str = "plantuml") -> UMLModel:
        lifelines: dict[str, UMLElement] = {}
        messages: list[UMLMessage] = []
        comments: list[UMLComment] = []
        warnings: list[str] = []
        diagnostics: list[Diagnostic] = []
        note_target: str | None = None
        note_lines: list[str] = []

        for line_number, raw in enumerate(source.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("'") or line.lower() in {"@startuml", "@enduml"}:
                continue
            if note_lines:
                if line.lower() == "end note":
                    comments.append(
                        UMLComment(
                            id=stable_id(source_name, "sequence_comment", line_number),
                            body="\n".join(note_lines).strip(),
                            annotated_element=self._line_id(note_target, lifelines),
                        )
                    )
                    note_lines = []
                    note_target = None
                else:
                    note_lines.append(line)
                continue
            note_match = NOTE_RE.match(line)
            if note_match:
                if ":" in line:
                    comments.append(
                        UMLComment(
                            id=stable_id(source_name, "sequence_comment", line_number),
                            body=line.split(":", 1)[1].strip(),
                            annotated_element=self._line_id(note_match.group("target"), lifelines),
                        )
                    )
                else:
                    note_target = note_match.group("target")
                    note_lines = []
                continue
            part_match = PARTICIPANT_RE.match(line)
            if part_match:
                name = (part_match.group("quoted") or part_match.group("name") or "").strip()
                alias = part_match.group("alias") or name
                kind = "actor" if part_match.group("kind").lower() == "actor" else "participant"
                lifelines[alias] = UMLElement(
                    id=stable_id(source_name, "lifeline", alias),
                    name=name,
                    kind=kind,
                    alias=alias,
                )
                continue
            msg_match = MESSAGE_RE.match(line)
            if msg_match:
                src = self._ensure_lifeline(msg_match.group("src"), lifelines, source_name)
                tgt = self._ensure_lifeline(msg_match.group("tgt"), lifelines, source_name)
                arrow = msg_match.group("arrow")
                label = (msg_match.group("label") or "").strip()
                messages.append(
                    UMLMessage(
                        id=stable_id(source_name, "message", len(messages), src, tgt, label),
                        source=src,
                        target=tgt,
                        name=label,
                        kind=self._message_kind(arrow, label),
                    )
                )
                continue
            if line.lower().startswith(("activate ", "deactivate ", "alt", "else", "opt", "loop", "par", "group", "end")):
                warnings.append(f"Sequence control/grouping syntax preserved as a warning only: {line}")
                continue
            diagnostics.append(
                Diagnostic(
                    rule_id="parse.unsupported_construct",
                    message=f"Unsupported sequence diagram syntax: {line}",
                    line=line_number,
                )
            )

        if note_lines:
            diagnostics.append(
                Diagnostic(rule_id="parse.unclosed_note", message="A sequence note was not closed.")
            )
        if diagnostics:
            raise PlantToXMIError(diagnostics)

        interaction = UMLInteraction(
            id=stable_id(source_name, "interaction", "main"),
            name="PlantUML Sequence Interaction",
            lifelines=tuple(lifelines.values()),
            messages=tuple(messages),
            comments=tuple(comments),
        )
        return UMLModel(
            id=stable_id(source_name, "model", "sequence"),
            name="PlantUML Sequence Model",
            diagram_type="sequence",
            interactions=(interaction,),
            warnings=tuple(warnings),
        )

    def _ensure_lifeline(
        self, alias: str, lifelines: dict[str, UMLElement], source_name: str
    ) -> str:
        if alias not in lifelines:
            lifelines[alias] = UMLElement(
                id=stable_id(source_name, "lifeline", alias),
                name=alias,
                kind="participant",
                alias=alias,
            )
        return lifelines[alias].id

    def _line_id(self, alias: str | None, lifelines: dict[str, UMLElement]) -> str | None:
        if not alias:
            return None
        lifeline = lifelines.get(alias)
        return lifeline.id if lifeline else None

    def _message_kind(self, arrow: str, label: str) -> str:
        lower_label = label.lower()
        if "x" in arrow or lower_label.startswith("destroy"):
            return "deleteMessage"
        if lower_label.startswith("create"):
            return "createMessage"
        if "--" in arrow:
            return "reply"
        return "asynchCall" if ">>" in arrow else "synchCall"
