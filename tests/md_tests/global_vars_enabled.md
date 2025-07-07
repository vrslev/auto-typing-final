# insert
## 1

```python
MY_CONSTANT = 42  # insert
MY_OTHER_CONSTANT = "hello"  # insert
```

## 5

```python
DEBUG = True  # insert
```

## 6

```python
MY_CONSTANT = 42  # insert
global_var = "hello"

def foo():
    local_var = 1  # insert
```

## 7

```python
MY_CONSTANT: typing.Final = 42
MY_OTHER_CONSTANT = "hello"  # insert
```

## 8

```python
MY_CONSTANT: int = 42  # insert
MY_OTHER_CONSTANT = "hello"  # insert
```

## 9

```python
MY_CONSTANT = 42  # insert

def foo():
    MY_CONSTANT = 1  # insert
    local_var = 2  # insert
```

## 10

```python
FRUIT = Apple | Banana  # insert
```

# remain unchanged
## 2

```python
global_var = 42
```

## 3

```python
myVar = "hello"
```

## 4

```python
A = 42
```

## 10

```python
MY_CONSTANT = 42

def foo():
    global MY_CONSTANT
    MY_CONSTANT = 1
```

## 10

```python
from foo import MY_CONSTANT
MY_CONSTANT = 42
```

## 10

```python
a: typing.Final = 1
```

## 10

```python
_T = typing.TypeVar("_T")
```

## 10

```python
_T: typing.Final = typing.TypeVar("_T")
```

## 10

```python
_P = typing.ParamSpec("_P")
```

## 10

```python
_P: typing.Final = typing.ParamSpec("_P")
```

## 10

```python
Fruit = Apple | Banana
```

## 10

```python
A = "ParamSpec"
```
