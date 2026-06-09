import logging
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Approximate screen region where the stamina counter sits on the city screen.
# The actual location varies by resolution — the stamina_icon template provides
# a better anchor when it is captured.
_FALLBACK_REGION = (0, 0, 420, 90)


class StaminaManager:
    """
    Reads the stamina counter on the city screen and uses a restore item from
    inventory when it falls below the configured threshold.
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def check_and_restore(self) -> bool:
        logger.info("Checking stamina…")

        if not self.nav.go_to_city():
            return False

        shot = self.screen.capture()
        if shot is None:
            return False

        stamina = self._read_stamina(shot)
        threshold = self.cfg.get("min_stamina", 10)

        if stamina is None:
            logger.debug("Could not read stamina value from screen")
            return False

        logger.info("Stamina: %d (threshold %d)", stamina, threshold)

        if stamina >= threshold:
            return True

        logger.info("Stamina below threshold — using restore item")
        return self._use_stamina_item()

    # ── Internal ──────────────────────────────────────────────────────────

    def _read_stamina(self, shot) -> Optional[int]:
        # Anchor on the stamina icon if captured; fall back to fixed region
        icon = self.screen.find_template("stamina_icon", shot, threshold=0.70)
        if icon:
            ix, iy, iw, ih, _ = icon
            region = (ix + iw, max(0, iy - 4), 110, ih + 8)
        else:
            region = _FALLBACK_REGION

        text = self.screen.read_text_region(region, shot)
        return _parse_stamina(text)

    def _use_stamina_item(self) -> bool:
        if not self.nav.open_inventory():
            logger.error("Cannot open inventory to restore stamina")
            return False

        time.sleep(0.8)
        shot = self.screen.capture()
        if shot is None:
            self.nav.close_panel()
            return False

        use_buttons = self.screen.find_all_templates("use_item_button", shot)
        preferred = self.cfg.get("preferred_items", ["small", "medium", "large"])

        for size in preferred:
            item = self.screen.find_template(f"stamina_item_{size}", shot)
            if not item:
                continue

            ix, iy, iw, ih, _ = item
            item_cy = iy + ih // 2

            btn = min(
                use_buttons,
                key=lambda b: abs((b[1] + b[3] // 2) - item_cy),
                default=None,
            )

            if btn and abs((btn[1] + btn[3] // 2) - item_cy) < ih * 2:
                bx, by, bw, bh, _ = btn
                self.adb.tap(bx + bw // 2, by + bh // 2)
            else:
                self.adb.tap(ix + iw + 80, item_cy)

            time.sleep(0.4)
            self.screen.tap_template("confirm_button")
            time.sleep(0.8)
            logger.info("Stamina restore item (%s) used", size)
            self.nav.close_panel()
            return True

        logger.warning("No stamina restore items found in inventory")
        self.nav.close_panel()
        return False


def _parse_stamina(text: str) -> Optional[int]:
    """Extract current stamina from text like '45', '45/100', or '45 / 100'."""
    if not text:
        return None
    m = re.search(r"(\d+)\s*/\s*\d+", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    return None
