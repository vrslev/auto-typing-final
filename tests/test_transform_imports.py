from typing import Final

import pytest

from auto_typing_final.main import transform_file_content
from auto_typing_final.transform import IMPORT_STYLES_TO_IMPORT_CONFIGS, ImportConfig


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
        """
typing = 1

def f():
    a = 1
---
typing = 1

def f():
    a: typing.Final = 1
""",
    ],
)
def test_add_import(case: str) -> None:
    before, _, after = case.partition("---")
    import_config: Final = IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"]
    assert (
        transform_file_content(before.strip(), import_config=import_config, ignore_global_vars=False) == after.strip()
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
def test_different_import_styles(case: str, import_config: ImportConfig) -> None:
    before, _, after = case.partition("---")
    assert (
        transform_file_content(before.strip(), import_config=import_config, ignore_global_vars=False) == after.strip()
    )
