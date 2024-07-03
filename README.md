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

### VS Code key binding

Add to your `keybindings.json`:

```json
{
  "key": "ctrl+shift+t",
  "when": "editorLangId == 'python'",
  "command": "runCommands",
  "args": {
    "commands": [
      "workbench.action.files.save",
      "workbench.action.terminal.newInActiveWorkspace",
      "workbench.action.terminal.toggleTerminal",
      {
        "command": "workbench.action.terminal.sendSequence",
        "args": {
          "text": "uvx auto-typing-final ${file}\u000Dexit\u000D"
        }
      }
    ]
  }
}
```
