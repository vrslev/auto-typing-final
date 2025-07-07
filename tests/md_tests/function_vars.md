# 1

```python
def foo():
    a: int
```

# 1

```python
def foo():
    a = 1  # insert
```

# 1

```python
def foo():
    a: Final = 1
```

# 1

```python
def foo():
    a: int = 1   # insert
```

# 1

```python
def foo():
    a: typing.Annotated[int, 'hello'] = 1   # insert
```

# 1

```python
def foo():
    a: list[int] = 1   # insert
```

# 1

```python
def foo():
    b = 1
    a = 2  # insert
    b = 3
```

# 1

```python
def foo():
    b = 1
    b = 2
    a = 3  # insert
```

# 1

```python
def foo():
    a = 1  # insert
    b = 2
    b = 3
```

# 1

```python
def foo():
    a = 1
    a = 2
    b: int
```

# 1

```python
def foo():
    a = 1
    a: int
```

# 1

```python
def foo():
    a: int
    a = 1
```

# 1

```python
def foo():
    a: Final
    a = 1
```

# 1

```python
def foo():
    a: int
    a: int = 1
```

# 1

```python
def foo():
    a, b = 1, 2
```

# 1

```python
def foo():
    (a, b) = 1, 2
```

# 1

```python
def foo():
    (a, b) = t()
```

# 1

```python
def foo():
    [a, b] = t()
```

# 1

```python
def foo():
    [a] = t()
```

# 1

```python
def foo():
    a = b = 1
```

# 1

```python
def foo():
    a = b = c = 1
```

# 1

```python
def foo():
    a = (b := 1)  # insert
```

# 1

```python
def foo():
    a = 1
    a: Final[int] = 2  # remove
```

# 1

```python
def foo():
    a = 1
    a: Final = 2  # remove
```

# 1

```python
def foo():
    a = 1
    a: Final=2  # remove
```

# 1

```python
def foo():
    a = 1
    a =2
```

# 1

```python
def foo():
    a: int = 1
    a: Final[int] = 2  # remove
```

# 1

```python
def foo():
    a: int = 1
    a: Final = 2  # remove
```

# 1

```python
def foo():
    a: Final = 1  # remove
    a: Final = 2  # remove
    a = 3
    a: int = 4
```

# 1

```python
def foo():
    a: Final = b = 1
```

# 1

```python
def foo():
    a = 1  # insert
    b = 2
    b: Final[int] = 3  # remove
```
