from typing import Final

import pytest

from auto_typing_final.main import transform_file_content
from auto_typing_final.transform import IMPORT_STYLES_TO_IMPORT_CONFIGS, ImportConfig


@pytest.mark.parametrize("import_config", IMPORT_STYLES_TO_IMPORT_CONFIGS.values())
@pytest.mark.parametrize(
    ("before", "after"),
    [
        # Add annotation
        ("a: int", "a: int"),
        ("a = 1", "a: {} = 1"),
        ("a: {} = 1", "a: {} = 1"),
        ("a: int = 1", "a: {}[int] = 1"),
        ("a: typing.Annotated[int, 'hello'] = 1", "a: {}[typing.Annotated[int, 'hello']] = 1"),
        ("a: list[int] = 1", "a: {}[list[int]] = 1"),
        ("b = 1\na = 2\nb = 3", "b = 1\na: {} = 2\nb = 3"),
        ("b = 1\nb = 2\na = 3", "b = 1\nb = 2\na: {} = 3"),
        ("a = 1\nb = 2\nb = 3", "a: {} = 1\nb = 2\nb = 3"),
        ("a = 1\na = 2\nb: int", "a = 1\na = 2\nb: int"),
        ("a = 1\na: int", "a = 1\na: int"),
        ("a: int\na = 1", "a: int\na = 1"),
        ("a: {}\na = 1", "a: {}\na = 1"),
        ("a: int\na: int = 1", "a: int\na: int = 1"),
        ("a, b = 1, 2", "a, b = 1, 2"),
        ("(a, b) = 1, 2", "(a, b) = 1, 2"),
        ("(a, b) = t()", "(a, b) = t()"),
        ("[a, b] = t()", "[a, b] = t()"),
        ("[a] = t()", "[a] = t()"),
        ("a = b = 1", "a = b = 1"),
        ("a = b = c = 1", "a = b = c = 1"),
        ("a = (b := 1)", "a: {} = (b := 1)"),
        # Remove annotation
        ("a = 1\na: {}[int] = 2", "a = 1\na: int = 2"),
        ("a = 1\na: {} = 2", "a = 1\na = 2"),
        ("a = 1\na: {}=2", "a = 1\na = 2"),
        ("a = 1\na =2", "a = 1\na =2"),
        ("a: int = 1\na: {}[int] = 2", "a: int = 1\na: int = 2"),
        ("a: int = 1\na: {} = 2", "a: int = 1\na = 2"),
        ("a: {} = 1\na: {} = 2\na = 3\na: int = 4", "a = 1\na = 2\na = 3\na: int = 4"),
        ("a: {} = b = 1", "a: {} = b = 1"),
        # Both
        ("a = 1\nb = 2\nb: {}[int] = 3", "a: {} = 1\nb = 2\nb: int = 3"),
    ],
)
def test_variants(import_config: ImportConfig, before: str, after: str) -> None:
    source_function_content: Final = "\n".join(
        f"    {line.format(import_config.value)}" for line in before.splitlines()
    )
    source: Final = f"""
{import_config.import_text}

def foo():
{source_function_content}
"""

    after_function_content: Final = "\n".join(f"    {line.format(import_config.value)}" for line in after.splitlines())
    after_source: Final = f"""
{import_config.import_text}

def foo():
{after_function_content}
"""
    assert transform_file_content(source.strip(), import_config=import_config) == after_source.strip()


