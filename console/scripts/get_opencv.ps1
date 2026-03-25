$PROJECT_ROOT = Resolve-Path "$PSScriptRoot/.."
Set-Location $PROJECT_ROOT

uv run --no-project --with packaging scripts/get_opencv.py