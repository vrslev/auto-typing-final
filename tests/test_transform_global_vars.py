import pathlib
from typing import Final

import pytest

from auto_typing_final.main import transform_file_content
from auto_typing_final.transform import IMPORT_STYLES_TO_IMPORT_CONFIGS, ImportConfig


@pytest.mark.parametrize(
    "case",
    [
        # Test that allows UPPER_CASE global constants
        """
MY_CONSTANT = 42
MY_OTHER_CONSTANT = "hello"
---
import typing
MY_CONSTANT: typing.Final = 42
MY_OTHER_CONSTANT: typing.Final = "hello"
""",
        # Test that non-UPPER_CASE global variables are still ignored
        """
global_var = 42
myVar = "hello"
---
global_var = 42
myVar = "hello"
""",
        # Test single letter constants are ignored
        """
A = 42
B = "hello"
---
A = 42
B = "hello"
""",
        # Test single word constants are ignored (like DEBUG, VERSION)
        """
DEBUG = True
VERSION = "1.0"
---
import typing
DEBUG: typing.Final = True
VERSION: typing.Final = "1.0"
""",
        # Test mixed case - function variables should still work
        """
MY_CONSTANT = 42
global_var = "hello"

def foo():
    local_var = 1
---
import typing
MY_CONSTANT: typing.Final = 42
global_var = "hello"

def foo():
    local_var: typing.Final = 1
""",
        # Test with existing Final annotation
        """
MY_CONSTANT: typing.Final = 42
MY_OTHER_CONSTANT = "hello"
---
import typing
MY_CONSTANT: typing.Final = 42
MY_OTHER_CONSTANT: typing.Final = "hello"
""",
        # Test with existing typed annotation
        """
MY_CONSTANT: int = 42
MY_OTHER_CONSTANT = "hello"
---
import typing
MY_CONSTANT: typing.Final[int] = 42
MY_OTHER_CONSTANT: typing.Final = "hello"
""",
        # Test local vars with same name as global vars
        """
MY_CONSTANT = 42

def foo():
    MY_CONSTANT = 1
    local_var = 2
---
import typing
MY_CONSTANT: typing.Final = 42

def foo():
    MY_CONSTANT: typing.Final = 1
    local_var: typing.Final = 2
""",
        # Test local vars with same name as global vars
        """
MY_CONSTANT = 42

def foo():
    global MY_CONSTANT
    MY_CONSTANT = 1
---
MY_CONSTANT = 42

def foo():
    global MY_CONSTANT
    MY_CONSTANT = 1
""",
        """
from foo import MY_CONSTANT
MY_CONSTANT = 42
---
from foo import MY_CONSTANT
MY_CONSTANT = 42
""",
        """
a: typing.Final = 1
---
a: typing.Final = 1
""",
        """
_T = typing.TypeVar("_T")
---
_T = typing.TypeVar("_T")
""",
        """
_T: typing.Final = typing.TypeVar("_T")
---
_T: typing.Final = typing.TypeVar("_T")
""",
        """
_P = typing.ParamSpec("_P")
---
_P = typing.ParamSpec("_P")
""",
        """
_P: typing.Final = typing.ParamSpec("_P")
---
_P: typing.Final = typing.ParamSpec("_P")
""",
        """
Fruit = Apple | Banana
---
Fruit = Apple | Banana
""",
        """
FRUIT = Apple | Banana
---
import typing
FRUIT: typing.Final = Apple | Banana
""",
        """
A = "ParamSpec"
---
A = "ParamSpec"
""",
    ],
)
def test_default_behavior_processes_upper_case_globals(case: str) -> None:
    import_config: Final = IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"]
    before, _, after = case.partition("---")
    result: Final = transform_file_content(before.strip(), import_config=import_config, ignore_global_vars=False)
    assert result == after.strip()


@pytest.mark.parametrize(
    "case",
    [
        # Test --ignore-global-vars flag: should ignore all global variables (preserve old behavior)
        """
MY_CONSTANT = 42
MY_OTHER_CONSTANT = "hello"
global_var = 123

def foo():
    local_var = 1
---
import typing
MY_CONSTANT = 42
MY_OTHER_CONSTANT = "hello"
global_var = 123

def foo():
    local_var: typing.Final = 1
""",
        # Test --ignore-global-vars with local vars same name as global
        """
MY_CONSTANT = 42

def foo():
    MY_CONSTANT = 1
    local_var = 2
---
import typing
MY_CONSTANT = 42

def foo():
    MY_CONSTANT: typing.Final = 1
    local_var: typing.Final = 2
""",
    ],
)
def test_ignore_global_vars_flag_preserves_old_behavior(case: str) -> None:
    import_config: Final = IMPORT_STYLES_TO_IMPORT_CONFIGS["typing-final"]
    before, _, after = case.partition("---")
    result: Final = transform_file_content(before.strip(), import_config=import_config, ignore_global_vars=True)
    assert result == after.strip()


def parse_md_test_cases(file_name: str) -> list[str]:
    md_test = (pathlib.Path(__file__).parent / "md_tests" / file_name).read_text()
    test_cases: Final = []
    while True:
        index_before = md_test.find("```python")
        if index_before == -1:
            break
        case_with_tail = md_test[index_before:].removeprefix("```python")
        index_after = case_with_tail.find("```")
        if index_after == -1:
            break
        test_cases.append(case_with_tail[:index_after].strip())
        md_test = case_with_tail[index_after:].removeprefix("```")
    return test_cases


def assert_md_test_case_transformed(*, test_case: str, transformed_result: str, import_config: ImportConfig) -> None:
    for one_before_line, one_after_line in zip(
        test_case.splitlines(),
        transformed_result.removeprefix(import_config.import_text + "\n").splitlines(),
        strict=True,
    ):
        if "# insert" in one_before_line:
            assert import_config.import_identifier in one_after_line
        elif "# remove" in one_before_line:
            assert "Final" in one_before_line
            assert import_config.import_text not in one_after_line
        else:
            assert one_before_line == one_after_line


@pytest.mark.parametrize("import_config", IMPORT_STYLES_TO_IMPORT_CONFIGS.values())
@pytest.mark.parametrize("case", parse_md_test_cases("global_vars.md"))
def test_new(case: str, import_config: ImportConfig) -> None:
    result: Final = transform_file_content(
        f"{import_config.import_text}\n{case}", import_config=import_config, ignore_global_vars=False
    )
    assert_md_test_case_transformed(test_case=case, transformed_result=result, import_config=import_config)
