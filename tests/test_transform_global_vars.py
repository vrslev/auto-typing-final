from typing import Final

import pytest

from auto_typing_final.main import transform_file_content
from auto_typing_final.transform import ImportConfig
from tests.conftest import assert_md_test_case_transformed, parse_md_test_cases


@pytest.mark.parametrize("case", parse_md_test_cases("global_vars_enabled.md"))
def test_global_vars_enabled(case: str, import_config: ImportConfig) -> None:
    result: Final = transform_file_content(
        f"{import_config.import_text}\n{case}", import_config=import_config, ignore_global_vars=False
    )
    assert_md_test_case_transformed(test_case=case, transformed_result=result, import_config=import_config)


@pytest.mark.parametrize("case", parse_md_test_cases("global_vars_with_ignore_flag.md"))
def test_global_vars_with_ignored_flag(case: str, import_config: ImportConfig) -> None:
    result: Final = transform_file_content(
        f"{import_config.import_text}\n{case}", import_config=import_config, ignore_global_vars=True
    )
    assert_md_test_case_transformed(test_case=case, transformed_result=result, import_config=import_config)
