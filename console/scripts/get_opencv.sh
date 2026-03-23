#!/bin/bash
REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../.." && pwd )"
cd "$REPO_ROOT"

echo "Checking for opencv-build branch..."
git fetch origin opencv-build:opencv-build --quiet 2>/dev/null || git fetch origin opencv-build --quiet

echo "Fetching LFS binaries..."
git lfs fetch origin opencv-build --include="console/bin/linux_x64/*,console/wheels/*" --exclude="*"

mkdir -p console/.tmp
git archive opencv-build console/bin/linux_x64 console/wheels -o console/.tmp/opencv.tar

if [ -f console/.tmp/opencv.tar ]; then
    tar -xf console/.tmp/opencv.tar -C ./
    rm -rf console/.tmp/
    echo "Done! OpenCV binaries and wheels are now in console/"
else
    echo "Error: Archive failed. Check if 'console/bin' exists in the 'opencv-build' branch."
fi