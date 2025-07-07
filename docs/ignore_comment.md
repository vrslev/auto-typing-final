# Variable with a comment
```python
VAR_WITH_COMMENT = 1 # some comment  # insert
```

### Ignored variable without type annotation
```python
IGNORED_VAR = 1 # auto-typing-final: ignore
```

### Ignored variable with `Final` type annotation
```python
IGNORED_VAR: Final = 1 # auto-typing-final: ignore
```

### Ignored variable with `Final` type annotation and additional comment
```python
IGNORED_VAR: Final = 1 # auto-typing-final: ignore  # some comment
```

### Function with an assigned variable
```python
def foo():
    a = 1  # insert
```

### Function with an ignored variable
```python
def foo():
    a = 1  # auto-typing-final: ignore
```
