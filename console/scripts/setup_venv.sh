#!/bin/bash
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJECT_ROOT"

rm -rf .venv uv.lock
uv venv --seed --system-site-packages --python /usr/bin/python3
if [ -n $VIRTUALIZED_UDEV ]; then
    echo "export VIRTUALIZED_UDEV=1" >> .venv/bin/activate
fi
uv sync
MAJOR=$(uv run python -c "import sys; sys.stdout.write(f'{sys.version_info.major}')")
MINOR=$(uv run python -c "import sys; sys.stdout.write(f'{sys.version_info.minor}')")
rm -rf ./.venv/lib/python$MAJOR.$MINOR/site-packages/cv2
ln -s /usr/lib/python3/dist-packages/cv2.cpython-$MAJOR$MINOR.*.so .venv/lib/python$MAJOR.$MINOR/site-packages/cv2.so