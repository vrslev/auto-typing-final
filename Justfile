default: install lint check-types test

install:
    uv lock
    uv sync

lint:
    uv -q run ruff check .
    uv -q run ruff format .

check-types:
    uv -q run mypy .

test *args:
    @.venv/bin/pytest -- {{ args }}

publish-package:
    rm -rf dist/*
    uv tool run --from build python -m build --installer uv
    uv tool run twine check dist/*
    uv tool run twine upload dist/* --username __token__ --password $PYPI_TOKEN

run *args:
    @.venv/bin/auto-typing-final {{ args }}

extension: install-ts check-types-ts lint-ts

install-ts:
    npm ci

check-types-ts:
    npm run compile

lint-ts:
    npm run lint
