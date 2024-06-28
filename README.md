# auto-typing-final

Auto-fixer for Python code that adds `typing.Final` annotation to variable assignments inside functions that are not reassigned, and removes the annotation from variables that _are_ mutated.

Keeps mypy happy.

- Global `import typing` will be added if `typing` was not imported before.
- Global variables are ignored to avoid confusion with the type aliases like `Fruit = Apple | Banana`.
- Class variables are ignored since it is common to use `typing.ClassVar` instead of `typing.Final`.
- One file at a time is inspected.

## How To Use

```sh
uv tool run auto-typing-final .
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
          "text": "uv tool run auto-typing-final ${file}\u000Dexit\u000D"
        }
      }
    ]
  }
}
```
