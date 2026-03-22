#!/bin/bash
set -e

# --- 1. Configuration ---
PYTHON_VER="${1:-3.11}"
export UV_PYTHON="$PYTHON_VER"

PROJECT_ROOT=$(pwd)
rm -rf .venv uv.lock
BIN_PATH="$PROJECT_ROOT/bin/linux_x64"
OPENCV_WRAPPER="$PROJECT_ROOT/vendored/opencv-python"

# High-level build directory
BUILD_DIR="$PROJECT_ROOT/build/opencv_python_cp${PYTHON_VER//./}"
WHEEL_FINAL_DIR="$PROJECT_ROOT/wheels"

# --- 2. Submodule & Environment ---
if [ ! -d "$OPENCV_WRAPPER/opencv" ]; then
    git submodule update --init --recursive --depth 1
fi

echo "Setting up build environment for Python $PYTHON_VER..."
uv sync --only-group build-opencv --no-install-project
source .venv/bin/activate

# --- 3. Path Extraction & Dependencies ---
PYTHON_EXE=$(which python)
PYTHON_INC=$(python -c "import sysconfig; print(sysconfig.get_path('include'))")
PYTHON_LIB_DIR=$(python -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))")
PYTHON_LIB_NAME=$(python -c "import sysconfig; print(sysconfig.get_config_var('LDLIBRARY'))")

# Ensure base tools are present for the backend hooks
for dep in "pip" "numpy" "setuptools" "wheel"; do
    uv pip install "$dep" --quiet
done

PYTHON_NUMPY_INC=$(python -c "import numpy; print(numpy.get_include())")
# --- 4. Official Build Execution ---
echo "Moving to official wrapper directory..."
cd "$OPENCV_WRAPPER"

# 1. Deep clean to remove any Python 3.11 artifacts or __pycache__
echo "Performing deep clean of wrapper metadata..."
rm -rf dist build *.egg-info .eggs _skbuild
find . -name "__pycache__" -type d -exec rm -rf {} +

# 2. Redirect scikit-build output
export SKBUILD_BUILD_DIR="$BUILD_DIR"

# 3. CRITICAL: Identify the backend location
# In opencv-python, the 'backend' module is usually inside '_build_backend'
BACKEND_PATH="$OPENCV_WRAPPER/_build_backend"

if [ ! -d "$BACKEND_PATH" ]; then
    echo "ERROR: Could not find build backend at $BACKEND_PATH"
    exit 1
fi

# 4. Inject the backend path into PYTHONPATH
# We add both the wrapper root AND the backend folder
export PYTHONPATH="${OPENCV_WRAPPER}:${BACKEND_PATH}:${PYTHONPATH}"

# 5. Pass custom CMake logic
export CMAKE_ARGS="\
  -D PYTHON3_EXECUTABLE=$PYTHON_EXE \
  -D PYTHON3_INCLUDE_DIR=$PYTHON_INC \
  -D PYTHON3_LIBRARY=$PYTHON_LIB_DIR/$PYTHON_LIB_NAME \
  -D PYTHON3_NUMPY_INCLUDE_DIRS=$PYTHON_NUMPY_INC \
  -D WITH_GSTREAMER=ON \
  -D GSTREAMER_1_0_INCLUDE_DIR=/usr/include/gstreamer-1.0 \
  -D GSTREAMER_1_0_LIBRARIES=$BIN_PATH/libgstreamer-1.0.so \
  -D BUILD_opencv_gapi=ON \
  -D BUILD_opencv_python3=ON \
  -D INSTALL_PYTHON_EXAMPLES=OFF \
  -D BUILD_EXAMPLES=OFF \
  -D BUILD_TESTS=OFF \
  -D BUILD_PERF_TESTS=OFF \
  -D CMAKE_BUILD_TYPE=Release"

echo "Launching build for Python $PYTHON_VER (using local backend at $BACKEND_PATH)..."
# Using --no-isolation to leverage the 'uv' group deps you synced earlier
python -m build --wheel --no-isolation --outdir dist .

# --- 5. Exporting the Artifact ---
mkdir -p "$WHEEL_FINAL_DIR"

GENERATED_WHEEL=$(ls dist/*.whl | head -n 1)
WHEEL_FILENAME=$(basename "$GENERATED_WHEEL")

echo "------------------------------------------------"
echo "Build Successful: $WHEEL_FILENAME"
echo "------------------------------------------------"

cp "$GENERATED_WHEEL" "$WHEEL_FINAL_DIR/"

cd "$PROJECT_ROOT"
rm -rf .venv uv.lock
uv sync