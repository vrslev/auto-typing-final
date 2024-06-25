default: install lint check-types test

install:
    uv lock
    uv sync

test *args:
    @uv run -q pytest -- {{ args }}

lint:
    uv -q run ruff check .
    uv -q run ruff format .

check-types:
    uv -q run mypy .

publish:
    rm -rf dist/*
    uv tool run --from build python -- -m build --installer uv
    # https://github.com/pypa/twine/issues/977
    uv tool run --with=importlib-metadata==7.* twine check dist/*
    uv tool run --with=importlib-metadata==7.* twine upload dist/* --username __token__ --password $PYPI_TOKEN

run *args:
    @.venv/bin/auto-typing-final {{ args }}
