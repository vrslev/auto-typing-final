from tests.conftest import parse_before_after_test_case


for case in [
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
    ]:
    before, after = parse_before_after_test_case(case)
    # print(before)
    # print()
    # t = "\n".join(f"    {line.format("Final")}" for line in before.splitlines())
    print(f"""# 1\n\n```python\n{before}\n```\n""")
