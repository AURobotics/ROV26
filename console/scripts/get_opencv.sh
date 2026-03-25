#!/bin/bash
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJECT_ROOT"

rm -rf .venv uv.lock
uv run --no-project --with packaging scripts/get_opencv.py
uv sync