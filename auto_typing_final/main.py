import argparse
import sys
from collections.abc import Iterable
from difflib import unified_diff
from pathlib import Path
from typing import Final, cast, get_args

from ast_grep_py import SgRoot

from auto_typing_final.transform import IMPORT_STYLES_TO_IMPORT_CONFIGS, ImportConfig, ImportStyle, make_replacements


def transform_file_content(source: str, import_config: ImportConfig) -> str:
    root: Final = SgRoot(source, "python").root()
    result: Final = make_replacements(root, import_config)
    new_text: Final = root.commit_edits(
        [edit.node.replace(edit.new_text) for replacement in result.replacements for edit in replacement.edits]
    )
    return root.commit_edits([root.replace(f"{result.import_text}\n{new_text}")]) if result.import_text else new_text


def take_python_source_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.suffix in {".py", ".pyi"}:
            yield path


def find_source_files_from_one_path(path: Path) -> Iterable[Path]:
    if path.is_dir():
        for inner_path in path.iterdir():
            if inner_path.name.startswith("."):
                continue
            yield from take_python_source_files(find_source_files_from_one_path(inner_path))

    else:
        yield path


def find_all_source_files(paths: list[Path]) -> Iterable[Path]:
    for path in paths:
        yield from find_source_files_from_one_path(path)


def main() -> int:
    parser: Final = argparse.ArgumentParser()
    parser.add_argument("files", type=Path, nargs="*", default=[Path()])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--import-style", type=str, choices=get_args(ImportStyle), default="typing-final")

    args: Final = parser.parse_args()
    import_config: Final = IMPORT_STYLES_TO_IMPORT_CONFIGS[args.import_style]
    open_mode: Final = "r" if args.check else "r+"
    changed_files_count = 0

    for path in find_all_source_files(args.files):
        with path.open(open_mode) as file:
            source = file.read()
            transformed_content = transform_file_content(source=source, import_config=import_config)
            if source == transformed_content:
                continue
            changed_files_count += 1

            if args.check:
                sys.stdout.writelines(
                    unified_diff(
                        source.splitlines(keepends=True),
                        transformed_content.splitlines(keepends=True),
                        fromfile=str(path),
                        tofile=str(path),
                    )
                )
                sys.stdout.write("\n")
            else:
                file.seek(0)
                file.write(transformed_content)
                file.truncate()

    match changed_files_count, cast(bool, args.check):
        case 0, _:
            result_message = "No errors found!"
        case 1, True:
            result_message = "Found errors in 1 file."
        case 1, False:
            result_message = "Fixed errors in 1 file."
        case _, True:
            result_message = f"Found errors in {changed_files_count} files."
        case _, False:
            result_message = f"Fixed errors in {changed_files_count} files."

    sys.stdout.write(f"{result_message}\n")
    return changed_files_count > 0 if args.check else 0
