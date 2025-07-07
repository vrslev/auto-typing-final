from typing import Final

import pytest

from auto_typing_final.main import transform_file_content
from auto_typing_final.transform import ImportConfig
from tests.conftest import assert_md_test_case_transformed, parse_md_test_cases


@pytest.mark.parametrize("case", parse_md_test_cases("ignore_comment.md"))
def test_ignore_comment_global_vars_enabled(case: str, import_config: ImportConfig) -> None:
    result: Final = transform_file_content(
        f"{import_config.import_text}\n" + case,
        import_config=import_config,
        ignore_global_vars=False,
    )
    assert_md_test_case_transformed(test_case=case, transformed_result=result, import_config=import_config)


def test_ignore_comment_global_vars_disabled(import_config: ImportConfig) -> None:
    case: Final = "VAR_WITH_COMMENT = 1 # some comment"
    result: Final = transform_file_content(
        f"{import_config.import_text}\n{case}",
        import_config=import_config,
        ignore_global_vars=True,
    )
    assert_md_test_case_transformed(test_case=case, transformed_result=result, import_config=import_config)
