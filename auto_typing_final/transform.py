import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from ast_grep_py import Edit, SgNode

from auto_typing_final.finder import find_definitions_in_functions_in_node

TYPING_FINAL_VALUE = "typing.Final"
TYPING_FINAL_OUTER_REGEX = re.compile(r"typing\.Final\[(.*)\]{1}")
FINAL_VALUE = "Final"
FINAL_OUTER_REGEX = re.compile(r"Final\[(.*)\]{1}")


class ImportMode(Enum):
    typing_final = "typing-final"
    final = "final"


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
            children = node.children()
            match tuple(child.kind() for child in children):
                case ("identifier", "=", _):
                    value_assignments.append(
                        AssignmentWithoutAnnotation(node=node, left=children[0].text(), right=children[2].text())
                    )
                case ("identifier", ":", "type", "=", _):
                    value_assignments.append(
                        AssignmentWithAnnotation(
                            node=node, left=children[0].text(), annotation=children[2].text(), right=children[4].text()
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


def _make_changed_text_from_operation(operation: Operation, import_mode: ImportMode) -> Iterable[tuple[SgNode, str]]:  # noqa: C901, PLR0912
    if import_mode == ImportMode.typing_final:
        final_value = TYPING_FINAL_VALUE
        final_outer_regex = TYPING_FINAL_OUTER_REGEX
    elif import_mode == ImportMode.final:
        final_value = FINAL_VALUE
        final_outer_regex = FINAL_OUTER_REGEX
    else:
        msg = "unreachable"
        raise AssertionError(msg)

    match operation:
        case AddFinal(assignment):
            match assignment:
                case AssignmentWithoutAnnotation(node, left, right):
                    yield node, f"{left}: {final_value} = {right}"
                case AssignmentWithAnnotation(node, left, annotation, right):
                    if final_value in annotation:
                        return
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
class AppliedEdit:
    node: SgNode
    edit: Edit


@dataclass
class AppliedOperation:
    operation: Operation
    edits: list[AppliedEdit]


def make_operations_from_root(root: SgNode, import_mode: ImportMode) -> Iterable[AppliedOperation]:
    for current_definitions in find_definitions_in_functions_in_node(root):
        operation = _make_operation_from_assignments_to_one_name(current_definitions)
        yield AppliedOperation(
            operation=operation,
            edits=[
                AppliedEdit(node=node, edit=node.replace(new_text))
                for node, new_text in _make_changed_text_from_operation(operation, import_mode)
                if node.text() != new_text
            ],
        )
