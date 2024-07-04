#!/bin/sh

set -eu

for cmd in brew apt dnf choco; do
    if command -v "$cmd" > /dev/null; then
        PACAKGE_MANAGER=$cmd
        break
    fi
done

_require() {
    if ! command -v "$@" > /dev/null; then
        "$PACAKGE_MANAGER" install -y "$@"
    fi
}

export PIPENV_VENV_IN_PROJECT=1
if [ ! -d .venv ]; then
    pipenv install
fi

pipenv run python3 ./src/main.py