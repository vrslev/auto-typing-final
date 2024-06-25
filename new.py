from collections import defaultdict
from collections.abc import Iterable
from typing import cast

from ast_grep_py import SgNode


def node_is_in_inner_function_or_class(root: SgNode, node: SgNode) -> bool:
    for ancestor in node.ancestors():
        if ancestor.kind() in {"function_definition", "class_definition"}:
            return ancestor != root
    return False


def find_identifiers_in_node(node: SgNode) -> Iterable[str]:
    match node.kind():
        case "assignment" | "augmented_assignment":
            if left := node.field("left"):
                match left.kind():
                    case "pattern_list" | "tuple_pattern":
                        for child in left.children():
                            if child.kind() == "identifier":
                                yield child.text()
                    case "identifier":
                        yield left.text()
        case "function_definition" | "class_definition" | "named_expression":
            if name := node.field("name"):
                yield name.text()
        case "import_from_statement":
            match tuple((child.kind(), child) for child in node.children()):
                case (("from", _), _, ("import", _), *name_nodes):
                    for _, child in cast(list[tuple[str, SgNode]], name_nodes):  # type: ignore[redundant-cast]
                        match child.kind():
                            case "dotted_name":
                                if (inner_children := child.children()) and (
                                    last_child := inner_children[-1]
                                ).kind() == "identifier":
                                    yield last_child.text()
                            case "aliased_import":
                                if alias := child.field("alias"):
                                    yield alias.text()
        case "as_pattern":
            match tuple((child.kind(), child) for child in node.children()):
                case (
                    (("identifier", _), ("as", _), ("as_pattern_target", alias))
                    | (("case_pattern", _), ("as", _), ("identifier", alias))
                ):
                    yield alias.text()
        case "keyword_pattern":
            match tuple((child.kind(), child) for child in node.children()):
                case (("identifier", _), ("=", _), ("dotted_name", alias)):
                    if (children := alias.children()) and (last_child := children[-1]).kind() == "identifier":
                        yield last_child.text()
        case "splat_pattern":
            for child in node.children():
                if child.kind() == "identifier":
                    yield child.text()
        case "dict_pattern":
            for child in node.children():
                if (
                    child.kind() == "case_pattern"  # noqa: PLR0916
                    and (previous := child.prev())
                    and previous.kind() == ":"
                    and (inner_children := child.children())
                    and (last_child := inner_children[-1]).kind() == "dotted_name"
                    and (inner_inner_children := last_child.children())
                    and (last_last_child := inner_inner_children[-1]).kind() == "identifier"
                ):
                    yield last_last_child.text()
        case "for_statement":
            if left := node.field("left"):
                for child in left.find_all(kind="identifier"):
                    yield child.text()


def find_definitions_in_function(function: SgNode) -> dict[str, list[SgNode]]:
    definition_map = defaultdict(list)
    ignored_names = set[str]()

    if parameters := function.field("parameters"):
        for child in parameters.children():
            match child.kind():
                case "default_parameter" | "typed_default_parameter":
                    if name := child.field("name"):
                        definition_map[name.text()].append(child)
                case "identifier":
                    definition_map[child.text()].append(child)
                case _:
                    for inner_child in child.children():
                        if inner_child.kind() == "identifier":
                            definition_map[inner_child.text()].append(child)

    for node in function.find_all(
        any=[
            {"kind": "assignment"},
            {"kind": "augmented_assignment"},
            {"kind": "named_expression"},
            {"kind": "function_definition"},
            {"kind": "global_statement"},
            {"kind": "nonlocal_statement"},
            {"kind": "class_definition"},
            {"kind": "import_from_statement"},
            {"kind": "as_pattern"},
            {"kind": "keyword_pattern"},
            {"kind": "splat_pattern"},
            {"kind": "dict_pattern"},
            {"kind": "for_statement"},
        ]
    ):
        if node_is_in_inner_function_or_class(function, node):
            continue
        match node.kind():
            case "global_statement" | "nonlocal_statement":
                for child in node.children():
                    if child.kind() == "identifier":
                        ignored_names.add(child.text())
            case _:
                for identifier in find_identifiers_in_node(node):
                    definition_map[identifier].append(node)

    for param in ignored_names:
        if param in definition_map:
            del definition_map[param]

    return definition_map
