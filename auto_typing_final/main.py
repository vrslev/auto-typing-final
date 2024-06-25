import argparse
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TextIO, cast

from ast_grep_py import Edit, SgNode, SgRoot

from auto_typing_final.finder import find_definitions_in_scope_grouped_by_name

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


def is_in_loop(node: SgNode) -> bool:
    return any(ancestor.kind() in {"for_statement", "while_statement"} for ancestor in node.ancestors())


def make_operation_from_assignments_to_one_name(nodes: list[SgNode]) -> Operation:
    value_assignments: list[Definition] = []

    for node in nodes:
        children = node.children()

        if node.kind() == "assignment" and not is_in_loop(node):
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


def make_edits_for_all_assignments_in_scope(node: SgNode) -> Iterable[Edit]:
    for assignments in find_definitions_in_scope_grouped_by_name(node):
        yield from make_edits_from_operation(make_operation_from_assignments_to_one_name(assignments))


def make_edits_for_all_functions(root: SgNode) -> Iterable[Edit]:
    for function in root.find_all(kind="function_definition"):
        yield from make_edits_for_all_assignments_in_scope(function)


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
