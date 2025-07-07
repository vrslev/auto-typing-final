import pathlib
import typing
from typing import Final

import pytest

from auto_typing_final.transform import IMPORT_STYLES_TO_IMPORT_CONFIGS, ImportConfig


@pytest.fixture(params=IMPORT_STYLES_TO_IMPORT_CONFIGS.values())
def import_config(request: pytest.FixtureRequest) -> ImportConfig:
    return typing.cast(ImportConfig, request.param)


@pytest.fixture(params=[True, False])
def ignore_global_vars(request: pytest.FixtureRequest) -> bool:
    return typing.cast(bool, request.param)


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
            assert import_config.value in one_after_line, test_case
        elif "# remove" in one_before_line:
            assert "Final" in one_before_line, test_case
            assert import_config.value not in one_after_line
        else:
            assert one_before_line == one_after_line, test_case


def parse_before_after_test_case(test_case: str) -> tuple[str, str]:
    before, _, after = test_case.partition("---")
    return before.strip(), after.strip()
