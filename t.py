for before, after in (
    [
        ("VAR_WITH_COMMENT = 1 # some comment", "VAR_WITH_COMMENT: Final = 1 # some comment"),
        ("IGNORED_VAR = 1 # auto-typing-final: ignore", "IGNORED_VAR = 1 # auto-typing-final: ignore"),
        ("IGNORED_VAR: Final = 1 # auto-typing-final: ignore", "IGNORED_VAR: Final = 1 # auto-typing-final: ignore"),
        (
            "IGNORED_VAR: Final = 1 # auto-typing-final: ignore  # some comment",
            "IGNORED_VAR: Final = 1 # auto-typing-final: ignore  # some comment",
        ),
        ("def foo():\n a = 1", "def foo():\n a: Final = 1"),
        ("def foo():\n a = 1  # auto-typing-final: ignore", "def foo():\n a = 1  # auto-typing-final: ignore"),
    ],
)[0]:
    t = "\n".join(f"    {line.format("Final")}" for line in before.splitlines())
    print(f"""# 1\n\n```python\ndef foo():\n{t}\n```\n""")
