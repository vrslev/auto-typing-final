import re
from collections.abc import Iterable
from dataclasses import dataclass

from ast_grep_py import Edit, SgNode, SgRoot

from auto_typing_final.finder import find_definitions_in_module

TYPING_FINAL = "typing.Final"
TYPING_FINAL_ANNOTATION_REGEX = re.compile(r"typing\.Final\[(.*)\]{1}")


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


def is_inside_loop(node: SgNode) -> bool:
    return any(ancestor.kind() in {"for_statement", "while_statement"} for ancestor in node.ancestors())


def make_operation_from_assignments_to_one_name(nodes: list[SgNode]) -> Operation:
    value_assignments: list[Definition] = []
    has_node_inside_loop = False

    for node in nodes:
        if is_inside_loop(node):
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


def make_edits_from_operation(operation: Operation) -> Iterable[Edit]:  # noqa: C901
    match operation:
        case AddFinal(assignment):
            match assignment:
                case AssignmentWithoutAnnotation(node, left, right):
                    yield node.replace(f"{left}: {TYPING_FINAL} = {right}")
                case AssignmentWithAnnotation(node, left, annotation, right):
                    if TYPING_FINAL in annotation:
                        return
                    yield node.replace(f"{left}: {TYPING_FINAL}[{annotation}] = {right}")

        case RemoveFinal(assignments):
            for assignment in assignments:
                match assignment:
                    case AssignmentWithoutAnnotation(node, left, right):
                        yield node.replace(f"{left} = {right}")
                    case AssignmentWithAnnotation(node, left, annotation, right):
                        if annotation == TYPING_FINAL:
                            yield node.replace(f"{left} = {right}")
                        elif new_annotation := TYPING_FINAL_ANNOTATION_REGEX.findall(annotation):
                            yield node.replace(f"{left}: {new_annotation[0]} = {right}")


def make_edits_for_definitions(definitions: Iterable[list[SgNode]]) -> Iterable[Edit]:
    for current_definitions in definitions:
        yield from make_edits_from_operation(make_operation_from_assignments_to_one_name(current_definitions))


def transform_file_content(source: str) -> str:
    root = SgRoot(source, "python").root()
    edits = list(make_edits_for_definitions(find_definitions_in_module(root)))
    return root.commit_edits(edits)