@pytest.mark.parametrize(
    "case",
    [
        """
a = 1
---
a = 1
""",
        """
def foo():
    a = 1
---
def foo():
    a: typing.Final = 1
""",
        """
a = 1

def foo():
    a = 2

    def bar():
        a = 3
---
a = 1

def foo():
    a: typing.Final = 2

    def bar():
        a: typing.Final = 3
""",
        """
a = 1

def foo():
    global a
    a = 2
---
a = 1

def foo():
    global a
    a = 2
""",
        """
def foo():
    from b import bar
    baz = 1
---
def foo():
    from b import bar
    baz: typing.Final = 1
""",
        """
def foo():
    from b import bar as baz
    bar = 1
    baz = 1
---
def foo():
    from b import bar as baz
    bar: typing.Final = 1
    baz = 1
""",
        """
def foo():
    from b import bar
    bar: typing.Final = 1
---
def foo():
    from b import bar
    bar = 1
""",
        """
def foo():
    import bar
    bar: typing.Final = 1
---
def foo():
    import bar
    bar = 1
""",
        """
def foo():
    import baz
    bar: typing.Final = 1
---
def foo():
    import baz
    bar: typing.Final = 1
""",
        """
def foo():
    from b import bar, baz
    bar = 1
    baz = 1
---
def foo():
    from b import bar, baz
    bar = 1
    baz = 1
""",
        """
def foo():
    from b import bar, baz as bazbaz
    bar = 1
    baz = 1
---
def foo():
    from b import bar, baz as bazbaz
    bar = 1
    baz: typing.Final = 1
""",
        """
def foo():
    # Dotted paths are not allowed, but tree-sitter-python grammar permits it
    from b import d.bar, bazbaz as baz
    bar = 1
    baz = 1
---
def foo():
    # Dotted paths are not allowed, but tree-sitter-python grammar permits it
    from b import d.bar, bazbaz as baz
    bar = 1
    baz = 1
""",
        """
def foo():
    from b import (bar, bazbaz)
    bar = 1
    baz = 1
---
def foo():
    from b import (bar, bazbaz)
    bar = 1
    baz: typing.Final = 1
""",
        """
def foo():
    a: typing.Final = 1
    a += 1
---
def foo():
    a = 1
    a += 1
""",
        """
def foo():
    a: typing.Final = 1
    a: int
---
def foo():
    a = 1
    a: int
""",
        """
def foo():
    a: typing.Final = 1
    a: typing.Final
---
def foo():
    a = 1
    a: typing.Final
""",
        """
def foo():
    a, b = 1
---
def foo():
    a, b = 1
""",
        """
def foo():
    a: typing.Final = 1
    b: typing.Final = 2
    a, b = 3
---
def foo():
    a = 1
    b = 2
    a, b = 3
""",
        """
def foo():
    a: typing.Final = 1
    b, c = 2
---
def foo():
    a: typing.Final = 1
    b, c = 2
""",
        """
def foo():
    a, b: typing.Final = 1
---
def foo():
    a, b: typing.Final = 1
""",
        """
def foo():
    a: typing.Final = 1
    (a, b) = 2
---
def foo():
    a = 1
    (a, b) = 2
""",
        """
def foo():
    a: typing.Final = 1
    (a, *other) = 2
---
def foo():
    a = 1
    (a, *other) = 2
""",
        """
def foo():
    def a(): ...
    a: typing.Final = 1
---
def foo():
    def a(): ...
    a = 1
""",
        """
def foo():
    class a: ...
    a: typing.Final = 1
---
def foo():
    class a: ...
    a = 1
""",
        """
def foo():
    a: typing.Final = 1
    if a := 1: ...
---
def foo():
    a = 1
    if a := 1: ...
""",
        """
def foo():
    while True:
        a = 1
---
def foo():
    while True:
        a = 1
""",
        """
def foo():
    while True:
        a: typing.Final = 1
---
def foo():
    while True:
        a = 1
""",
        """
def foo():
    for _ in ...:
        a: typing.Final = 1
---
def foo():
    for _ in ...:
        a = 1
""",
        """
def foo():
    for _ in ...:
        def foo():
            a: typing.Final = 1
---
def foo():
    for _ in ...:
        def foo():
            a = 1
""",
        """
def foo():
    a: typing.Final = 1
    b: typing.Final = 2

    for _ in ...:
        a: typing.Final = 1
---
def foo():
    a = 1
    b: typing.Final = 2

    for _ in ...:
        a = 1
""",
        """
def foo():
    for _ in ...:
        a = 1
---
def foo():
    for _ in ...:
        a = 1
""",
        """
def foo():
    a: typing.Final = 1
    for a in ...: ...
---
def foo():
    a = 1
    for a in ...: ...
""",
        """
def foo():
    a: typing.Final = 1

    match ...:
        case ...: ...
---
def foo():
    a: typing.Final = 1

    match ...:
        case ...: ...
""",
        """
def foo():
    a: typing.Final = 1

    match ...:
        case [] as a: ...
---
def foo():
    a = 1

    match ...:
        case [] as a: ...
""",
        """
def foo():
    a: typing.Final = 1

    match ...:
        case {"hello": a, **b}: ...
---
def foo():
    a = 1

    match ...:
        case {"hello": a, **b}: ...
""",
        """
def foo():
    a: typing.Final = 1

    match ...:
        case {**a}: ...
---
def foo():
    a = 1

    match ...:
        case {**a}: ...
""",
        """
def foo():
    a: typing.Final = 1

    match ...:
        case A(b=a) | B(b=a): ...
---
def foo():
    a = 1

    match ...:
        case A(b=a) | B(b=a): ...
""",
        """
def foo():
    a: typing.Final = 1

    match ...:
        case [b, *a]: ...
---
def foo():
    a = 1

    match ...:
        case [b, *a]: ...
""",
        """
def foo():
    a: typing.Final = 1

    match ...:
        case [a]: ...
---
def foo():
    a = 1

    match ...:
        case [a]: ...
""",
        """
def foo():
    a: typing.Final = 1

    match ...:
        case (a,): ...
---
def foo():
    a = 1

    match ...:
        case (a,): ...
""",
        """
def foo():
    a: typing.Final = 1
    nonlocal a
---
def foo():
    a = 1
    nonlocal a
""",
        """
def foo():
    a = 1
    nonlocal a
---
def foo():
    a = 1
    nonlocal a
""",
        """
def foo():
    a: typing.Final = 1
    global b
---
def foo():
    a: typing.Final = 1
    global b
""",
        """
def foo():
    a: typing.Final = 1
    global a
---
def foo():
    a = 1
    global a
""",
        """
def foo():
    a: typing.Final = 1
    b: typing.Final = 2
    c: typing.Final = 3

    def bar():
        nonlocal a
        b: typing.Final = 4
        c: typing.Final = 5

        class C:
            a = 6
            c = 7

            def baz():
                nonlocal a, b
                b: typing.Final = 8
                c: typing.Final = 9
---
def foo():
    a = 1
    b: typing.Final = 2
    c: typing.Final = 3

    def bar():
        nonlocal a
        b = 4
        c: typing.Final = 5

        class C:
            a = 6
            c = 7

            def baz():
                nonlocal a, b
                b = 8
                c: typing.Final = 9
""",
        """
def foo():
    foo = 1
---
def foo():
    foo: typing.Final = 1
""",
        """
def foo(a, b: int, c=1, d: int = 2):
    a: typing.Final = 1
    b: typing.Final = 2
    c: typing.Final = 3
    d: typing.Final = 4
    e: typing.Final = 5
---
def foo(a, b: int, c=1, d: int = 2):
    a = 1
    b = 2
    c = 3
    d = 4
    e: typing.Final = 5
""",
        """
def foo(self):
    self.me = 1
---
def foo(self):
    self.me = 1
""",
        """
a.b = 1
---
a.b = 1
""",
    ],
)
def test_transform_file_content(case: str) -> None:
    import_config: Final = IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"]
    before, _, after = case.partition("---")
    assert (
        transform_file_content(f"{import_config.import_text}\n" + before.strip(), import_config=import_config)
        == f"{import_config.import_text}\n" + after.strip()
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
    assert transform_file_content(before.strip(), import_config=import_config) == after.strip()


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
def test_different_styles(case: str, import_config: ImportConfig) -> None:
    before, _, after = case.partition("---")
    assert transform_file_content(before.strip(), import_config=import_config) == after.strip()
# TODO: test cases where local var has same name as global var

@pytest.mark.parametrize(
    "case",
    [
        # Test that allows UPPER_CASE global constants
        """
MY_CONSTANT = 42
MY_OTHER_CONSTANT = "hello"
---
import typing
MY_CONSTANT: typing.Final = 42
MY_OTHER_CONSTANT: typing.Final = "hello"
""",
        # Test that non-UPPER_CASE global variables are still ignored
        """
global_var = 42
myVar = "hello"
---
global_var = 42
myVar = "hello"
""",
        # Test single letter constants are ignored  # TODO: also ignore cases where not only one letter, but one word.
        """
A = 42
B = "hello"
---
A = 42
B = "hello"
""",
        # Test mixed case - function variables should still work
        """
MY_CONSTANT = 42
global_var = "hello"

def foo():
    local_var = 1
---
import typing
MY_CONSTANT: typing.Final = 42
global_var = "hello"

def foo():
    local_var: typing.Final = 1
""",
        # Test with existing Final annotation
        """
MY_CONSTANT: typing.Final = 42
MY_OTHER_CONSTANT = "hello"
---
import typing
MY_CONSTANT: typing.Final = 42
MY_OTHER_CONSTANT: typing.Final = "hello"
""",
        # Test with existing typed annotation
        """
MY_CONSTANT: int = 42
MY_OTHER_CONSTANT = "hello"
---
import typing
MY_CONSTANT: typing.Final[int] = 42
MY_OTHER_CONSTANT: typing.Final = "hello"
""",
    ],
)
def test_ignore_global_vars_flag(case: str) -> None:
    """Test the flag functionality."""
    import_config: Final = IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"]
    before, _, after = case.partition("---")
    result = transform_file_content(before.strip(), import_config=import_config, ignore_global_vars=True)
    assert result == after.strip()


@pytest.mark.parametrize(
    "case",
    [
        # Test behavior where ignore_global_vars=True - should ignore all global variables
        """
MY_CONSTANT = 42
MY_OTHER_CONSTANT = "hello"
global_var = 123

def foo():
    local_var = 1
---
import typing
MY_CONSTANT = 42
MY_OTHER_CONSTANT = "hello"
global_var = 123

def foo():
    local_var: typing.Final = 1
""",
    ],
)
def test_default_behavior_still_ignores_globals(case: str) -> None:
    """Test that default behavior (ignore_global_vars=False) still ignores all global variables."""
    import_config: Final = IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"]
    before, _, after = case.partition("---")
    result = transform_file_content(before.strip(), import_config=import_config, ignore_global_vars=True)
    assert result == after.strip()
