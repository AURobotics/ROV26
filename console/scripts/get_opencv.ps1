$RepoRoot = Resolve-Path "$PSScriptRoot/../.."
Set-Location $RepoRoot

Write-Host "Checking for opencv-build branch..." -ForegroundColor Cyan
git fetch origin opencv-build:opencv-build --quiet 2>$null

Write-Host "Fetching LFS binaries..." -ForegroundColor Cyan
git lfs fetch origin opencv-build --include="console/bin/*" --exclude="*"

$TempDir = "console/.tmp"
if (-not (Test-Path $TempDir)) { New-Item -ItemType Directory -Path $TempDir }

$ArchivePath = "$TempDir/opencv.tar"
Write-Host "Archiving from opencv-build..." -ForegroundColor Cyan
git archive opencv-build console/bin -o $ArchivePath

if (Test-Path $ArchivePath) {
    tar.exe -xf $ArchivePath -C ./
    Remove-Item -Recurse -Force $TempDir
    Write-Host "Done! OpenCV-GStreamer binaries and are now in console/" -ForegroundColor Green
} else {
    Write-Warning "Error: Archive failed. Check if 'console/bin' exists in the 'opencv-build' branch."
}