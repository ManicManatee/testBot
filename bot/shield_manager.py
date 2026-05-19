import logging
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)


class ShieldManager:
    """
    Monitors the protection shield on the city screen.
    Automatically uses a shield item from inventory when the timer
    falls below the configured threshold.
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def check_and_refresh(self) -> bool:
        logger.info("Checking shield status…")

        if not self.nav.go_to_city():
            logger.error("Cannot navigate to city to check shield")
            return False

        shot = self.screen.capture()
        if shot is None:
            return False

        # Detect expired shield first (red icon / "no shield" indicator)
        if self.screen.find_template("shield_expired", shot, threshold=0.75):
            logger.warning("Shield EXPIRED — activating replacement")
            return self._activate_shield()

        shield_match = self.screen.find_template("shield_icon", shot)
        if not shield_match:
            logger.warning("Shield icon not visible — assuming expired")
            return self._activate_shield()

        x, y, w, h, _ = shield_match
        # Read the timer text that typically sits just above or beside the icon
        timer_region = (max(0, x - 20), max(0, y - h), w + 40, h)
        timer_text = self.screen.read_text_region(timer_region, shot)
        remaining = _parse_minutes(timer_text)

        threshold = self.cfg.get("refresh_threshold_minutes", 60)

        if remaining is None:
            logger.debug("Could not parse shield timer text ('%s') — shield assumed OK", timer_text)
            return True

        if remaining <= threshold:
            logger.info("Shield expires in %dm (threshold %dm) — refreshing", remaining, threshold)
            return self._activate_shield()

        logger.info("Shield OK: %dm remaining", remaining)
        return True

    # ── Internal ──────────────────────────────────────────────────────────

    def _activate_shield(self) -> bool:
        if not self.nav.open_inventory():
            logger.error("Cannot open inventory")
            return False

        time.sleep(0.8)
        shot = self.screen.capture()

        for shield_type in self.cfg.get("preferred_shields", ["8h", "24h", "3d"]):
            tmpl = f"shield_item_{shield_type}"
            if self.screen.tap_template(tmpl, shot):
                time.sleep(0.5)
                if self.screen.tap_template("use_item_button"):
                    time.sleep(0.4)
                    self.screen.tap_template("confirm_button")
                    time.sleep(1.0)
                    logger.info("Shield '%s' activated", shield_type)
                    self.nav.close_panel()
                    return True

        logger.warning("No shield items found in inventory")
        self.nav.close_panel()
        return False


def _parse_minutes(text: str) -> Optional[int]:
    """Convert timer strings like '2d 4h 30m', '1h 45m', '30m' to total minutes."""
    if not text:
        return None
    text = text.lower()
    total = 0
    found = False
    for pattern, multiplier in [
        (r"(\d+)\s*d", 1440),
        (r"(\d+)\s*h", 60),
        (r"(\d+)\s*m", 1),
    ]:
        m = re.search(pattern, text)
        if m:
            total += int(m.group(1)) * multiplier
            found = True
    return total if found else None
