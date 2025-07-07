### Assigning a Variable Inside a Function
```python
a = 1

def foo():
    a = 2  # insert

    def bar():
        a = 3  # insert
```

### Using `global` to Modify a Global Variable
```python
a = 1

def foo():
    global a
    a = 2
```

### Reassigning a Variable After Importing
```python
def foo():
    from b import bar
    baz = 1  # insert
```

### Reassigning a Variable Imported with an Alias
```python
def foo():
    from b import bar as baz
    bar = 1  # insert
    baz = 1
```

### Reassigning a Variable Declared as Final
```python
def foo():
    from b import bar
    bar: Final = 1  # remove
```

### Reassigning an Imported Final Variable
```python
def foo():
    import bar
    bar: Final = 1  # remove
```

### Reassigning a Final Variable with a Different Name
```python
def foo():
    import baz
    bar: Final = 1
```

### Reassigning Multiple Final Variables
```python
def foo():
    from b import bar, baz
    bar = 1
    baz = 1
```

### Reassigning an Imported Final Variable and Another with an Alias
```python
def foo():
    from b import bar, baz as bazbaz
    bar = 1
    baz = 1  # insert
```

### Reassigning a Dotted Import and an Alias
```python
def foo():
    from b import d.bar, bazbaz as baz
    bar = 1
    baz = 1
```

### Reassigning a Final Variable in a Parenthesized Import
```python
def foo():
    from b import (bar, bazbaz)
    bar = 1
    baz = 1  # insert
```

### Reassigning a Final Variable in a Function Parameter
```python
def foo():
    a: Final = 1  # remove
    a += 1
```

### Reassigning a Final Variable After a Type Annotation
```python
def foo():
    a: Final = 1  # remove
    a: int
```

### Reassigning a Final Variable with Another Final Declaration
```python
def foo():
    a: Final = 1  # remove
    a: Final
```

### Assigning a Single Value to a Tuple
```python
def foo():
    a, b = 1
```

### Reassigning Final Variables in a Tuple Assignment
```python
def foo():
    a: Final = 1  # remove
    b: Final = 2  # remove
    a, b = 3
```

### Reassigning a Final Variable in a Tuple Assignment
```python
def foo():
    a: Final = 1
    b, c = 2
```

### Syntax Error in Tuple Assignment
```python
def foo():
    a, b: Final = 1
```

### Reassigning a Final Variable in a Parenthesized Unpacking
```python
def foo():
    a: Final = 1  # remove
    (a, b) = 2
```

### Reassigning a Final Variable in a Starred Unpacking
```python
def foo():
    a: Final = 1  # remove
    (a, *other) = 2
```

### Reassigning a Final Variable After a Function Definition
```python
def foo():
    def a(): ...
    a: Final = 1  # remove
```

### Reassigning a Final Variable After a Class Definition
```python
def foo():
    class a: ...
    a: Final = 1  # remove
```

### Reassigning a Final Variable with Walrus Assignment
```python
def foo():
    a: Final = 1  # remove
    if a := 1: ...
```

### Reassigning a Variable Inside a While Loop
```python
def foo():
    while True:
        a = 1
```

### Reassigning a Final Variable Inside a While Loop
```python
def foo():
    while True:
        a: Final = 1  # remove
```

### Reassigning a Final Variable Inside a For Loop
```python
def foo():
    for _ in ...:
        a: Final = 1  # remove
```

### Reassigning a Final Variable Inside a Nested Function in a For Loop
```python
def foo():
    for _ in ...:
        def foo():
            a: Final = 1  # remove
```

### Reassigning a Final Variable and Using It in a For Loop
```python
def foo():
    a: Final = 1  # remove
    b: Final = 2

    for _ in ...:
        a: Final = 1  # remove
```

### Reassigning a Variable Inside a For Loop
```python
def foo():
    for _ in ...:
        a = 1
```

### Reassigning a Final Variable Inside a For Loop with the Same Name
```python
def foo():
    a: Final = 1  # remove
    for a in ...: ...
```

### Reassigning a Final Variable Before a Match Statement
```python
def foo():
    a: Final = 1

    match ...:
        case ...: ...
```

### Reassigning a Final Variable in a Match Case with `as`
```python
def foo():
    a: Final = 1  # remove

    match ...:
        case [] as a: ...
```

### Reassigning a Final Variable in a Match Dictionary Pattern
```python
def foo():
    a: Final = 1  # remove

    match ...:
        case {"hello": a, **b}: ...
```

### Reassigning a Final Variable in a Match Dictionary with Double Star
```python
def foo():
    a: Final = 1  # remove

    match ...:
        case {**a}: ...
```

### Reassigning a Final Variable in a Match Class Pattern
```python
def foo():
    a: Final = 1  # remove

    match ...:
        case A(b=a) | B(b=a): ...
```

### Reassigning a Final Variable in a Match List Pattern
```python
def foo():
    a: Final = 1  # remove

    match ...:
        case [b, *a]: ...
```

### Reassigning a Final Variable in a Match List with a Single Element
```python
def foo():
    a: Final = 1  # remove

    match ...:
        case [a]: ...
```

### Reassigning a Final Variable in a Match Tuple with a Single Element
```python
def foo():
    a: Final = 1  # remove

    match ...:
        case (a,): ...
```

### Reassigning a Final Variable with `nonlocal`
```python
def foo():
    a: Final = 1  # remove
    nonlocal a
```

### Reassigning a Variable with `nonlocal`
```python
def foo():
    a = 1
    nonlocal a
```

### Reassigning a Final Variable with `global`
```python
def foo():
    a: Final = 1
    global b
```

### Reassigning a Final Variable with `global a`
```python
def foo():
    a: Final = 1  # remove
    global a
```

### Reassigning Final Variables in Nested Functions
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

### Assigning an Inner Variable with same name as a function

```python
def foo():
    foo = 1  # insert
```

### Reassigning Final Variables in Function Parameters
```python
def foo(a, b: int, c=1, d: int = 2):
    a: Final = 1  # remove
    b: Final = 2  # remove
    c: Final = 3  # remove
    d: Final = 4  # remove
    e: Final = 5
```

### Assigning an Instance Variable in a Method
```python
def foo(self):
    self.me = 1
```

### Assigning to an Attribute of a Variable
```python
a.b = 1
```
