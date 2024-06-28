import pytest
from ast_grep_py import SgRoot

from auto_typing_final.main import make_edits_for_all_assignments_in_scope, run_fixer


@pytest.mark.parametrize(
    ("before", "after"),
    [
        # Add annotation
        ("a: int", "a: int"),
        ("a = 1", "a: typing.Final = 1"),
        ("a: typing.Final = 1", "a: typing.Final = 1"),
        ("a: int = 1", "a: typing.Final[int] = 1"),
        ("a: typing.Annotated[int, 'hello'] = 1", "a: typing.Final[typing.Annotated[int, 'hello']] = 1"),
        ("b = 1\na = 2\nb = 3", "b = 1\na: typing.Final = 2\nb = 3"),
        ("b = 1\nb = 2\na = 3", "b = 1\nb = 2\na: typing.Final = 3"),
        ("a = 1\nb = 2\nb = 3", "a: typing.Final = 1\nb = 2\nb = 3"),
        ("a = 1\na = 2\nb: int", "a = 1\na = 2\nb: int"),
        ("a = 1\na: int", "a = 1\na: int"),
        ("a: int\na = 1", "a: int\na = 1"),
        ("a: typing.Final\na = 1", "a: typing.Final\na = 1"),
        ("a: int\na: int = 1", "a: int\na: int = 1"),
        ("a, b = 1, 2", "a, b = 1, 2"),
        ("(a, b) = 1, 2", "(a, b) = 1, 2"),
        ("(a, b) = t()", "(a, b) = t()"),
        ("[a, b] = t()", "[a, b] = t()"),
        ("[a] = t()", "[a] = t()"),
        # Remove annotation
        ("a = 1\na: typing.Final[int] = 2", "a = 1\na: int = 2"),
        ("a = 1\na: typing.Final = 2", "a = 1\na = 2"),
        ("a: int = 1\na: typing.Final[int] = 2", "a: int = 1\na: int = 2"),
        ("a: int = 1\na: typing.Final = 2", "a: int = 1\na = 2"),
        ("a: typing.Final = 1\na: typing.Final = 2\na = 3\na: int = 4", "a = 1\na = 2\na = 3\na: int = 4"),
        # Both
        ("a = 1\nb = 2\nb: typing.Final[int] = 3", "a: typing.Final = 1\nb = 2\nb: int = 3"),
    ],
)
def test_variants(before: str, after: str) -> None:
    root = SgRoot(before.strip(), "python").root()
    assert root.commit_edits(list(make_edits_for_all_assignments_in_scope(root))) == after.strip()


