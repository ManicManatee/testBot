import logging
import os
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

try:
    import pytesseract
    _TESSERACT = True
except ImportError:
    _TESSERACT = False

logger = logging.getLogger(__name__)

# All templates are stored at this reference resolution.
# Screenshots are scaled to match before template matching.
REF_W, REF_H = 1920, 1080

# x, y, w, h on the *actual* device screen, plus match confidence
MatchResult = Tuple[int, int, int, int, float]


class ScreenReader:
    """Screenshot capture, template matching, and OCR."""

    def __init__(self, adb, templates_dir: str = "templates"):
        self.adb = adb
        self.templates_dir = templates_dir
        self._cache: dict[str, np.ndarray] = {}
        self._screen_w, self._screen_h = adb.get_screen_size()

    # ── Capture ───────────────────────────────────────────────────────────

    def capture(self) -> Optional[np.ndarray]:
        img = self.adb.screenshot()
        if img is None:
            return None
        arr = np.array(img.convert("RGB"))
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    # ── Template matching ─────────────────────────────────────────────────

    def find_template(
        self,
        name: str,
        screenshot: Optional[np.ndarray] = None,
        threshold: float = 0.8,
    ) -> Optional[MatchResult]:
        results = self.find_all_templates(name, screenshot, threshold, limit=1)
        return results[0] if results else None

    def find_all_templates(
        self,
        name: str,
        screenshot: Optional[np.ndarray] = None,
        threshold: float = 0.8,
        limit: int = 20,
    ) -> List[MatchResult]:
        tmpl = self._load_template(name)
        if tmpl is None:
            return []

        if screenshot is None:
            screenshot = self.capture()
        if screenshot is None:
            return []

        scaled, sx, sy = self._scale_to_ref(screenshot)
        gray_screen = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
        gray_tmpl = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)

        res = cv2.matchTemplate(gray_screen, gray_tmpl, cv2.TM_CCOEFF_NORMED)
        th, tw = gray_tmpl.shape
        matches: List[MatchResult] = []

        work = res.copy()
        while len(matches) < limit:
            _, max_val, _, max_loc = cv2.minMaxLoc(work)
            if max_val < threshold:
                break
            rx, ry = max_loc
            # Convert ref coordinates back to device coordinates
            x = int(rx / sx)
            y = int(ry / sy)
            w = int(tw / sx)
            h = int(th / sy)
            matches.append((x, y, w, h, float(max_val)))
            # Suppress this region so the next iteration finds a different match
            y0 = max(0, ry - th // 2)
            y1 = min(work.shape[0], ry + th)
            x0 = max(0, rx - tw // 2)
            x1 = min(work.shape[1], rx + tw)
            work[y0:y1, x0:x1] = 0

        return matches

    def tap_template(
        self,
        name: str,
        screenshot: Optional[np.ndarray] = None,
        threshold: float = 0.8,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> bool:
        match = self.find_template(name, screenshot, threshold)
        if not match:
            logger.debug("Template not found: %s", name)
            return False
        x, y, w, h, _ = match
        self.adb.tap(x + w // 2 + offset_x, y + h // 2 + offset_y)
        logger.debug("Tapped %s at (%d, %d)", name, x + w // 2, y + h // 2)
        return True

    def wait_for_template(
        self,
        name: str,
        timeout: float = 10.0,
        threshold: float = 0.8,
        poll: float = 0.5,
    ) -> Optional[MatchResult]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            match = self.find_template(name, threshold=threshold)
            if match:
                return match
            time.sleep(poll)
        return None

    # ── OCR ───────────────────────────────────────────────────────────────

    def read_text_region(
        self,
        region: Tuple[int, int, int, int],
        screenshot: Optional[np.ndarray] = None,
    ) -> str:
        if not _TESSERACT:
            logger.warning("pytesseract unavailable — install it for OCR support")
            return ""
        if screenshot is None:
            screenshot = self.capture()
        if screenshot is None:
            return ""
        x, y, w, h = region
        x, y = max(0, x), max(0, y)
        crop = screenshot[y : y + h, x : x + w]
        if crop.size == 0:
            return ""
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        pil = Image.fromarray(binary)
        return pytesseract.image_to_string(pil, config="--psm 7").strip()

    # ── Internal ──────────────────────────────────────────────────────────

    def _scale_to_ref(
        self, img: np.ndarray
    ) -> Tuple[np.ndarray, float, float]:
        h, w = img.shape[:2]
        sx = REF_W / w
        sy = REF_H / h
        if abs(sx - 1.0) < 0.01 and abs(sy - 1.0) < 0.01:
            return img, sx, sy
        scaled = cv2.resize(img, (REF_W, REF_H))
        return scaled, sx, sy

    def _load_template(self, name: str) -> Optional[np.ndarray]:
        if name in self._cache:
            return self._cache[name]
        for root, _, files in os.walk(self.templates_dir):
            for fname in files:
                stem = os.path.splitext(fname)[0]
                if stem == name or fname == name:
                    path = os.path.join(root, fname)
                    img = cv2.imread(path)
                    if img is not None:
                        self._cache[name] = img
                        return img
        logger.warning(
            "Template '%s' not found — run capture_templates.py to create it", name
        )
        return None
