# ruff: noqa: T201, ERA001

from collections import defaultdict
from pathlib import Path
from pprint import pp
from typing import cast

from ast_grep_py import SgNode, SgRoot

with Path("t.py").open("r+", encoding="locale") as f:
    root = SgRoot(f.read(), "python").root()

functions = root.find_all(kind="function_definition")

function = functions[0]


# print(function.find_all({"rule": {"kind": "assignment", "not": {"inside": {"kind": "function_definition"}}}}))
def node_is_in_inner_function_or_class(root: SgNode, node: SgNode) -> bool:
    # print([c.kind() for c in node.ancestors()])
    for ancestor in node.ancestors():
        if ancestor.kind() in {"function_definition", "class_definition"} and ancestor != root:
            return True
    return False


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
        case "assignment":
            if left := node.field("left"):
                match left.kind():
                    case "pattern_list":
                        for child in left.children():
                            if child.kind() == "identifier":
                                definition_map[child.text()].append(node)
                    case "identifier":
                        definition_map[left.text()].append(node)
        case "function_definition" | "class_definition" | "named_expression":
            if name := node.field("name"):
                definition_map[name.text()].append(node)
        case "global_statement" | "nonlocal_statement":
            for child in node.children():
                if child.kind() == "identifier":
                    ignored_names.add(child.text())
        case "import_from_statement":
            match tuple((child.kind(), child) for child in node.children()):
                case (("from", _), _, ("import", _), *name_nodes):
                    for _, child in cast(list[tuple[str, SgNode]], name_nodes):  # type: ignore[redundant-cast]
                        match child.kind():
                            case "dotted_name":
                                if (inner_children := child.children()) and (
                                    last_child := inner_children[-1]
                                ).kind() == "identifier":
                                    definition_map[last_child.text()].append(node)
                            case "aliased_import":
                                if alias := child.field("alias"):
                                    definition_map[alias.text()].append(node)
        case "as_pattern":
            match tuple((child.kind(), child) for child in node.children()):
                case (
                    (("identifier", _), ("as", _), ("as_pattern_target", alias))
                    | (("case_pattern", _), ("as", _), ("identifier", alias))
                ):
                    definition_map[alias.text()].append(node)
        case "keyword_pattern":
            match tuple((child.kind(), child) for child in node.children()):
                case (("identifier", _), ("=", _), ("dotted_name", alias)):
                    if (children := alias.children()) and (last_child := children[-1]).kind() == "identifier":
                        definition_map[last_child.text()].append(node)
        case "splat_pattern":
            for child in node.children():
                if child.kind() == "identifier":
                    definition_map[child.text()].append(node)
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
                    definition_map[last_last_child.text()].append(node)
        case "for_statement":
            if left := node.field("left"):
                for child in left.find_all(kind="identifier"):
                    definition_map[child.text()].append(node)
pp(definition_map)
pp(ignored_names)
# pp([(c.kind(), c) for c in a])
# name = function.field("name")
# params = function.field("parameters")
# assert params
# body = function.field("body")
# assert body


# def find_definitions(node: SgNode) -> defaultdict[str, list[SgNode]]:
#     # if node.kind() == "parameters":
#     #     for child in node.children():
#     #         ...

#     definitions_map = defaultdict(list)
#     for child in node.children():
#         print(child.kind())
#         match child.kind():
#             case "function_definition":
#                 definitions_map[child.field("name").text()].append(child)
#             case "expression_statement":
#                 ...
#     return definitions_map
# # print(list(find_definitions(params)))
# print(list(find_definitions(body)))
