import io
import logging
import subprocess
import time
from typing import Optional, Tuple

from PIL import Image

from bot import dependencies

logger = logging.getLogger(__name__)


class ADBController:
    """Thin wrapper around ADB for device control."""

    def __init__(self, device: str = "127.0.0.1:5555"):
        self.device = device
        # Resolve the adb executable once (bundled tools/, PATH, or well-known)
        self._adb = dependencies.adb_path()
        self._prefix = [self._adb, "-s", device]

    # ── Connection ────────────────────────────────────────────────────────

    def connect(self) -> bool:
        try:
            result = subprocess.run(
                [self._adb, "connect", self.device],
                capture_output=True, text=True, timeout=10,
            )
            ok = "connected" in result.stdout.lower()
            if ok:
                logger.info("Connected to %s", self.device)
            else:
                logger.error("ADB connect failed: %s", result.stdout.strip())
            return ok
        except FileNotFoundError:
            logger.error("adb not found — install Android Platform Tools and add to PATH")
            return False
        except subprocess.TimeoutExpired:
            logger.error("ADB connect timed out")
            return False

    def is_connected(self) -> bool:
        try:
            result = subprocess.run(
                [self._adb, "devices"], capture_output=True, text=True, timeout=5
            )
            return self.device in result.stdout
        except Exception:
            return False

    # ── Screen ────────────────────────────────────────────────────────────

    def screenshot(self) -> Optional[Image.Image]:
        try:
            result = subprocess.run(
                self._prefix + ["exec-out", "screencap", "-p"],
                capture_output=True, timeout=15,
            )
            if result.returncode == 0 and result.stdout:
                return Image.open(io.BytesIO(result.stdout))
            logger.warning("Screenshot returned empty data")
            return None
        except Exception as e:
            logger.error("Screenshot error: %s", e)
            return None

    def get_screen_size(self) -> Tuple[int, int]:
        output = self._shell("wm", "size", capture=True) or ""
        try:
            size_str = output.strip().split(":")[-1].strip()
            w, h = size_str.split("x")
            return int(w), int(h)
        except (ValueError, IndexError):
            return 1920, 1080

    # ── Input ─────────────────────────────────────────────────────────────

    def tap(self, x: int, y: int, delay: float = 0.3) -> None:
        self._shell("input", "tap", str(x), str(y))
        time.sleep(delay)

    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> None:
        self._shell("input", "swipe", str(x), str(y), str(x), str(y), str(duration_ms))
        time.sleep(duration_ms / 1000 + 0.3)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 500) -> None:
        self._shell(
            "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), str(duration_ms),
        )
        time.sleep(duration_ms / 1000 + 0.3)

    def press_back(self) -> None:
        self._shell("input", "keyevent", "KEYCODE_BACK")
        time.sleep(0.5)

    def press_home(self) -> None:
        self._shell("input", "keyevent", "KEYCODE_HOME")
        time.sleep(0.5)

    def input_text(self, text: str) -> None:
        self._shell("input", "text", text)
        time.sleep(0.3)

    # ── Internal ──────────────────────────────────────────────────────────

    def _shell(self, *args: str, capture: bool = False) -> Optional[str]:
        try:
            result = subprocess.run(
                self._prefix + ["shell"] + list(args),
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout if capture else None
        except subprocess.TimeoutExpired:
            logger.warning("Shell command timed out: %s", " ".join(args))
            return None
        except Exception as e:
            logger.error("Shell error (%s): %s", " ".join(args), e)
            return None