# fmt: off
scopes_cases = [
("""
a = 1
""", """
a = 1
"""),

("""
def foo():
    a = 1
""", """
def foo():
    a: typing.Final = 1
"""),

("""
a = 1

def foo():
    a = 2

    def bar():
        a = 3
""", """
a = 1

def foo():
    a: typing.Final = 2

    def bar():
        a: typing.Final = 3
"""),

("""
a = 1

def foo():
    global a
    a = 2
""", """
a = 1

def foo():
    global a
    a = 2
"""),

("""
def foo():
    from b import bar
    baz = 1
""", """
def foo():
    from b import bar
    baz: typing.Final = 1
"""),

("""
def foo():
    from b import bar as baz
    bar = 1
    baz = 1
""", """
def foo():
    from b import bar as baz
    bar: typing.Final = 1
    baz = 1
"""),

("""
def foo():
    from b import bar
    bar = 1
""", """
def foo():
    from b import bar
    bar = 1
"""),

("""
def foo():
    from b import bar, baz
    bar = 1
    baz = 1
""", """
def foo():
    from b import bar, baz
    bar = 1
    baz = 1
"""),

("""
def foo():
    from b import bar, baz as bazbaz
    bar = 1
    baz = 1
""", """
def foo():
    from b import bar, baz as bazbaz
    bar = 1
    baz: typing.Final = 1
"""),

("""
def foo():
    # Dotted paths are not allowed, but tree-sitter-python grammar permits it
    from b import d.bar, bazbaz as baz
    bar = 1
    baz = 1
""", """
def foo():
    # Dotted paths are not allowed, but tree-sitter-python grammar permits it
    from b import d.bar, bazbaz as baz
    bar = 1
    baz = 1
"""),

("""
def foo():
    from b import (bar, bazbaz)
    bar = 1
    baz = 1
""", """
def foo():
    from b import (bar, bazbaz)
    bar = 1
    baz: typing.Final = 1
"""),

("""
def foo():
    a: typing.Final = 1
    a += 1
""", """
def foo():
    a = 1
    a += 1
"""),

("""
def foo():
    a: typing.Final = 1
    a: int
""", """
def foo():
    a = 1
    a: int
"""),

("""
def foo():
    a: typing.Final = 1
    a: typing.Final
""", """
def foo():
    a = 1
    a: typing.Final
"""),

("""
def foo():
    a, b = 1
""", """
def foo():
    a, b = 1
"""),

("""
def foo():
    a: typing.Final = 1
    b: typing.Final = 2
    a, b = 3
""", """
def foo():
    a = 1
    b = 2
    a, b = 3
"""),

("""
def foo():
    a: typing.Final = 1
    b, c = 2
""", """
def foo():
    a: typing.Final = 1
    b, c = 2
"""),

("""
def foo():
    a, b: typing.Final = 1
""", """
def foo():
    a, b: typing.Final = 1
"""),

("""
def foo():
    a: typing.Final = 1
    (a, b) = 2
""", """
def foo():
    a = 1
    (a, b) = 2
"""),

("""
def foo():
    a: typing.Final = 1
    (a, *other) = 2
""", """
def foo():
    a = 1
    (a, *other) = 2
"""),

("""
def foo():
    def a(): ...
    a: typing.Final = 1
""", """
def foo():
    def a(): ...
    a = 1
"""),

("""
def foo():
    class a: ...
    a: typing.Final = 1
""", """
def foo():
    class a: ...
    a = 1
"""),

("""
def foo():
    a: typing.Final = 1
    if a := 1: ...
""", """
def foo():
    a = 1
    if a := 1: ...
"""),

("""
def foo():
    while True:
        a = 1
""", """
def foo():
    while True:
        a = 1
"""),

("""
def foo():
    for _ in ...:
        a: typing.Final = 1
""", """
def foo():
    for _ in ...:
        a: typing.Final = 1
"""),

("""
def foo():
    for _ in ...:
        a = 1
""", """
def foo():
    for _ in ...:
        a = 1
"""),

("""
def foo():
    a: typing.Final = 1
    for a in ...: ...
""", """
def foo():
    a = 1
    for a in ...: ...
"""),

("""
def foo():
    a: typing.Final = 1

    match ...:
        case ...: ...
""", """
def foo():
    a: typing.Final = 1

    match ...:
        case ...: ...
"""),

("""
def foo():
    a: typing.Final = 1

    match ...:
        case [] as a: ...
""", """
def foo():
    a = 1

    match ...:
        case [] as a: ...
"""),

("""
def foo():
    a: typing.Final = 1

    match ...:
        case {"hello": a, **b}: ...
""", """
def foo():
    a = 1

    match ...:
        case {"hello": a, **b}: ...
"""),

("""
def foo():
    a: typing.Final = 1

    match ...:
        case {**a}: ...
""", """
def foo():
    a = 1

    match ...:
        case {**a}: ...
"""),

("""
def foo():
    a: typing.Final = 1

    match ...:
        case A(b=a) | B(b=a): ...
""", """
def foo():
    a = 1

    match ...:
        case A(b=a) | B(b=a): ...
"""),

("""
def foo():
    a: typing.Final = 1

    match ...:
        case [b, *a]: ...
""", """
def foo():
    a = 1

    match ...:
        case [b, *a]: ...
"""),

("""
def foo():
    a: typing.Final = 1

    match ...:
        case [a]: ...
""", """
def foo():
    a = 1

    match ...:
        case [a]: ...
"""),

("""
def foo():
    a: typing.Final = 1

    match ...:
        case (a,): ...
""", """
def foo():
    a = 1

    match ...:
        case (a,): ...
"""),

("""
def foo():
    a: typing.Final = 1
    nonlocal a
""", """
def foo():
    a: typing.Final = 1
    nonlocal a
"""),

("""
def foo():
    a = 1
    nonlocal a
""", """
def foo():
    a = 1
    nonlocal a
"""),

("""
def foo():
    a: typing.Final = 1
    global b
""", """
def foo():
    a: typing.Final = 1
    global b
"""),

("""
def foo():
    a: typing.Final = 1
    global a
""", """
def foo():
    a: typing.Final = 1
    global a
"""),

("""
def foo():
    a = 1
    nonlocal a
""", """
def foo():
    a = 1
    nonlocal a
"""),

("""
def foo():
    a: typing.Final = 1
    global b
""", """
def foo():
    a: typing.Final = 1
    global b
"""),

("""
def foo():
    foo: typing.Final = 1
""", """
def foo():
    foo = 1
"""),

("""
def foo(a, b: int, c=1, d: int = 2):
    a: typing.Final = 1
    b: typing.Final = 2
    c: typing.Final = 3
    d: typing.Final = 4
    e: typing.Final = 5
""", """
def foo(a, b: int, c=1, d: int = 2):
    a = 1
    b = 2
    c = 3
    d = 4
    e: typing.Final = 5
"""),
]
# fmt: on


@pytest.mark.parametrize(("before", "after"), scopes_cases)
def test_scopes(before: str, after: str) -> None:
    assert run_fixer(before.strip()) == after.strip()
