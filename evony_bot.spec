# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec — builds two console executables:
#   dist/evony_bot/evony_bot.exe          (the main bot)
#   dist/evony_bot/capture_templates.exe  (one-time template capture tool)
#
# Build with:  python build.py
#          or: pyinstaller evony_bot.spec

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

# ── Shared analysis settings ───────────────────────────────────────────────

_hidden = [
    # OpenCV needs these on some systems
    "cv2",
    "cv2.cv2",
    # Pillow imaging formats
    "PIL.Image",
    "PIL.ImageOps",
    "PIL.BmpImagePlugin",
    "PIL.JpegImagePlugin",
    "PIL.PngImagePlugin",
    # pytesseract
    "pytesseract",
    # PyYAML
    "yaml",
    # numpy
    "numpy",
    "numpy.core._methods",
    "numpy.lib.format",
]

_datas = [
    ("config.yaml",  "."),          # default config next to exe
    ("templates",    "templates"),  # empty template dirs (user fills these in)
]

# ── Main bot ──────────────────────────────────────────────────────────────

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe_main = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="evony_bot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # keep console visible so log output is readable
    icon=None,
)

# ── Template capture tool ─────────────────────────────────────────────────

b = Analysis(
    ["capture_templates.py"],
    pathex=[],
    binaries=[],
    datas=_datas,
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz_b = PYZ(b.pure, b.zipped_data, cipher=block_cipher)

exe_capture = EXE(
    pyz_b,
    b.scripts,
    [],
    exclude_binaries=True,
    name="capture_templates",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

# ── Combined output directory ─────────────────────────────────────────────
# Both exes share the same dist/evony_bot/ folder so they share DLLs
# and the config / templates directories.

coll = COLLECT(
    exe_main,
    a.binaries,
    a.zipfiles,
    a.datas,
    exe_capture,
    b.binaries,
    b.zipfiles,
    b.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="evony_bot",
)
