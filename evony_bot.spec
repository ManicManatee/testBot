# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec (compatible with PyInstaller 6+)
# Produces four executables in dist/evony_bot/:
#
#   EvonyBot.exe            — GUI manager  (users double-click this)
#   evony_bot.exe           — headless CLI bot
#   capture_templates.exe   — one-time template capture wizard
#   deploy.exe              — auto-installs adb + Tesseract (GUI Setup tab runs this)
#
# Build:  python build.py
#     or: pyinstaller evony_bot.spec --noconfirm

from PyInstaller.utils.hooks import collect_data_files

# CustomTkinter ships theme / asset JSON files that must travel with the exe.
_ctk_datas = collect_data_files("customtkinter", include_py_files=False)

_shared_datas = [
    ("config.yaml", "."),          # default config placed next to the exe
    ("config.example.yaml", "."),  # pristine defaults (deploy.py scaffolds from this)
    ("templates",   "templates"),  # empty subdirs; user fills these in
] + _ctk_datas

_hidden = [
    # OpenCV
    "cv2", "cv2.cv2",
    # Pillow image plugins
    "PIL.Image", "PIL.ImageOps",
    "PIL.BmpImagePlugin", "PIL.JpegImagePlugin", "PIL.PngImagePlugin",
    # Other runtime deps
    "pytesseract",
    "yaml",
    "numpy", "numpy.core._methods", "numpy.lib.format",
    # GUI
    "customtkinter",
]

_no_gui_excludes = ["tkinter", "matplotlib", "scipy", "pandas"]
_gui_excludes    = [           "matplotlib", "scipy", "pandas"]

# ── 1.  GUI Manager ───────────────────────────────────────────────────────────

gui = Analysis(
    ["gui.py"],
    datas=_shared_datas,
    hiddenimports=_hidden,
    excludes=_gui_excludes,
)
pyz_gui = PYZ(gui.pure)
exe_gui = EXE(
    pyz_gui, gui.scripts, [],
    exclude_binaries=True,
    name="EvonyBot",
    console=False,   # No black terminal window for the GUI
    upx=True,
    debug=False,
    strip=False,
    icon=None,
)

# ── 2.  Headless CLI bot ──────────────────────────────────────────────────────

cli = Analysis(
    ["main.py"],
    datas=_shared_datas,
    hiddenimports=_hidden,
    excludes=_no_gui_excludes,
)
pyz_cli = PYZ(cli.pure)
exe_cli = EXE(
    pyz_cli, cli.scripts, [],
    exclude_binaries=True,
    name="evony_bot",
    console=True,
    upx=True,
    debug=False,
    strip=False,
    icon=None,
)

# ── 3.  Template capture wizard ───────────────────────────────────────────────

cap = Analysis(
    ["capture_templates.py"],
    datas=_shared_datas,
    hiddenimports=_hidden,
    excludes=_no_gui_excludes,
)
pyz_cap = PYZ(cap.pure)
exe_cap = EXE(
    pyz_cap, cap.scripts, [],
    exclude_binaries=True,
    name="capture_templates",
    console=True,
    upx=True,
    debug=False,
    strip=False,
    icon=None,
)

# ── 4.  Auto-deploy tool (installs adb + Tesseract into tools/) ──────────────
# The GUI's Setup tab launches this as deploy.exe when frozen; deploy.py
# itself skips the pip step in frozen mode since packages are bundled.

dep = Analysis(
    ["deploy.py"],
    datas=_shared_datas,
    hiddenimports=_hidden,
    excludes=_no_gui_excludes,
)
pyz_dep = PYZ(dep.pure)
exe_dep = EXE(
    pyz_dep, dep.scripts, [],
    exclude_binaries=True,
    name="deploy",
    console=True,
    upx=True,
    debug=False,
    strip=False,
    icon=None,
)

# ── Combined output directory ─────────────────────────────────────────────────
# All four exes share dist/evony_bot/ — PyInstaller deduplicates shared DLLs.

COLLECT(
    exe_gui,  gui.binaries,  gui.zipfiles,  gui.datas,
    exe_cli,  cli.binaries,  cli.zipfiles,  cli.datas,
    exe_cap,  cap.binaries,  cap.zipfiles,  cap.datas,
    exe_dep,  dep.binaries,  dep.zipfiles,  dep.datas,
    name="evony_bot",
    upx=True,
    strip=False,
)
