# Variable Declaration with Type Annotation
```python
def foo():
    a: int
```

# Variable Assignment with Inline Comment
```python
def foo():
    a = 1  # insert
```

# Variable Declaration with Final Type Annotation
```python
def foo():
    a: Final = 1
```

# Variable Declaration with Type Annotation and Assignment
```python
def foo():
    a: int = 1   # insert
```

# Annotated Variable with Custom Metadata
```python
def foo():
    a: typing.Annotated[int, 'hello'] = 1   # insert
```

# List Type Annotation and Assignment
```python
def foo():
    a: list[int] = 1   # insert
```

# Variable Assignment with Previous Declaration
```python
def foo():
    b = 1
    a = 2  # insert
    b = 3
```

# Variable Assignment with Reassignment of Another Variable
```python
def foo():
    b = 1
    b = 2
    a = 3  # insert
```

# Variable Assignment with Later Reassignment
```python
def foo():
    a = 1  # insert
    b = 2
    b = 3
```

# Reassignment of a Variable with Previous Assignment
```python
def foo():
    a = 1
    a = 2
    b: int
```

# Variable Declaration After Assignment
```python
def foo():
    a = 1
    a: int
```

# Variable Declaration Before Assignment
```python
def foo():
    a: int
    a = 1
```

# Final Variable Declaration Before Assignment
```python
def foo():
    a: Final
    a = 1
```

# Redundant Type Annotation with Final
```python
def foo():
    a: int
    a: int = 1
```

# Simultaneous Variable Assignment
```python
def foo():
    a, b = 1, 2
```

# Tuple Assignment with Parentheses
```python
def foo():
    (a, b) = 1, 2
```

# Tuple Assignment from Function Return
```python
def foo():
    (a, b) = t()
```

# List Assignment from Function Return
```python
def foo():
    [a, b] = t()
```

# Single Element List Assignment
```python
def foo():
    [a] = t()
```

# Multiple Variable Assignment in a Single Line
```python
def foo():
    a = b = 1
```

# Chained Multiple Variable Assignment
```python
def foo():
    a = b = c = 1
```

# Variable Assignment with Walrus Operator
```python
def foo():
    a = (b := 1)  # insert
```

# Reassignment with Final Annotation
```python
def foo():
    a = 1
    a: Final[int] = 2  # remove
```

# Reassignment with Final Type Declaration
```python
def foo():
    a = 1
    a: Final = 2  # remove
```

# Reassignment with Final Type Declaration (No Space)
```python
def foo():
    a = 1
    a: Final=2  # remove
```

# Simple Variable Reassignment
```python
def foo():
    a = 1
    a =2
```

# Type Annotation Followed by Final Reassignment
```python
def foo():
    a: int = 1
    a: Final[int] = 2  # remove
```

# Final Reassignment After Int Type Annotation
```python
def foo():
    a: int = 1
    a: Final = 2  # remove
```

# Multiple Reassignments with Final and Type Annotation
```python
def foo():
    a: Final = 1  # remove
    a: Final = 2  # remove
    a = 3
    a: int = 4
```

# Final and Assignment in a Single Line
```python
def foo():
    a: Final = b = 1
```

# Variable Assignment and Final Annotation
```python
def foo():
    a = 1  # insert
    b = 2
    b: Final[int] = 3  # remove
```
