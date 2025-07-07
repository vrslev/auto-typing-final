from typing import Final

import pytest

from auto_typing_final.main import transform_file_content
from auto_typing_final.transform import IMPORT_STYLES_TO_IMPORT_CONFIGS


@pytest.mark.parametrize(
    ("before", "after"),
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
)
def test_ignore_comment(before: str, after: str) -> None:
    import_config: Final = IMPORT_STYLES_TO_IMPORT_CONFIGS["final"]
    result: Final = transform_file_content(
        f"{import_config.import_text}\n" + before.strip(), import_config=import_config, ignore_global_vars=False
    )
    assert result == f"{import_config.import_text}\n" + after.strip()
