# -*- mode: python ; coding: utf-8 -*-

import cv2
import os
from pathlib import Path
cv2_path = Path(cv2.__file__).parent

a = Analysis(
    ['src/console/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('src/console/assets', 'console/assets'),
    (str(cv2_path / "bin/linux"), "cv2/bin/linux")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ROV Console',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ROV Console',
)