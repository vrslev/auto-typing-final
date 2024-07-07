import argparse
import sys
from collections.abc import Iterable
from difflib import unified_diff
from pathlib import Path

from ast_grep_py import Edit, SgRoot

from auto_typing_final.finder import should_add_from_typing_import_final, should_add_import_typing
from auto_typing_final.transform import AddFinal, ImportMode, make_operations_from_root


def transform_file_content(source: str, import_mode: ImportMode) -> str:
    root = SgRoot(source, "python").root()
    edits: list[Edit] = []
    has_added_final = False

    for applied_operation in make_operations_from_root(root, import_mode):
        if isinstance(applied_operation.operation, AddFinal) and applied_operation.edits:
            has_added_final = True

        edits.extend(edit.edit for edit in applied_operation.edits)

    result = root.commit_edits(edits)

    if has_added_final:
        if import_mode == ImportMode.typing_final and should_add_import_typing(root):
            return root.commit_edits([root.replace(f"import typing\n{result}")])
        if import_mode == ImportMode.final and should_add_from_typing_import_final(root):
            return root.commit_edits([root.replace(f"from typing import Final\n{result}")])

    return result


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

    has_changes = False

    for path in find_all_source_files(args.files):
        with path.open("r+") as file:
            source = file.read()
            transformed_content = transform_file_content(source=source, import_mode=args.import_mode)
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
