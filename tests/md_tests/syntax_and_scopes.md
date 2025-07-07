# 1

```python
a = 1

def foo():
    a = 2  # insert

    def bar():
        a = 3  # insert
```

# 1

```python
a = 1

def foo():
    global a
    a = 2
```

# 1

```python
def foo():
    from b import bar
    baz = 1  # insert
```

# 1

```python
def foo():
    from b import bar as baz
    bar = 1  # insert
    baz = 1
```

# 1

```python
def foo():
    from b import bar
    bar: Final = 1  # remove
```

# 1

```python
def foo():
    import bar
    bar: Final = 1  # remove
```

# 1

```python
def foo():
    import baz
    bar: Final = 1
```

# 1

```python
def foo():
    from b import bar, baz
    bar = 1
    baz = 1
```

# 1

```python
def foo():
    from b import bar, baz as bazbaz
    bar = 1
    baz = 1  # insert
```

# 1

```python
def foo():
    # Dotted paths are not allowed, but tree-sitter-python grammar permits it
    from b import d.bar, bazbaz as baz
    bar = 1
    baz = 1
```

# 1

```python
def foo():
    from b import (bar, bazbaz)
    bar = 1
    baz = 1  # insert
```

# 1

```python
def foo():
    a: Final = 1  # remove
    a += 1
```

# 1

```python
def foo():
    a: Final = 1  # remove
    a: int
```

# 1

```python
def foo():
    a: Final = 1  # remove
    a: Final
```

# 1

```python
def foo():
    a, b = 1
```

# 1

```python
def foo():
    a: Final = 1  # remove
    b: Final = 2  # remove
    a, b = 3
```

# 1

```python
def foo():
    a: Final = 1
    b, c = 2
```

# 1

```python
def foo():
    a, b: Final = 1
```

# 1

```python
def foo():
    a: Final = 1  # remove
    (a, b) = 2
```

# 1

```python
def foo():
    a: Final = 1  # remove
    (a, *other) = 2
```

# 1

```python
def foo():
    def a(): ...
    a: Final = 1  # remove
```

# 1

```python
def foo():
    class a: ...
    a: Final = 1  # remove
```

# 1

```python
def foo():
    a: Final = 1  # remove
    if a := 1: ...
```

# 1

```python
def foo():
    while True:
        a = 1
```

# 1

```python
def foo():
    while True:
        a: Final = 1  # remove
```

# 1

```python
def foo():
    for _ in ...:
        a: Final = 1  # remove
```

# 1

```python
def foo():
    for _ in ...:
        def foo():
            a: Final = 1  # remove
```

# 1

```python
def foo():
    a: Final = 1  # remove
    b: Final = 2

    for _ in ...:
        a: Final = 1  # remove
```

# 1

```python
def foo():
    for _ in ...:
        a = 1
```

# 1

```python
def foo():
    a: Final = 1  # remove
    for a in ...: ...
```

# 1

```python
def foo():
    a: Final = 1

    match ...:
        case ...: ...
```

# 1

```python
def foo():
    a: Final = 1  # remove

    match ...:
        case [] as a: ...
```

# 1

```python
def foo():
    a: Final = 1  # remove

    match ...:
        case {"hello": a, **b}: ...
```

# 1

```python
def foo():
    a: Final = 1  # remove

    match ...:
        case {**a}: ...
```

# 1

```python
def foo():
    a: Final = 1  # remove

    match ...:
        case A(b=a) | B(b=a): ...
```

# 1

```python
def foo():
    a: Final = 1  # remove

    match ...:
        case [b, *a]: ...
```

# 1

```python
def foo():
    a: Final = 1  # remove

    match ...:
        case [a]: ...
```

# 1

```python
def foo():
    a: Final = 1  # remove

    match ...:
        case (a,): ...
```

# 1

```python
def foo():
    a: Final = 1  # remove
    nonlocal a
```

# 1

```python
def foo():
    a = 1
    nonlocal a
```

# 1

```python
def foo():
    a: Final = 1
    global b
```

# 1

```python
def foo():
    a: Final = 1  # remove
    global a
```

# 1

```python
def foo():
    a: Final = 1  # remove
    b: Final = 2
    c: Final = 3

    def bar():
        nonlocal a
        b: Final = 4  # remove
        c: Final = 5

        class C:
            a = 6
            c = 7

            def baz():
                nonlocal a, b
                b: Final = 8  # remove
                c: Final = 9
```

# 1

```python
def foo():
    foo = 1  # insert
```

# 1

```python
def foo(a, b: int, c=1, d: int = 2):
    a: Final = 1  # remove
    b: Final = 2  # remove
    c: Final = 3  # remove
    d: Final = 4  # remove
    e: Final = 5
```

# 1

```python
def foo(self):
    self.me = 1
```

# 1

```python
a.b = 1
```
