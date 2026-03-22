#!/bin/bash
set -e
# --- 1. Install System Dependencies ---
sudo apt update
sudo apt install -y gcc g++ cmake build-essential git pkg-config \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav gstreamer1.0-vaapi gstreamer1.0-tools \
    libgstreamer1.0-dev libglib2.0-0 patchelf libgtk2.0-dev libgstreamer-plugins-base1.0-dev

# --- 2. Configuration ---
PROJECT_ROOT="$(pwd)"
DEST_ROOT="$PROJECT_ROOT/bin/linux_x64"
SYS_LIB="/usr/lib/x86_64-linux-gnu"
SYS_GST_PLUGINS="$SYS_LIB/gstreamer-1.0"

# Create directory tree
mkdir -p "$DEST_ROOT/gstreamer-1.0"
mkdir -p "$DEST_ROOT/helpers"

echo "--- Stage 1: Collecting Core Libraries ---"
# Base names of the required libraries
CORE_LIBS=(
    "libglib-2.0" "libgobject-2.0" "libgmodule-2.0" "libgio-2.0"
    "libgstreamer-1.0" "libgstbase-1.0" "libgstapp-1.0" "libgstaudio-1.0"
    "libgstvideo-1.0" "libgstpbutils-1.0" "libgsttag-1.0" "libgstnet-1.0"
    "libgstcontroller-1.0" "libgstfft-1.0" "libgstgl-1.0" "libgstallocators-1.0"
    "libgstrtp-1.0" "libgstsdp-1.0" "libgstrtsp-1.0" "libgstcheck-1.0"
    "libgstcodecparsers-1.0" "libgstcodecs-1.0" "libgstriff-1.0"
    "libgstadaptivedemux-1.0" "libgstinsertbin-1.0" "libgstisoff-1.0"
    "libgstmpegts-1.0" "libgstphotography-1.0" "libgstplay-1.0" 
    "libgstplayer-1.0" "libgstsctp-1.0" "libgsttranscoder-1.0"
    "libgsturidownloader-1.0" "libgstva-1.0" "libgstvulkan-1.0"
    "libgstwayland-1.0" "libgstwebrtc-1.0" "libgstwebrtcnice-1.0"
)

for lib in "${CORE_LIBS[@]}"; do
    # Search for the library in the standard Debian x86_64 path
    # We grab the .so.0 (link) and the actual versioned binary
    FILES=$(find "$SYS_LIB" -maxdepth 1 -name "$lib.so.0*" 2>/dev/null)
    if [ -n "$FILES" ]; then
        cp -P $FILES "$DEST_ROOT/"
    else
        echo "Skipped $lib (not found in $SYS_LIB)"
    fi
done

echo "--- Stage 2: Collecting Plugins ---"
PLUGINS=(
    "libgstlibav.so" "libgstrtp.so" "libgstudp.so" "libgstapp.so"
    "libgstplayback.so" "libgstsdpelem.so" "libgstcoreelements.so"
    "libgstrtpmanager.so" "libgsttypefindfunctions.so" 
    "libgstvideoconvertscale.so" "libgstvideoparsersbad.so"
    "libgstisomp4.so" "libgstvpx.so" "libgstx264.so"
)

for plugin in "${PLUGINS[@]}"; do
    if [ -f "$SYS_GST_PLUGINS/$plugin" ]; then
        cp "$SYS_GST_PLUGINS/$plugin" "$DEST_ROOT/gstreamer-1.0/"
    else
        echo "Warning: Plugin $plugin not found"
    fi
done

echo "--- Stage 3: Collecting the Helper (Surgical Search) ---"
# Debian 1.0 specific paths for the scanner
SCANNER_SEARCH_PATHS=(
    "/usr/lib/x86_64-linux-gnu/gstreamer1.0/gstreamer-1.0/gst-plugin-scanner"
    "/usr/libexec/gstreamer-1.0/gst-plugin-scanner"
    "/usr/lib/gstreamer-1.0/gst-plugin-scanner"
)

FOUND=false
for path in "${SCANNER_SEARCH_PATHS[@]}"; do
    if [ -f "$path" ]; then
        echo "Found scanner at $path"
        cp "$path" "$DEST_ROOT/helpers/gst-plugin-scanner"
        FOUND=true
        break
    fi
done

if [ "$FOUND" = false ]; then
    echo "Attempting global find for scanner..."
    GLOBAL_SCANNER=$(find /usr/lib -name gst-plugin-scanner | head -n 1)
    if [ -n "$GLOBAL_SCANNER" ]; then
        cp "$GLOBAL_SCANNER" "$DEST_ROOT/helpers/gst-plugin-scanner"
    else
        echo "ERROR: gst-plugin-scanner not found. Is gstreamer1.0-plugins-base installed?"
        exit 1
    fi
fi

echo "--- Stage 4: Patching RPATHs for Portability ---"
# Fix Core Libs
cd "$DEST_ROOT"
for f in *.so*; do
    if [ -f "$f" ] && [ ! -L "$f" ]; then
        patchelf --set-rpath '$ORIGIN' "$f"
    fi
done

# Fix Plugins
cd "$DEST_ROOT/gstreamer-1.0"
for f in *.so; do
    if [ -f "$f" ]; then
        patchelf --set-rpath '$ORIGIN/..' "$f"
    fi
done

# Fix Scanner
cd "$DEST_ROOT/helpers"
chmod +x gst-plugin-scanner
patchelf --set-rpath '$ORIGIN/..' gst-plugin-scanner

echo "------------------------------------------------"
echo "Done! Portable structure created in: $DEST_ROOT"
echo "------------------------------------------------"