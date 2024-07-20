default: install lint check-types test
extension: install-ts check-types-ts lint-ts

run *args:
    uv run -q --frozen auto-typing-final {{ args }}

install:
    uv lock
    uv sync

lint:
    uv run -q --frozen ruff check .
    uv run -q --frozen ruff format .

check-types:
    uv run -q --frozen mypy .

test *args:
    uv run -q --frozen pytest {{ args }}

publish-package:
    rm -rf dist/*
    uv tool run --from build python -m build --installer uv
    uv tool run twine check dist/*
    uv tool run twine upload dist/* --username __token__ --password $PYPI_TOKEN


install-ts:
    npm ci

check-types-ts:
    npm run compile

lint-ts:
    npm run lint
