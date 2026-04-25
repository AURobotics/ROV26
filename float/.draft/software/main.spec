# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # We removed 'unittest' from excludes to fix your crash
    excludes=[
        'matplotlib.tests', 
        'matplotlib.sample_data',
        'matplotlib.backends.backend_tkagg', 
        'numpy.distutils', 
        'tkinter',
        'PySide6.QtDesigner',
        'PySide6.QtNetwork',
        'PySide6.QtBluetooth',
        'PySide6.QtNfc',
        'PySide6.QtWebEngine',
        'PySide6.QtPdf',
        'PySide6.QtQuick',
        'IPython',
        'jedi'
    ],
    noarchive=False,
    optimize=2, # Enable bytecode optimization
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True, # Strips symbols to reduce size
    upx=True,   # Uses UPX compression if you have it installed
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)