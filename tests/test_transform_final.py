from typing import Final

import pytest

from auto_typing_final.main import transform_file_content
from auto_typing_final.transform import IMPORT_STYLES_TO_IMPORT_CONFIGS, ImportConfig
from tests.conftest import assert_md_test_case_transformed, parse_md_test_cases


@pytest.mark.parametrize("import_config", IMPORT_STYLES_TO_IMPORT_CONFIGS.values())
@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("a: typing.Annotated[int, 'hello'] = 1", "a: {}[typing.Annotated[int, 'hello']] = 1"),
        ("a: list[int] = 1", "a: {}[list[int]] = 1"),
        ("a = 1\na: {}[int] = 2", "a = 1\na: int = 2"),
        ("a = 1\nb = 2\nb: {}[int] = 3", "a: {} = 1\nb = 2\nb: int = 3"),
    ],
)
def test_tricky_annotations_exact_match(import_config: ImportConfig, before: str, after: str) -> None:
    source_function_content: Final = "\n".join(
        f"    {line.format(import_config.value)}" for line in before.splitlines()
    )
    source: Final = f"""
{import_config.import_text}

def foo():
{source_function_content}
"""

    after_function_content: Final = "\n".join(f"    {line.format(import_config.value)}" for line in after.splitlines())
    after_source: Final = f"""
{import_config.import_text}

def foo():
{after_function_content}
"""
    assert (
        transform_file_content(source.strip(), import_config=import_config, ignore_global_vars=False)
        == after_source.strip()
    )


class TestWithMdTests:
    @pytest.mark.parametrize("case", parse_md_test_cases("function_vars.md"))
    def test_function_vars(self, case: str, import_config: ImportConfig, ignore_global_vars: bool) -> None:
        result: Final = transform_file_content(
            f"{import_config.import_text}\n{case}", import_config=import_config, ignore_global_vars=ignore_global_vars
        )
        assert_md_test_case_transformed(test_case=case, transformed_result=result, import_config=import_config)

    @pytest.mark.parametrize("case", parse_md_test_cases("syntax_and_scopes.md"))
    def test_syntax_and_scopes(self, case: str, import_config: ImportConfig, ignore_global_vars: bool) -> None:
        result: Final = transform_file_content(
            f"{import_config.import_text}\n{case}", import_config=import_config, ignore_global_vars=ignore_global_vars
        )
        assert_md_test_case_transformed(test_case=case, transformed_result=result, import_config=import_config)

    @pytest.mark.parametrize("case", parse_md_test_cases("global_vars_enabled.md"))
    def test_global_vars_enabled(self, case: str, import_config: ImportConfig) -> None:
        result: Final = transform_file_content(
            f"{import_config.import_text}\n{case}", import_config=import_config, ignore_global_vars=False
        )
        assert_md_test_case_transformed(test_case=case, transformed_result=result, import_config=import_config)

    @pytest.mark.parametrize("case", parse_md_test_cases("global_vars_with_ignore_flag.md"))
    def test_global_vars_with_ignored_flag(self, case: str, import_config: ImportConfig) -> None:
        result: Final = transform_file_content(
            f"{import_config.import_text}\n{case}", import_config=import_config, ignore_global_vars=True
        )
        assert_md_test_case_transformed(test_case=case, transformed_result=result, import_config=import_config)

    @pytest.mark.parametrize("case", parse_md_test_cases("ignore_comment.md"))
    def test_ignore_comment_global_vars_enabled(self, case: str, import_config: ImportConfig) -> None:
        result: Final = transform_file_content(
            f"{import_config.import_text}\n" + case,
            import_config=import_config,
            ignore_global_vars=False,
        )
        assert_md_test_case_transformed(test_case=case, transformed_result=result, import_config=import_config)


def test_ignore_comment_global_vars_disabled(import_config: ImportConfig) -> None:
    case: Final = f"{import_config.import_text}\nVAR_WITH_COMMENT = 1 # some comment"
    result: Final = transform_file_content(case, import_config=import_config, ignore_global_vars=True)
    assert result == case
