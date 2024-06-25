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


scopes_case = (
    """
a = 1
b, c = 1
MUTABLE_FIRST = 1
MUTABLE_FIRST = 2

@f
class A:
    def first(self) -> None:
        a = 1

        if a:
            b = 2

        if ...: c = 3

        if ...:
            a = 4

        while ...:
            ...

        for _ in ...:
            ...

        async for _ in ...: ...

        with ...:
            d = 5

        async with ...:
            e = 6

@s()
class B(A):
    def duplicated(self) -> None:
        a = 1
        a = 2

def second() -> whatever:
    hi = "hi"
    for _ in ...:
        me = 1
    ih = 0
    ih += 1

class C:
    @t(a=1)
    def duplicated(self) -> None:
        a: typing.Final = 2
        a = 1

MUTABLE_SECOND = 1
CONSTANT = 300
MUTABLE_SECOND: int = 2

def fourth() -> None:
    def inner() -> None:
        @f(a=2)
        def inner_inner() -> None:
            a = 1
            sss = 1

        a: typing.Final = 1
        b = 2
        c: typing.Final = 3

    class A:
        a = 1

        def fifth() -> None:
            a = 1

    a = 1
""",
    """
a = 1
b, c = 1
MUTABLE_FIRST = 1
MUTABLE_FIRST = 2

@f
class A:
    def first(self) -> None:
        a = 1

        if a:
            b: typing.Final = 2

        if ...: c: typing.Final = 3

        if ...:
            a = 4

        while ...:
            ...

        for _ in ...:
            ...

        async for _ in ...: ...

        with ...:
            d: typing.Final = 5

        async with ...:
            e: typing.Final = 6

@s()
class B(A):
    def duplicated(self) -> None:
        a = 1
        a = 2

def second() -> whatever:
    hi: typing.Final = "hi"
    for _ in ...:
        me = 1
    ih = 0
    ih += 1

class C:
    @t(a=1)
    def duplicated(self) -> None:
        a = 2
        a = 1

MUTABLE_SECOND = 1
CONSTANT = 300
MUTABLE_SECOND: int = 2

def fourth() -> None:
    def inner() -> None:
        @f(a=2)
        def inner_inner() -> None:
            a: typing.Final = 1
            sss: typing.Final = 1

        a: typing.Final = 1
        b: typing.Final = 2
        c: typing.Final = 3

    class A:
        a = 1

        def fifth() -> None:
            a: typing.Final = 1

    a: typing.Final = 1

""",
)


@pytest.mark.parametrize(("before", "after"), [scopes_case])
def test_scopes(before: str, after: str) -> None:
    assert run_fixer(before.strip()) == after.strip()
