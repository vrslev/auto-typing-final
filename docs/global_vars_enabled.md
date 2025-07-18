Test for global variables for case when running **without** `ignore-global-vars`.

### Constants and Variable Assignments
```python
MY_CONSTANT = 42  # insert
MY_OTHER_CONSTANT = "hello"  # insert
```

### Debug Flag Assignment
```python
DEBUG = True  # insert
```

### Global vs. Local Variable Scope
```python
MY_CONSTANT = 42  # insert
global_var = "hello"  # insert

def foo():
    local_var = 1  # insert
```

### Constants with Type Hints
```python
MY_CONSTANT: typing.Final = 42
MY_OTHER_CONSTANT = "hello"  # insert
```

### Constants with Explicit Typing
```python
MY_CONSTANT: int = 42  # insert
MY_OTHER_CONSTANT = "hello"  # insert
```

### Constant Shadowing in Function Scope
```python
MY_CONSTANT = 42  # insert

def foo():
    MY_CONSTANT = 1  # insert
    local_var = 2  # insert
```

### Union Types for Constants
```python
FRUIT = Apple | Banana  # insert
```

### Code Examples with Header Improvements

### Changed lower case assignment
```python
global_var = 42  # insert
```

### Not lower case assignment
```python
myVar = "hello"
```

### Constant Assignment
```python
A = 42
```

### Constants with Global Statement

```python
MY_CONSTANT = 42

def foo():
    global MY_CONSTANT
    MY_CONSTANT = 1
```

### Constants with Global Declaration
```python
from foo import MY_CONSTANT
MY_CONSTANT = 42
```

### Final Assignment for Constants
```python
a: typing.Final = 1
```

### TypeVar Declaration for Generics
```python
_T = typing.TypeVar("_T")
```

### Final TypeVar Declaration
```python
_T: typing.Final = typing.TypeVar("_T")
```

### ParamSpec Declaration for Function Generics
```python
_P = typing.ParamSpec("_P")
```

### Final ParamSpec Declaration
```python
_P: typing.Final = typing.ParamSpec("_P")
```

### Union Types for Variables
```python
Fruit = Apple | Banana
```

### String Assignment for Constants
```python
A = "ParamSpec"
```
