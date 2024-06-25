# auto-typing-final

Auto-fixer for Python code that would:

- set `typing.Final` inside functions for variables that are not reassigned,
- and remove `typing.Final` from variables that *are* reassigned.

## How To Use

```sh
uv tool run auto-typing-final ./**/*.py
```

or:

```sh
pipx run auto-typing-final main.py
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
