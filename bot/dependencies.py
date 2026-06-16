"""
Dependency resolution and configuration for Evony Bot.

This module is the single source of truth for where the bot's external tools
live (ADB and Tesseract OCR).  It lets the rest of the codebase call
``adb_path()`` / ``tesseract_path()`` instead of assuming the tools are on the
system PATH, and ``configure()`` wires everything up at process start so the
bot "just works" after ``deploy.py`` has run.

Resolution order for each tool:
  1. Path recorded in tools/tools.json  (written by deploy.py)
  2. Bundled copy inside the local tools/ directory
  3. An executable on the system PATH
  4. Well-known install locations (Windows)

Nothing here downloads anything — see deploy.py for the installer.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform.startswith("win")
_EXE = ".exe" if _IS_WINDOWS else ""


# ── Locations ───────────────────────────────────────────────────────────────

def tools_dir() -> Path:
    """Directory that holds bundled tools and tools.json.

    Override with the EVONY_TOOLS_DIR environment variable.  Defaults to a
    ``tools/`` folder next to the working directory (which main.py/gui.py pin
    to the executable's location when frozen).
    """
    override = os.environ.get("EVONY_TOOLS_DIR")
    return Path(override).expanduser().resolve() if override else Path("tools").resolve()


def _manifest_path() -> Path:
    return tools_dir() / "tools.json"


def load_manifest() -> dict:
    try:
        with open(_manifest_path(), "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_manifest(data: dict) -> None:
    tools_dir().mkdir(parents=True, exist_ok=True)
    with open(_manifest_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── Tool resolution ──────────────────────────────────────────────────────────

def _valid(path: Optional[str]) -> Optional[str]:
    return path if path and Path(path).exists() else None


def adb_path() -> str:
    """Resolve the adb executable, falling back to the bare command name."""
    manifest = load_manifest()
    found = _valid(manifest.get("adb"))
    if found:
        return found

    bundled = tools_dir() / "platform-tools" / f"adb{_EXE}"
    if bundled.exists():
        return str(bundled)

    on_path = shutil.which("adb")
    if on_path:
        return on_path

    # Last resort: well-known spots, else the bare name (errors handled by caller)
    for guess in _adb_well_known():
        if guess.exists():
            return str(guess)
    return "adb"


def tesseract_path() -> Optional[str]:
    """Resolve the tesseract executable, or None if not installed."""
    manifest = load_manifest()
    found = _valid(manifest.get("tesseract"))
    if found:
        return found

    bundled = tools_dir() / "Tesseract-OCR" / f"tesseract{_EXE}"
    if bundled.exists():
        return str(bundled)

    on_path = shutil.which("tesseract")
    if on_path:
        return on_path

    for guess in _tesseract_well_known():
        if guess.exists():
            return str(guess)
    return None


def _adb_well_known() -> list[Path]:
    spots: list[Path] = []
    if _IS_WINDOWS:
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            spots.append(Path(local) / "Android" / "Sdk" / "platform-tools" / "adb.exe")
        spots.append(Path(r"C:\platform-tools\adb.exe"))
    else:
        spots += [Path("/usr/bin/adb"), Path("/usr/local/bin/adb")]
    return spots


def _tesseract_well_known() -> list[Path]:
    spots: list[Path] = []
    if _IS_WINDOWS:
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
            spots.append(Path(base) / "Tesseract-OCR" / "tesseract.exe")
    else:
        spots += [Path("/usr/bin/tesseract"), Path("/usr/local/bin/tesseract"),
                  Path("/opt/homebrew/bin/tesseract")]
    return spots


# ── Configuration (called at process start) ──────────────────────────────────

def configure() -> dict:
    """
    Point the running process at the resolved tools.

    - Prepends the bundled tool directories to PATH so bare ``adb`` and any
      subprocess lookups resolve to our copies.
    - Sets pytesseract's tesseract_cmd so OCR works without manual config.

    Returns a small dict describing what was wired up (handy for logging).
    """
    wired = {"adb": None, "tesseract": None}

    adb = adb_path()
    wired["adb"] = adb
    adb_dir = str(Path(adb).parent)
    if Path(adb).exists() and adb_dir not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = adb_dir + os.pathsep + os.environ.get("PATH", "")

    tess = tesseract_path()
    wired["tesseract"] = tess
    if tess:
        tess_dir = str(Path(tess).parent)
        if tess_dir not in os.environ.get("PATH", "").split(os.pathsep):
            os.environ["PATH"] = tess_dir + os.pathsep + os.environ.get("PATH", "")
        try:
            import pytesseract  # noqa: WPS433 (runtime optional import)
            pytesseract.pytesseract.tesseract_cmd = tess
        except ImportError:
            logger.debug("pytesseract not installed yet — skipping OCR wiring")

    logger.debug("Dependencies configured: %s", wired)
    return wired


# ── Status reporting (used by deploy.py --check and the GUI) ──────────────────

# Python packages the bot needs at runtime, mapped to their import names
RUNTIME_PACKAGES = {
    "opencv-python": "cv2",
    "Pillow": "PIL",
    "numpy": "numpy",
    "PyYAML": "yaml",
    "pytesseract": "pytesseract",
    "customtkinter": "customtkinter",
}


def python_package_status() -> dict[str, bool]:
    import importlib.util
    return {
        pkg: importlib.util.find_spec(mod) is not None
        for pkg, mod in RUNTIME_PACKAGES.items()
    }


def adb_status() -> tuple[bool, str]:
    adb = adb_path()
    try:
        r = subprocess.run([adb, "version"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            first = (r.stdout.strip().splitlines() or ["adb"])[0]
            return True, f"{first}  ({adb})"
        return False, f"adb exited {r.returncode}"
    except FileNotFoundError:
        return False, "adb not found"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def tesseract_status() -> tuple[bool, str]:
    tess = tesseract_path()
    if not tess:
        return False, "tesseract not found"
    try:
        r = subprocess.run([tess, "--version"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            first = (r.stdout.strip().splitlines() or ["tesseract"])[0]
            return True, f"{first}  ({tess})"
        return False, f"tesseract exited {r.returncode}"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def full_status() -> dict:
    """Structured status of every requirement, for the GUI Setup tab."""
    pkgs = python_package_status()
    adb_ok, adb_detail = adb_status()
    tess_ok, tess_detail = tesseract_status()
    return {
        "packages": pkgs,
        "packages_ok": all(pkgs.values()),
        "adb": {"ok": adb_ok, "detail": adb_detail},
        "tesseract": {"ok": tess_ok, "detail": tess_detail},
        "all_ok": all(pkgs.values()) and adb_ok and tess_ok,
    }
