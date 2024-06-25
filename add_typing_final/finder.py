from collections import defaultdict
from collections.abc import Iterable

from ast_grep_py import Config, SgNode


def last_child_of_type(node: SgNode, type_: str) -> SgNode | None:
    return last_child if (children := node.children()) and (last_child := children[-1]).kind() == type_ else None


def texts_of_identifier_nodes(node: SgNode) -> Iterable[str]:
    return (child.text() for child in node.children() if child.kind() == "identifier")


def find_identifiers_in_function_body(node: SgNode) -> Iterable[str]:  # noqa: C901, PLR0912
    match node.kind():
        case "assignment" | "augmented_assignment":
            if (left := node.field("left")):
                match left.kind():
                    case "pattern_list" | "tuple_pattern":
                        yield from texts_of_identifier_nodes(left)
                    case "identifier":
                        yield left.text()
        case "function_definition" | "class_definition" | "named_expression":
            if name := node.field("name"):
                yield name.text()
        case "import_from_statement":
            match tuple((child.kind(), child) for child in node.children()):
                case (("from", _), _, ("import", _), *name_nodes):
                    for _, child in name_nodes:
                        match child.kind():
                            case "dotted_name":
                                if identifier := last_child_of_type(child, "identifier"):
                                    yield identifier.text()
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
                    if identifier := last_child_of_type(alias, "identifier"):
                        yield identifier.text()
        case "splat_pattern":
            yield from texts_of_identifier_nodes(node)
        case "dict_pattern":
            for child in node.children():
                if (
                    child.kind() == "case_pattern"
                    and (previous_child := child.prev())
                    and previous_child.kind() == ":"
                    and (last_child := last_child_of_type(child, "dotted_name"))
                    and (last_last_child := last_child_of_type(last_child, "identifier"))
                ):
                    yield last_last_child.text()
        case "for_statement":
            if left := node.field("left"):
                for child in left.find_all(kind="identifier"):
                    yield child.text()


def find_identifiers_in_function_parameter(node: SgNode) -> Iterable[str]:
    match node.kind():
        case "default_parameter" | "typed_default_parameter":
            if name := node.field("name"):
                yield name.text()
        case "identifier":
            yield node.text()
        case _:
            yield from texts_of_identifier_nodes(node)


rule: Config = {
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
            {"kind": "for_statement"},
        ]
    }
}


def node_is_in_inner_function_or_class(root: SgNode, node: SgNode) -> bool:
    for ancestor in node.ancestors():
        if ancestor.kind() in {"function_definition", "class_definition"}:
            return ancestor != root
    return False


def find_definitions_in_scope_grouped_by_name(root: SgNode) -> Iterable[list[SgNode]]:
    definition_map = defaultdict(list)
    ignored_names = set[str]()
    if parameters := root.field("parameters"):
        for node in parameters.children():
            for identifier in find_identifiers_in_function_parameter(node):
                definition_map[identifier].append(node)

    for node in root.find_all(rule):
        if node_is_in_inner_function_or_class(root, node):
            continue
        match node.kind():
            case "global_statement" | "nonlocal_statement":
                ignored_names.update(texts_of_identifier_nodes(node))
            case _:
                for identifier in find_identifiers_in_function_body(node):
                    definition_map[identifier].append(node)

    for param in ignored_names:
        if param in definition_map:
            del definition_map[param]
    return definition_map.values()
