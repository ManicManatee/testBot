#!/usr/bin/env python3
"""
Evony Bot — Automated Deployment

One command that gets the bot ready to run, with no manual downloads:

    python deploy.py

It will:
  1. Install the required Python packages (pip install -r requirements.txt)
  2. Download Android Platform Tools (adb) into ./tools/platform-tools
  3. Install Tesseract OCR into ./tools/Tesseract-OCR
        - Windows: silently runs the official UB-Mannheim installer
        - Linux/macOS: uses the system package manager (apt/dnf/brew) if adb
          or tesseract aren't already present
  4. Record the resolved tool paths in tools/tools.json so the bot finds them
  5. Create config.yaml (from defaults) and the templates/ + logs/ folders
  6. Verify every requirement and print a status report

Re-running is safe: anything already present and working is skipped.

Usage:
    python deploy.py                 # full auto-deploy
    python deploy.py --check         # report status only, install nothing
    python deploy.py --device 127.0.0.1:5555   # also set the emulator address
    python deploy.py --tools-dir D:\EvonyTools  # custom tools location
    python deploy.py --skip-tesseract / --skip-adb / --skip-pip
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import ssl
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

# When running as a PyInstaller-frozen exe, resolve everything relative to the
# executable's folder (Python packages are already bundled in that case).
FROZEN = getattr(sys, "frozen", False)
if FROZEN:
    REPO_ROOT = Path(sys.executable).resolve().parent
    os.chdir(REPO_ROOT)
else:
    REPO_ROOT = Path(__file__).resolve().parent
    # Ensure we can import the bot package when run from any directory
    sys.path.insert(0, str(REPO_ROOT))

from bot import dependencies as deps  # noqa: E402

# ── Download sources ──────────────────────────────────────────────────────────

PLATFORM_TOOLS = {
    "windows": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
    "linux":   "https://dl.google.com/android/repository/platform-tools-latest-linux.zip",
    "darwin":  "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip",
}

# Official UB-Mannheim Tesseract builds (NSIS installers — support /S silent).
# A couple of versions are listed so a single dead link doesn't break setup.
TESSERACT_WIN_URLS = [
    "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe",
    "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.1.20230401.exe",
]

_DOWNLOAD_RETRIES = 4


# ── Pretty output ─────────────────────────────────────────────────────────────

def hr() -> None:
    print("─" * 64)


def step(n: int, total: int, msg: str) -> None:
    print(f"\n[{n}/{total}] {msg}")
    hr()


def ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def warn(msg: str) -> None:
    print(f"  ! {msg}")


def fail(msg: str) -> None:
    print(f"  ✗ {msg}")


# ── Download helper ─────────────────────────────────────────────────────────────

def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    ctx = ssl.create_default_context()
    for attempt in range(1, _DOWNLOAD_RETRIES + 1):
        try:
            print(f"  Downloading {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "EvonyBot-Deploy"})
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp, \
                    open(dest, "wb") as out:
                total = int(resp.headers.get("Content-Length", 0))
                read = 0
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    out.write(chunk)
                    read += len(chunk)
                    if total:
                        pct = read * 100 // total
                        print(f"\r    {pct:3d}%  ({read // 1024} KB)", end="", flush=True)
                print()
            return True
        except Exception as e:  # noqa: BLE001
            wait = 2 ** attempt
            warn(f"Attempt {attempt} failed: {e}")
            if attempt < _DOWNLOAD_RETRIES:
                print(f"    retrying in {wait}s…")
                import time
                time.sleep(wait)
    return False


# ── Steps ───────────────────────────────────────────────────────────────────

def install_pip(total: int) -> bool:
    step(1, total, "Installing Python packages")
    if FROZEN:
        # Packaged exe: all Python packages are bundled inside the executable.
        ok("Running from packaged exe — Python packages already bundled")
        return True
    req = REPO_ROOT / "requirements.txt"
    if not req.exists():
        fail("requirements.txt not found")
        return False
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req)],
            check=True,
        )
        ok("Python packages installed")
        return True
    except subprocess.CalledProcessError as e:
        fail(f"pip install failed ({e.returncode})")
        return False


def install_adb(total: int) -> bool:
    step(2, total, "Setting up Android Platform Tools (adb)")

    existing = shutil.which("adb")
    if existing:
        ok(f"adb already on PATH: {existing}")
        return True

    tools = deps.tools_dir()
    target = tools / "platform-tools" / f"adb{deps._EXE}"
    if target.exists():
        ok(f"adb already bundled: {target}")
        return True

    osname = platform.system().lower()
    key = "windows" if osname.startswith("win") else ("darwin" if osname == "darwin" else "linux")
    url = PLATFORM_TOOLS[key]

    zip_path = tools / "platform-tools.zip"
    if not download(url, zip_path):
        fail("Could not download platform-tools")
        _adb_manual_hint(key)
        return False

    print("  Extracting…")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tools)
    zip_path.unlink(missing_ok=True)

    if not target.exists():
        fail("Extraction completed but adb is missing")
        return False

    # On Unix the binary needs the executable bit
    if not deps._IS_WINDOWS:
        target.chmod(0o755)

    ok(f"adb installed: {target}")
    return True


def install_tesseract(total: int) -> bool:
    step(3, total, "Setting up Tesseract OCR")

    existing = shutil.which("tesseract") or deps.tesseract_path()
    if existing and Path(existing).exists():
        ok(f"Tesseract already available: {existing}")
        return True

    if deps._IS_WINDOWS:
        return _install_tesseract_windows()
    return _install_tesseract_unix()


def _install_tesseract_windows() -> bool:
    tools = deps.tools_dir()
    target_dir = tools / "Tesseract-OCR"
    installer = tools / "tesseract-setup.exe"

    downloaded = False
    for url in TESSERACT_WIN_URLS:
        if download(url, installer):
            downloaded = True
            break
    if not downloaded:
        fail("Could not download the Tesseract installer")
        _tesseract_manual_hint()
        return False

    # NSIS silent install: /S = silent, /D=<dir> must be LAST and UNQUOTED —
    # even when the path contains spaces.  subprocess list form would wrap a
    # space-containing /D= arg in quotes and break NSIS parsing, so on Windows
    # we build the command line as a raw string instead.
    print("  Running silent installer…")
    try:
        subprocess.run(
            f'"{installer}" /S /D={target_dir}',
            check=True, timeout=600,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        fail(f"Tesseract installer failed: {e}")
        _tesseract_manual_hint()
        return False
    finally:
        installer.unlink(missing_ok=True)

    exe = target_dir / "tesseract.exe"
    if not exe.exists():
        fail("Installer finished but tesseract.exe not found")
        return False
    ok(f"Tesseract installed: {exe}")
    return True


def _install_tesseract_unix() -> bool:
    """Use the system package manager. May prompt for sudo."""
    managers = [
        ("apt-get", ["sudo", "apt-get", "install", "-y", "tesseract-ocr"]),
        ("dnf",     ["sudo", "dnf", "install", "-y", "tesseract"]),
        ("pacman",  ["sudo", "pacman", "-S", "--noconfirm", "tesseract"]),
        ("brew",    ["brew", "install", "tesseract"]),
    ]
    for binary, cmd in managers:
        if shutil.which(binary):
            print(f"  Installing via {binary}…")
            try:
                subprocess.run(cmd, check=True)
                if shutil.which("tesseract"):
                    ok("Tesseract installed via system package manager")
                    return True
            except subprocess.CalledProcessError as e:
                warn(f"{binary} install failed: {e}")
            break
    fail("Could not auto-install Tesseract on this system")
    _tesseract_manual_hint()
    return False


def write_manifest(total: int) -> None:
    step(4, total, "Recording tool paths (tools/tools.json)")
    manifest = deps.load_manifest()
    adb = shutil.which("adb") or str(deps.tools_dir() / "platform-tools" / f"adb{deps._EXE}")
    tess = deps.tesseract_path()
    if Path(adb).exists():
        manifest["adb"] = adb
    if tess and Path(tess).exists():
        manifest["tesseract"] = tess
    deps.save_manifest(manifest)
    ok(f"Wrote {deps.tools_dir() / 'tools.json'}")
    for k, v in manifest.items():
        print(f"      {k}: {v}")


def scaffold(total: int, device: str | None) -> None:
    step(5, total, "Creating config and folders")

    for sub in ("templates/ui", "templates/shields", "templates/rally",
                "templates/monsters", "templates/resources", "templates/items", "logs"):
        (REPO_ROOT / sub).mkdir(parents=True, exist_ok=True)
    ok("templates/ and logs/ folders ready")

    cfg = REPO_ROOT / "config.yaml"
    if not cfg.exists():
        example = REPO_ROOT / "config.example.yaml"
        if example.exists():
            shutil.copy(example, cfg)
            ok("Created config.yaml from config.example.yaml")
        else:
            warn("No config.yaml and no config.example.yaml to copy from")
    else:
        ok("config.yaml already present")

    if device:
        _set_device(cfg, device)
        ok(f"Set emulator address to {device}")


def _set_device(cfg_path: Path, device: str) -> None:
    try:
        import yaml
    except ImportError:
        warn("PyYAML not available yet — skipping device write")
        return
    data = {}
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    data.setdefault("adb", {})["device"] = device
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def verify(total: int) -> bool:
    step(total, total, "Verifying installation")
    # Re-resolve now that everything is in place
    deps.configure()
    status = deps.full_status()

    print("  Python packages:")
    for pkg, present in status["packages"].items():
        (ok if present else fail)(f"  {pkg}")

    (ok if status["adb"]["ok"] else fail)(status["adb"]["detail"])
    (ok if status["tesseract"]["ok"] else fail)(status["tesseract"]["detail"])

    hr()
    if status["all_ok"]:
        print("\n  All requirements satisfied. The bot is ready to run:")
        print("    GUI :  python gui.py")
        print("    CLI :  python main.py")
    else:
        print("\n  Some requirements are still missing — see the ✗ items above.")
    return status["all_ok"]


# ── Manual hints ──────────────────────────────────────────────────────────────

def _adb_manual_hint(key: str) -> None:
    warn("Manual install: download platform-tools and add it to PATH:")
    print(f"      {PLATFORM_TOOLS[key]}")


def _tesseract_manual_hint() -> None:
    warn("Manual install:")
    if deps._IS_WINDOWS:
        print("      https://github.com/UB-Mannheim/tesseract/wiki")
    else:
        print("      Debian/Ubuntu:  sudo apt-get install tesseract-ocr")
        print("      macOS (brew) :  brew install tesseract")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-deploy Evony Bot dependencies")
    parser.add_argument("--check", action="store_true",
                        help="Report requirement status only; install nothing")
    parser.add_argument("--device", help="Emulator ADB address to write into config.yaml")
    parser.add_argument("--tools-dir", help="Where to install bundled tools (default ./tools)")
    parser.add_argument("--skip-pip", action="store_true")
    parser.add_argument("--skip-adb", action="store_true")
    parser.add_argument("--skip-tesseract", action="store_true")
    args = parser.parse_args()

    if args.tools_dir:
        os.environ["EVONY_TOOLS_DIR"] = args.tools_dir

    print("=" * 64)
    print("  Evony Bot — Automated Deployment")
    print("=" * 64)
    print(f"  Python      : {sys.version.split()[0]}")
    print(f"  Platform    : {platform.system()} {platform.release()}")
    print(f"  Tools dir   : {deps.tools_dir()}")

    if args.check:
        deps.configure()
        status = deps.full_status()
        print("\nRequirement status:")
        hr()
        for pkg, present in status["packages"].items():
            (ok if present else fail)(pkg)
        (ok if status["adb"]["ok"] else fail)(status["adb"]["detail"])
        (ok if status["tesseract"]["ok"] else fail)(status["tesseract"]["detail"])
        sys.exit(0 if status["all_ok"] else 1)

    total = 6
    results = []

    if args.skip_pip:
        step(1, total, "Installing Python packages"); warn("skipped")
    else:
        results.append(("pip", install_pip(total)))

    if args.skip_adb:
        step(2, total, "Setting up Android Platform Tools (adb)"); warn("skipped")
    else:
        results.append(("adb", install_adb(total)))

    if args.skip_tesseract:
        step(3, total, "Setting up Tesseract OCR"); warn("skipped")
    else:
        results.append(("tesseract", install_tesseract(total)))

    write_manifest(total)
    scaffold(total, args.device)
    all_ok = verify(total)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
