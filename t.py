for before, after in [
    ("a: typing.Annotated[int, 'hello'] = 1", "a: {}[typing.Annotated[int, 'hello']] = 1"),
    ("a: list[int] = 1", "a: {}[list[int]] = 1"),
    ("a = 1\na: {}[int] = 2", "a = 1\na: int = 2"),
    ("a = 1\nb = 2\nb: {}[int] = 3", "a: {} = 1\nb = 2\nb: int = 3"),
]:
    t = "\n".join(f"    {line.format("Final")}" for line in before.splitlines())
    print(f"""# 1\n\n```python\ndef foo():\n{t}\n```\n""")
