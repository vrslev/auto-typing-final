import pytest
from ast_grep_py import SgRoot

from auto_typing_final.finder import ImportsResult, find_imports_of_identifier_in_scope


@pytest.mark.parametrize(
    ("source", "result"),
    [
        ("import typing", ImportsResult(module_aliases={"typing"}, has_from_import=False)),
        ("import typing, platform", ImportsResult(module_aliases={"typing"}, has_from_import=False)),
        ("import typing, platform\nimport typing", ImportsResult(module_aliases={"typing"}, has_from_import=False)),
        ("from typing import Final", ImportsResult(module_aliases={"typing"}, has_from_import=True)),
        ("from typing import Final as Final", ImportsResult(module_aliases={"typing"}, has_from_import=False)),
        ("from typing import Final as F", ImportsResult(module_aliases={"typing"}, has_from_import=False)),
        ("import typing; from typing import Final", ImportsResult(module_aliases={"typing"}, has_from_import=True)),
        ("import typing as tp", ImportsResult(module_aliases={"tp", "typing"}, has_from_import=False)),
        (
            "import typing as tp\nimport typing as tt\nimport typing\n"
            "from typing import Final as F\nfrom typing import Final",
            ImportsResult(module_aliases={"tp", "tt", "typing"}, has_from_import=True),
        ),
        (
            "import typing as tp\nimport typing as tt",
            ImportsResult(module_aliases={"tp", "tt", "typing"}, has_from_import=False),
        ),
    ],
)
def test_get_global_imports(source: str, result: ImportsResult) -> None:
    assert (
        find_imports_of_identifier_in_scope(
            SgRoot(source, "python").root(), module_name="typing", identifier_name="Final"
        )
        == result
    )
