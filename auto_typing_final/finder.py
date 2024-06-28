from collections import defaultdict
from collections.abc import Iterable

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


def last_child_of_type(node: SgNode, type_: str) -> SgNode | None:
    return last_child if (children := node.children()) and (last_child := children[-1]).kind() == type_ else None


def find_identifiers_in_children(node: SgNode) -> Iterable[SgNode]:
    for child in node.children():
        if child.kind() == "identifier":
            yield child


def node_is_in_inner_function(root: SgNode, node: SgNode) -> bool:
    for ancestor in node.ancestors():
        if ancestor.kind() == "function_definition":
            return ancestor != root
    return False


def node_is_in_inner_function_or_class(root: SgNode, node: SgNode) -> bool:
    for ancestor in node.ancestors():
        if ancestor.kind() in {"function_definition", "class_definition"}:
            return ancestor != root
    return False


def find_identifiers_in_function_parameter(node: SgNode) -> Iterable[SgNode]:
    match node.kind():
        case "default_parameter" | "typed_default_parameter":
            if name := node.field("name"):
                yield name
        case "identifier":
            yield node
        case _:
            yield from find_identifiers_in_children(node)


def find_identifiers_in_function_body(node: SgNode) -> Iterable[SgNode]:  # noqa: C901, PLR0912, PLR0915
    match node.kind():
        case "assignment" | "augmented_assignment":
            if not (left := node.field("left")):
                return
            match left.kind():
                case "pattern_list" | "tuple_pattern":
                    yield from find_identifiers_in_children(left)
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
                    if node_is_in_inner_function(root=function, node=nonlocal_statement):
                        continue
                    yield from find_identifiers_in_children(nonlocal_statement)
        case "function_definition":
            if name := node.field("name"):
                yield name
            for nonlocal_statement in node.find_all(kind="nonlocal_statement"):
                if node_is_in_inner_function(root=node, node=nonlocal_statement):
                    continue
                yield from find_identifiers_in_children(nonlocal_statement)
        case "import_from_statement":
            match tuple((child.kind(), child) for child in node.children()):  # TODO: child to something specific
                case (("from", _), _, ("import", _), *name_nodes):
                    for name_node_kind, name_node in name_nodes:
                        match name_node_kind:
                            case "dotted_name":
                                if identifier := last_child_of_type(name_node, "identifier"):
                                    yield identifier
                            case "aliased_import":
                                if alias := name_node.field("alias"):
                                    yield alias
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
                    if identifier := last_child_of_type(alias, "identifier"):
                        yield identifier
        case "list_pattern" | "tuple_pattern":
            for child in node.children():
                if (
                    child.kind() == "case_pattern"
                    and (dotted_name := last_child_of_type(child, "dotted_name"))
                    and (identifier := last_child_of_type(dotted_name, "identifier"))
                ):
                    yield identifier
        case "splat_pattern" | "global_statement" | "nonlocal_statement":
            yield from find_identifiers_in_children(node)
        case "dict_pattern":
            for child in node.children():
                if (
                    child.kind() == "case_pattern"
                    and (previous_child := child.prev())
                    and previous_child.kind() == ":"
                    and (dotted_name := last_child_of_type(child, "dotted_name"))
                    and (identifier := last_child_of_type(dotted_name, "identifier"))
                ):
                    yield identifier
        case "for_statement":
            if left := node.field("left"):
                yield from left.find_all(kind="identifier")


def find_definitions_in_scope_grouped_by_name(root: SgNode) -> dict[str, list[SgNode]]:
    definition_map = defaultdict(list)

    if parameters := root.field("parameters"):
        for node in parameters.children():
            for identifier in find_identifiers_in_function_parameter(node):
                definition_map[identifier.text()].append(node)

    for node in root.find_all(DEFINITION_RULE):
        if node_is_in_inner_function_or_class(root, node) or node == root:
            continue
        for identifier in find_identifiers_in_function_body(node):
            definition_map[identifier.text()].append(node)

    return definition_map


def find_definitions_in_global_scope(root: SgNode) -> dict[str, list[SgNode]]:
    global_statement_identifiers = defaultdict(list)
    for node in root.find_all(kind="global_statement"):
        for identifier in find_identifiers_in_children(node):
            global_statement_identifiers[identifier.text()].append(node)

    return {
        identifier: (global_statement_identifiers[identifier] + definitions)
        for identifier, definitions in find_definitions_in_scope_grouped_by_name(root).items()
    }


def find_definitions_in_module(root: SgNode) -> Iterable[list[SgNode]]:
    for function in root.find_all(kind="function_definition"):
        yield from find_definitions_in_scope_grouped_by_name(function).values()
    yield from find_definitions_in_global_scope(root).values()
