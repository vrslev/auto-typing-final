# auto-typing-final

Auto-fixer for Python code that adds `typing.Final` annotation to variable assignments inside functions that are not reassigned, and removes the annotation from variables that _are_ mutated.

```diff
 def foo() -> None:
-    a = 2
+    a: typing.Final = 2

-    b: typing.Final = 2
+    b = 2
     b = 3
```

Basically, this, but handles different operations (like usage of `nonlocal`, augmented assignments: `+=`, etc) as well.

- Keeps mypy happy.
- Ignores global variables to avoid confusion with the type aliases like `Fruit = Apple | Banana`.
- Ignores class variables: it is common to use `typing.ClassVar` instead of `typing.Final`.
- Adds global `typing` import if it's not imported yet.
- Inspects one file at a time.

## How To Use

Having uv installed:

```sh
uvx auto-typing-final .
```

or:

```sh
pipx run auto-typing-final .
```

You can specify `--check` flag to check the files instead of actually fixing them:

```sh
auto-typing-final . --check
```

You also can install VS Code extension. It uses installation of `auto-typing-final` from the current Python environment and shows diagnostics and quick fixes.

To get started, add `auto-typing-final` to your project:

```sh
uv add auto-typing-final --dev
```

or:

```sh
poetry add auto-typing-final --group=dev
```

And install the extension: https://marketplace.visualstudio.com/items?itemName=vrslev.auto-typing-final.
