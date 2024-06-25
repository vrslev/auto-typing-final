# auto-typing-final

Auto-fixer for Python code that:

- sets `typing.Final` inside functions for variables that are not reassigned
- and removes `typing.Final` from variables that are reassined.

## How To Use

```sh
uv tool run auto-typing-final *files*
```

or

```sh
pipx run auto-typing-final *files*
```

### Setting up VS Code keybinding

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
