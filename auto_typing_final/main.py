import argparse
import sys
from collections.abc import Iterable
from difflib import unified_diff
from pathlib import Path
from typing import Final, get_args

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
    parser.add_argument("files", type=Path, nargs="*")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--import-style", type=str, choices=get_args(ImportStyle), default="typing-final")

    args: Final = parser.parse_args()
    import_config: Final = IMPORT_STYLES_TO_IMPORT_CONFIGS[args.import_style]

    has_changes = False

    for path in find_all_source_files(args.files):
        with path.open("r+") as file:
            source = file.read()
            transformed_content = transform_file_content(source=source, import_config=import_config)
            if source == transformed_content:
                continue

            has_changes = True

            if args.check:
                sys.stdout.writelines(
                    unified_diff(
                        source.splitlines(keepends=True),
                        transformed_content.splitlines(keepends=True),
                        fromfile=str(path),
                        tofile=str(path),
                    )
                )
            else:
                file.seek(0)
                file.write(transformed_content)
                file.truncate()

    return has_changes if args.check else 0
