$PROJECT_ROOT = Resolve-Path "$PSScriptRoot/.."
Set-Location $PROJECT_ROOT

Remove-Item -Recurse -Force .venv
Remove-Item uv.lock
uv run --no-project --with packaging scripts/get_opencv.py
uv sync