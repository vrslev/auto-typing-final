default: install lint check-types test
extension: install-ts check-types-ts lint-ts

run *args:
    uv run auto-typing-final {{ args }}

install:
    uv lock
    uv sync

lint:
    uv run ruff check
    uv run auto-typing-final --import-style final
    uv run ruff format

check-types:
    uv run mypy .

test *args:
    uv run pytest {{ args }}

publish-package:
    rm -rf dist
    uv build
    uv publish --token $PYPI_TOKEN

install-ts:
    npm ci

check-types-ts:
    npm run compile

lint-ts:
    npm run lint
