from typing import Final

import pytest

from auto_typing_final.main import transform_file_content
from auto_typing_final.transform import IMPORT_STYLES_TO_IMPORT_CONFIGS, ImportConfig
from tests.conftest import assert_md_test_case_transformed, parse_md_test_cases


@pytest.mark.parametrize("import_config", IMPORT_STYLES_TO_IMPORT_CONFIGS.values())
@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("a: typing.Annotated[int, 'hello'] = 1", "a: {}[typing.Annotated[int, 'hello']] = 1"),
        ("a: list[int] = 1", "a: {}[list[int]] = 1"),
        ("a = 1\na: {}[int] = 2", "a = 1\na: int = 2"),
        ("a = 1\nb = 2\nb: {}[int] = 3", "a: {} = 1\nb = 2\nb: int = 3"),
    ],
)
def test_tricky_annotations_exact_match(import_config: ImportConfig, before: str, after: str) -> None:
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
    assert (
        transform_file_content(source.strip(), import_config=import_config, ignore_global_vars=False)
        == after_source.strip()
    )


@pytest.mark.parametrize("case", parse_md_test_cases("function_vars.md"))
def test_function_vars(case: str, import_config: ImportConfig, ignore_global_vars: bool) -> None:
    result: Final = transform_file_content(
        f"{import_config.import_text}\n{case}", import_config=import_config, ignore_global_vars=ignore_global_vars
    )
    assert_md_test_case_transformed(test_case=case, transformed_result=result, import_config=import_config)


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
        transform_file_content(
            f"{import_config.import_text}\n" + before.strip(), import_config=import_config, ignore_global_vars=False
        )
        == f"{import_config.import_text}\n" + after.strip()
    )
