import argparse
import sys
from difflib import ndiff
from typing import TextIO, cast

from auto_typing_final.transform import transform_file_content


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=argparse.FileType("r+"), nargs="*")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    has_changes = False

    for file in cast(list[TextIO], args.files):
        data = file.read()
        transformed_content = transform_file_content(data)

        if args.check:
            sys.stdout.writelines(ndiff(data.splitlines(keepends=True), transformed_content.splitlines(keepends=True)))
        else:
            file.seek(0)
            file.write(transformed_content)
            file.truncate()

        if data != transformed_content:
            has_changes = True

    return has_changes
