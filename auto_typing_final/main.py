import argparse
from typing import TextIO, cast

from auto_typing_final.transform import transform_file_content


def main() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=argparse.FileType("r+"), nargs="*")

    for file in cast(list[TextIO], parser.parse_args().files):
        data = file.read()
        file.seek(0)
        file.write(transform_file_content(data))
        file.truncate()


if __name__ == "__main__":  # pragma: no cover
    main()
