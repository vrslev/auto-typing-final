import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from ast_grep_py import SgNode

from auto_typing_final.finder import find_all_definitions_in_functions, has_global_identifier_with_name

ImportStyle = Literal["typing-final", "final"]


@dataclass
class ImportConfig:
    value: str
    outer_regex: re.Pattern[str]
    import_text: str
    import_identifier: str


IMPORT_STYLES_TO_IMPORT_CONFIGS: dict[ImportStyle, ImportConfig] = {
    "typing-final": ImportConfig(
        value="typing.Final",
        outer_regex=re.compile(r"typing\.Final\[(.*)\]{1}"),
        import_text="import typing",
        import_identifier="typing",
    ),
    "final": ImportConfig(
        value="Final",
        outer_regex=re.compile(r"Final\[(.*)\]{1}"),
        import_text="from typing import Final",
        import_identifier="Final",
    ),
}


@dataclass
class AssignmentWithoutAnnotation:
    node: SgNode
    left: str
    right: str


@dataclass
class AssignmentWithAnnotation:
    node: SgNode
    left: str
    annotation: str
    right: str


@dataclass
class OtherDefinition:
    node: SgNode


Definition = AssignmentWithoutAnnotation | AssignmentWithAnnotation | OtherDefinition


@dataclass
class AddFinal:
    definition: Definition


@dataclass
class RemoveFinal:
    nodes: list[Definition]


Operation = AddFinal | RemoveFinal


def _make_operation_from_assignments_to_one_name(nodes: list[SgNode]) -> Operation:
    value_assignments: list[Definition] = []
    has_node_inside_loop = False

    for node in nodes:
        if any(ancestor.kind() in {"for_statement", "while_statement"} for ancestor in node.ancestors()):
            has_node_inside_loop = True

        if node.kind() == "assignment":
            match tuple((child.kind(), child) for child in node.children()):
                case (("identifier", left), ("=", _), (_, right)):
                    value_assignments.append(
                        AssignmentWithoutAnnotation(node=node, left=left.text(), right=right.text())
                    )
                case (("identifier", left), (":", _), ("type", annotation), ("=", _), (_, right)):
                    value_assignments.append(
                        AssignmentWithAnnotation(
                            node=node, left=left.text(), annotation=annotation.text(), right=right.text()
                        )
                    )
                case _:
                    value_assignments.append(OtherDefinition(node))
        else:
            value_assignments.append(OtherDefinition(node))

    if has_node_inside_loop:
        return RemoveFinal(value_assignments)

    match value_assignments:
        case [assignment]:
            return AddFinal(assignment)
        case assignments:
            return RemoveFinal(assignments)


def _make_changed_text_from_operation(  # noqa: C901
    operation: Operation, final_value: str, final_outer_regex: re.Pattern[str]
) -> Iterable[tuple[SgNode, str]]:
    match operation:
        case AddFinal(assignment):
            match assignment:
                case AssignmentWithoutAnnotation(node, left, right):
                    yield node, f"{left}: {final_value} = {right}"
                case AssignmentWithAnnotation(node, left, annotation, right):
                    if final_value not in annotation:
                        yield node, f"{left}: {final_value}[{annotation}] = {right}"

        case RemoveFinal(assignments):
            for assignment in assignments:
                match assignment:
                    case AssignmentWithoutAnnotation(node, left, right):
                        yield node, f"{left} = {right}"
                    case AssignmentWithAnnotation(node, left, annotation, right):
                        if annotation == final_value:
                            yield node, f"{left} = {right}"
                        elif new_annotation := final_outer_regex.findall(annotation):
                            yield node, f"{left}: {new_annotation[0]} = {right}"


@dataclass
class Edit:
    node: SgNode
    new_text: str


@dataclass
class Replacement:
    operation_type: type[Operation]
    edits: list[Edit]


@dataclass
class MakeReplacementsResult:
    replacements: list[Replacement]
    import_text: str | None


def make_replacements(root: SgNode, import_config: ImportConfig) -> MakeReplacementsResult:
    replacements = []
    has_added_final = False

    for current_definitions in find_all_definitions_in_functions(root):
        operation = _make_operation_from_assignments_to_one_name(current_definitions)
        edits = [
            Edit(node=node, new_text=new_text)
            for node, new_text in _make_changed_text_from_operation(
                operation=operation,
                final_value=import_config.value,
                final_outer_regex=import_config.outer_regex,
            )
            if node.text() != new_text
        ]

        if (operation_type := type(operation)) == AddFinal and edits:
            has_added_final = True

        replacements.append(Replacement(operation_type=operation_type, edits=edits))

    return MakeReplacementsResult(
        replacements=replacements,
        import_text=(
            import_config.import_text
            if has_added_final and not has_global_identifier_with_name(root=root, name=import_config.import_identifier)
            else None
        ),
    )
