# Global Constants and Variable Declaration

```python
MY_CONSTANT = 42
MY_OTHER_CONSTANT = "hello"
global_var = 123

def foo():
    local_var = 1  # insert
```

# Function Scope and Variable Shadowing
```python
MY_CONSTANT = 42

def foo():
    MY_CONSTANT = 1  # insert
    local_var = 2  # insert
```
