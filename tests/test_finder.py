import pytest
from ast_grep_py import SgRoot

from auto_typing_final.finder import ImportsResult, get_global_imports


@pytest.mark.parametrize(
    ("source", "result"),
    [
        ("import typing", ImportsResult(module_aliases={"typing"}, has_from_import=False)),
        ("import typing, platform", ImportsResult(module_aliases={"typing"}, has_from_import=False)),
        ("import typing, platform\nimport typing", ImportsResult(module_aliases={"typing"}, has_from_import=False)),
    ],
)
def test_get_global_imports(source: str, result: ImportsResult) -> None:
    assert get_global_imports(SgRoot(source, "python").root()) == result
