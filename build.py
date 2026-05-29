#!/usr/bin/env python3
"""
Build script for Evony Bot.

Steps:
  1. Installs PyInstaller if missing.
  2. Runs PyInstaller with evony_bot.spec → dist/evony_bot/
  3. (Optional) Runs Inno Setup → installer/output/EvonyBot_Setup_v1.0.0.exe

Usage:
    python build.py                # exe only
    python build.py --installer    # exe + Windows installer
    python build.py --clean        # remove build/dist artifacts only
"""

import argparse
import shutil
import subprocess
import sys
import os
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd: list[str], **kwargs) -> None:
    print(f"\n>>> {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not found — installing…")
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])


def clean() -> None:
    for d in ["build", "dist"]:
        p = Path(d)
        if p.exists():
            shutil.rmtree(p)
            print(f"Removed {d}/")
    pyc = Path("__pycache__")
    if pyc.exists():
        shutil.rmtree(pyc)


def find_iscc() -> Path | None:
    """Locate the Inno Setup compiler (ISCC.exe) on this machine."""
    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
    ]
    for p in candidates:
        if p.exists():
            return p
    # Also try PATH
    found = shutil.which("ISCC")
    return Path(found) if found else None


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Build Evony Bot")
    parser.add_argument("--installer", action="store_true",
                        help="Package the exe into a Windows installer via Inno Setup")
    parser.add_argument("--clean", action="store_true",
                        help="Remove build artifacts and exit")
    args = parser.parse_args()

    if args.clean:
        clean()
        print("Clean done.")
        return

    # ── Step 1: clean previous build ──────────────────────────────────────
    clean()

    # ── Step 2: build exe ─────────────────────────────────────────────────
    ensure_pyinstaller()

    spec = Path("evony_bot.spec")
    if not spec.exists():
        sys.exit("ERROR: evony_bot.spec not found. Run from the repo root.")

    run([sys.executable, "-m", "PyInstaller", str(spec), "--noconfirm"])

    exe_path = Path("dist") / "evony_bot" / "evony_bot.exe"
    if not exe_path.exists():
        sys.exit("ERROR: PyInstaller finished but exe not found — check output above.")

    dist = exe_path.parent
    print(f"\n✓  GUI launcher:       {dist / 'EvonyBot.exe'}")
    print(f"   CLI bot:            {exe_path}")
    print(f"   Capture-templates:  {dist / 'capture_templates.exe'}")
    print(f"\n   → Double-click EvonyBot.exe to open the management GUI.")

    # ── Step 3: installer (optional) ──────────────────────────────────────
    if not args.installer:
        print("\nSkipping installer (pass --installer to build one).")
        return

    iscc = find_iscc()
    if not iscc:
        print(
            "\nInno Setup not found on this machine.\n"
            "Download from: https://jrsoftware.org/isinfo.php\n"
            "Install it, then re-run:  python build.py --installer"
        )
        sys.exit(1)

    iss_script = Path("installer") / "setup.iss"
    if not iss_script.exists():
        sys.exit(f"ERROR: {iss_script} not found.")

    Path("installer/output").mkdir(parents=True, exist_ok=True)
    run([str(iscc), str(iss_script)])

    # Filename may include a version stamp — find whatever was produced
    outputs = list(Path("installer/output").glob("EvonyBot_Setup_*.exe"))
    installer_out = outputs[0] if outputs else Path("installer/output/EvonyBot_Setup.exe")
    print(f"\n✓  Installer:  {installer_out}")
    print(
        "\nDistribute that single .exe file.\n"
        "Recipients must also install:\n"
        "  • Android Platform Tools (adb.exe in PATH)\n"
        "  • Tesseract OCR  https://github.com/UB-Mannheim/tesseract/wiki"
    )


if __name__ == "__main__":
    main()
