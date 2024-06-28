# auto-typing-final

Auto-fixer for Python code that would:

- set `typing.Final` inside functions for variables that are not reassigned,
- and remove `typing.Final` from variables that _are_ reassigned.

## How To Use

```sh
uv tool run auto-typing-final .
```

or:

```sh
pipx run auto-typing-final .
```

You can specify `--check` flag to check only, without fixing:

```sh
pipx run auto-typing-final . --check
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
