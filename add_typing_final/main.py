import argparse
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TextIO, cast

from ast_grep_py import Edit, SgNode, SgRoot

# https://github.com/tree-sitter/tree-sitter-python/blob/71778c2a472ed00a64abf4219544edbf8e4b86d7/grammar.js


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


Assignment = AssignmentWithoutAnnotation | AssignmentWithAnnotation


@dataclass
class AddFinal:
    assignment: Assignment


@dataclass
class RemoveFinal:
    nodes: list[Assignment]


Operation = AddFinal | RemoveFinal


def make_operation_from_assignments_to_one_name(nodes: list[SgNode]) -> Operation:
    value_assignments: list[Assignment] = []

    for node in nodes:
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

    match value_assignments:
        case [assignment]:
            return AddFinal(assignment)
        case assignments:
            return RemoveFinal(assignments)


def convert_edits_from_operation(operation: Operation) -> Iterable[Edit]:  # noqa: C901
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


def find_assignments_not_in_function_or_class(node: SgNode) -> Iterable[SgNode]:
    if node.kind() == "assignment":
        yield node
    else:
        for child in node.children():
            if child.kind() not in {"function_definition", "class_definition"}:
                yield from find_assignments_not_in_function_or_class(child)


def find_assignments_grouped_by_name(node: SgNode) -> Iterable[list[SgNode]]:
    assignment_map: defaultdict[str, list[SgNode]] = defaultdict(list)
    for child in find_assignments_not_in_function_or_class(node):
        if left := child.field("left"):
            assignment_map[left.text()].append(child)
    return assignment_map.values()


def make_edits_for_all_assignments_in_scope(node: SgNode) -> Iterable[Edit]:
    for assignments in find_assignments_grouped_by_name(node):
        yield from convert_edits_from_operation(make_operation_from_assignments_to_one_name(assignments))


def make_edits_for_all_functions(root: SgNode) -> Iterable[Edit]:
    for function in root.find_all(kind="function_definition"):
        if body := function.field("body"):
            yield from make_edits_for_all_assignments_in_scope(body)


def run_fixer(source: str) -> str:
    root = SgRoot(source, "python").root()
    return root.commit_edits(list(make_edits_for_all_functions(root)))


def main() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=argparse.FileType("r+"), nargs="*")

    for file in cast(list[TextIO], parser.parse_args().files):
        data = file.read()
        file.seek(0)
        file.write(run_fixer(data))
        file.truncate()


if __name__ == "__main__":  # pragma: no cover
    main()
