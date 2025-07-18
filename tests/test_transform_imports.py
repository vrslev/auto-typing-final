import pytest
from ast_grep_py import SgRoot

from auto_typing_final.finder import ImportsResult, find_imports_of_identifier_in_scope
from auto_typing_final.main import transform_file_content
from auto_typing_final.transform import IMPORT_STYLES_TO_IMPORT_CONFIGS, ImportConfig
from tests.conftest import parse_before_after_test_case


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


@pytest.mark.parametrize(
    "case",
    [
        """
import typing

def f():
    a = 1
---
import typing

def f():
    a: typing.Final = 1
""",
        """
import typing

def f():
    a: typing.Final = 1
---
import typing

def f():
    a: typing.Final = 1
""",
        """
def f():
    a = 1
---
import typing
def f():
    a: typing.Final = 1
""",
        """
def f():
    a: typing.Final = 1
    a = 2
---
def f():
    a = 1
    a = 2
""",
    ],
)
def test_add_import(case: str, ignore_global_vars: bool) -> None:
    before, after = parse_before_after_test_case(case)
    assert (
        transform_file_content(
            before, import_config=IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"], ignore_global_vars=ignore_global_vars
        )
        == after
    )


@pytest.mark.parametrize(
    ("case", "import_config"),
    [
        (
            """
from typing import Final

def f():
    a: Final[int] = 1
---
from typing import Final

def f():
    a: Final[int] = 1
""",
            IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"],
        ),
        (
            """
def f():
    a: Final = 1
    b: typing.Final = 2
    c: Final = 3
---
def f():
    a: Final = 1
    b: typing.Final = 2
    c: Final = 3
""",
            IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"],
        ),
        (
            """
import typing

def f():
    a: Final = 1
    b: typing.Final = 2
    c: Final = 3
---
import typing

def f():
    a: Final = 1
    b: typing.Final = 2
    c: Final = 3
""",
            IMPORT_STYLES_TO_IMPORT_CONFIGS["final"],
        ),
        (
            """
import typing as tp

def f():
    a: tp.Final = 1
---
import typing as tp

def f():
    a: tp.Final = 1
""",
            IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"],
        ),
        (
            """
import typing as tp

def f():
    a: tp.Final = 1
---
import typing as tp

def f():
    a: tp.Final = 1
""",
            IMPORT_STYLES_TO_IMPORT_CONFIGS["final"],
        ),
        (
            """
import typing as tp

def f():
    a: tp.Final = 1
    a: tp.Final = 2
    b = 1
---
import typing
import typing as tp

def f():
    a = 1
    a = 2
    b: typing.Final = 1
""",
            IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"],
        ),
        (
            """
import typing as tp

def f():
    a: tp.Final = 1
    a: tp.Final = 2
    b = 1
---
from typing import Final
import typing as tp

def f():
    a = 1
    a = 2
    b: Final = 1
""",
            IMPORT_STYLES_TO_IMPORT_CONFIGS["final"],
        ),
        (
            """
from typing import Final

def f():
    a: Final[
        int
    ] = 1
---
from typing import Final

def f():
    a: Final[
        int
    ] = 1
""",
            IMPORT_STYLES_TO_IMPORT_CONFIGS["final"],
        ),
        (
            """
from typing import Annotated

def f():
    a: Annotated[
        int,
        "hello",
    ] = 1
    a = 2
---
from typing import Annotated

def f():
    a: Annotated[
        int,
        "hello",
    ] = 1
    a = 2
""",
            IMPORT_STYLES_TO_IMPORT_CONFIGS["final"],
        ),
        (
            """
from typing import Annotated

def f():
    a: Annotated[
        int,
        "hello"
    ] = 1
---
from typing import Final
from typing import Annotated

def f():
    a: Final[Annotated[
        int,
        "hello"
    ]] = 1
""",
            IMPORT_STYLES_TO_IMPORT_CONFIGS["final"],
        ),
    ],
)
def test_different_import_styles(case: str, import_config: ImportConfig, ignore_global_vars: bool) -> None:
    before, after = parse_before_after_test_case(case)
    assert transform_file_content(before, import_config=import_config, ignore_global_vars=ignore_global_vars) == after
