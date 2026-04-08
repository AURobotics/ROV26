#!/bin/bash
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJECT_ROOT"

rm -rf .venv uv.lock
uv venv --seed --system-site-packages --python /usr/bin/python3
if [ -n $VIRTUALIZED_UDEV ]; then
    echo "export VIRTUALIZED_UDEV=1" >> .venv/bin/activate
fi
uv sync