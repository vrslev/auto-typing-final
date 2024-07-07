from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from ast_grep_py import Config, SgNode

# https://github.com/tree-sitter/tree-sitter-python/blob/71778c2a472ed00a64abf4219544edbf8e4b86d7/grammar.js
DEFINITION_RULE: Config = {
    "rule": {
        "any": [
            {"kind": "assignment"},
            {"kind": "augmented_assignment"},
            {"kind": "named_expression"},
            {"kind": "function_definition"},
            {"kind": "global_statement"},
            {"kind": "nonlocal_statement"},
            {"kind": "class_definition"},
            {"kind": "import_from_statement"},
            {"kind": "import_statement"},
            {"kind": "as_pattern"},
            {"kind": "keyword_pattern"},
            {"kind": "splat_pattern"},
            {"kind": "dict_pattern"},
            {"kind": "list_pattern"},
            {"kind": "tuple_pattern"},
            {"kind": "for_statement"},
        ]
    }
}


def _get_last_child_of_type(node: SgNode, type_: str) -> SgNode | None:
    return last_child if (children := node.children()) and (last_child := children[-1]).kind() == type_ else None


def _find_identifiers_in_children(node: SgNode) -> Iterable[SgNode]:
    for child in node.children():
        if child.kind() == "identifier":
            yield child


def _is_inside_inner_function(root: SgNode, node: SgNode) -> bool:
    for ancestor in node.ancestors():
        if ancestor.kind() == "function_definition":
            return ancestor != root
    return False


def _is_inside_inner_function_or_class(root: SgNode, node: SgNode) -> bool:
    for ancestor in node.ancestors():
        if ancestor.kind() in {"function_definition", "class_definition"}:
            return ancestor != root
    return False


def _find_identifiers_in_import_statement(node: SgNode) -> Iterable[SgNode]:
    match tuple((child.kind(), child) for child in node.children()):
        case (("from", _), _, ("import", _), *name_nodes) | (("import", _), *name_nodes):
            for kind, name_node in name_nodes:
                match kind:
                    case "dotted_name":
                        if identifier := _get_last_child_of_type(name_node, "identifier"):
                            yield identifier
                    case "aliased_import":
                        if alias := name_node.field("alias"):
                            yield alias


def _find_identifiers_made_by_node(node: SgNode) -> Iterable[SgNode]:  # noqa: C901, PLR0912
    match node.kind():
        case "assignment" | "augmented_assignment":
            if not (left := node.field("left")):
                return
            match left.kind():
                case "pattern_list" | "tuple_pattern":
                    yield from _find_identifiers_in_children(left)
                case "identifier":
                    yield left
        case "named_expression":
            if name := node.field("name"):
                yield name
        case "class_definition":
            if name := node.field("name"):
                yield name
            for function in node.find_all(kind="function_definition"):
                for nonlocal_statement in node.find_all(kind="nonlocal_statement"):
                    if _is_inside_inner_function(root=function, node=nonlocal_statement):
                        continue
                    yield from _find_identifiers_in_children(nonlocal_statement)
        case "function_definition":
            if name := node.field("name"):
                yield name
            for nonlocal_statement in node.find_all(kind="nonlocal_statement"):
                if _is_inside_inner_function(root=node, node=nonlocal_statement):
                    continue
                yield from _find_identifiers_in_children(nonlocal_statement)
        case "import_from_statement" | "import_statement":
            yield from _find_identifiers_in_import_statement(node)
        case "as_pattern":
            match tuple((child.kind(), child) for child in node.children()):
                case (
                    (("identifier", _), ("as", _), ("as_pattern_target", alias))
                    | (("case_pattern", _), ("as", _), ("identifier", alias))
                ):
                    yield alias
        case "keyword_pattern":
            match tuple((child.kind(), child) for child in node.children()):
                case (("identifier", _), ("=", _), ("dotted_name", alias)):
                    if identifier := _get_last_child_of_type(alias, "identifier"):
                        yield identifier
        case "list_pattern" | "tuple_pattern":
            for child in node.children():
                if (
                    child.kind() == "case_pattern"
                    and (dotted_name := _get_last_child_of_type(child, "dotted_name"))
                    and (identifier := _get_last_child_of_type(dotted_name, "identifier"))
                ):
                    yield identifier
        case "splat_pattern" | "global_statement" | "nonlocal_statement":
            yield from _find_identifiers_in_children(node)
        case "dict_pattern":
            for child in node.children():
                if (
                    child.kind() == "case_pattern"
                    and (previous_child := child.prev())
                    and previous_child.kind() == ":"
                    and (dotted_name := _get_last_child_of_type(child, "dotted_name"))
                    and (identifier := _get_last_child_of_type(dotted_name, "identifier"))
                ):
                    yield identifier
        case "for_statement":
            if left := node.field("left"):
                yield from left.find_all(kind="identifier")


def _find_identifiers_in_current_scope(node: SgNode) -> Iterable[tuple[SgNode, SgNode]]:
    for child in node.find_all(DEFINITION_RULE):
        if _is_inside_inner_function_or_class(node, child) or child == node:
            continue
        for identifier in _find_identifiers_made_by_node(child):
            yield identifier, child


def _find_identifiers_in_function_parameter(node: SgNode) -> Iterable[SgNode]:
    match node.kind():
        case "default_parameter" | "typed_default_parameter":
            if name := node.field("name"):
                yield name
        case "identifier":
            yield node
        case _:
            yield from _find_identifiers_in_children(node)


def find_all_definitions_in_functions(root: SgNode) -> Iterable[list[SgNode]]:
    for function in root.find_all(kind="function_definition"):
        definition_map = defaultdict(list)

        if parameters := function.field("parameters"):
            for parameter in parameters.children():
                for identifier in _find_identifiers_in_function_parameter(parameter):
                    definition_map[identifier.text()].append(parameter)

        for identifier, node in _find_identifiers_in_current_scope(function):
            definition_map[identifier.text()].append(node)

        yield from definition_map.values()


def has_global_identifier_with_name(root: SgNode, name: str) -> bool:
    return name in {identifier.text() for identifier, _ in _find_identifiers_in_current_scope(root)}


@dataclass
class ImportsResult:
    module_aliases: set[str]
    has_from_import: bool


def find_imports_of_identifier_in_scope(root: SgNode, module_name: str, identifier_name: str) -> ImportsResult:  # noqa: C901
    result: Final = ImportsResult(module_aliases={module_name}, has_from_import=False)

    for node in root.find_all(any=[{"kind": "import_statement"}, {"kind": "import_from_statement"}]):
        if _is_inside_inner_function_or_class(root, node) or node == root:
            continue

        match tuple((child.kind(), child) for child in node.children()):
            case (("from", _), (_, module), ("import", _), *name_nodes):
                for kind, name_node in name_nodes:
                    if (
                        kind == "dotted_name"
                        and (identifier := _get_last_child_of_type(name_node, "identifier"))
                        and module.text() == module_name
                        and identifier.text() == identifier_name
                    ):
                        result.has_from_import = True
            case (("import", _), *name_nodes):
                for kind, name_node in name_nodes:
                    match kind:
                        case "dotted_name":
                            if (identifier := _get_last_child_of_type(name_node, "identifier")) and (
                                identifier_text := identifier.text()
                            ) == module_name:
                                result.module_aliases.add(identifier_text)
                        case "aliased_import":
                            if (
                                (name := name_node.field("name"))
                                and (name.text() == module_name)
                                and (alias := name_node.field("alias"))
                            ):
                                result.module_aliases.add(alias.text())
    return result
