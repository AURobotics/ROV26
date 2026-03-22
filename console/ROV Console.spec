# -*- mode: python ; coding: utf-8 -*-
import os
import glob

spec_root = os.path.abspath(os.curdir)
linux_bin_path = os.path.join(spec_root, 'bin', 'linux_x64')

# Helper to collect all .so files from a directory into a specific bundle destination
def collect_libs(source_dir, dest_bundle_dir):
    libs = []
    # Find all .so files including versioned ones (e.g., .so.0.2402.0)
    for f in glob.glob(os.path.join(source_dir, '*.so*')):
        if os.path.isfile(f):
            libs.append((f, dest_bundle_dir))
    return libs

# Define our binary mapping
# 1. Core GStreamer/GLib libs -> bin/linux_x64/
# 2. Plugins -> bin/linux_x64/gstreamer-1.0/
# 3. Helpers -> bin/linux_x64/helpers/
my_binaries = []
my_binaries += collect_libs(linux_bin_path, 'bin/linux_x64')
my_binaries += collect_libs(os.path.join(linux_bin_path, 'gstreamer-1.0'), 'bin/linux_x64/gstreamer-1.0')

# Explicitly add the scanner (it's an executable, not a .so)
scanner_path = os.path.join(linux_bin_path, 'helpers', 'gst-plugin-scanner')
if os.path.exists(scanner_path):
    my_binaries.append((scanner_path, 'bin/linux_x64/helpers'))

a = Analysis(
    ['src/console/__main__.py'],
    pathex=[spec_root],
    binaries=my_binaries,
    datas=[
        ('src/console/assets', 'console/assets'),
    ],
    hiddenimports=['cv2', 'numpy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ROV-Console',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False, # Keeping UPX False as requested for Fedora/Qt stability
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='ROV-Console' 
)