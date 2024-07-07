import argparse
import sys
from collections.abc import Iterable
from difflib import unified_diff
from pathlib import Path

from ast_grep_py import SgRoot

from auto_typing_final.transform import (
    IMPORT_MODES_TO_IMPORT_CONFIGS,
    ImportConfig,
    ImportMode,
    make_operations_from_root,
)


def transform_file_content(source: str, import_config: ImportConfig) -> str:
    root = SgRoot(source, "python").root()
    operations, import_string = make_operations_from_root(root, import_config)
    result = root.commit_edits(
        [node.replace(new_text) for applied_operation in operations for node, new_text in applied_operation.edits]
    )
    return root.commit_edits([root.replace(f"{import_string}\n{result}")]) if import_string else result


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
    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=Path, nargs="*")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--import-mode", type=ImportMode, default=ImportMode.typing_final)

    args = parser.parse_args()
    import_config = IMPORT_MODES_TO_IMPORT_CONFIGS[args.import_mode]

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
