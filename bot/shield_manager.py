import logging
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)


class ShieldManager:
    """
    Monitors the Truce Agreement (shield) on the city screen.
    Automatically uses a Truce Agreement item from inventory when the timer
    falls below the configured threshold.

    Evony timer format in the Use Item panel: "Remaining Time: HH:MM:SS"
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def check_and_refresh(self) -> bool:
        logger.info("Checking Truce Agreement status…")

        if not self.nav.go_to_city():
            logger.error("Cannot navigate to city to check Truce Agreement")
            return False

        shot = self.screen.capture()
        if shot is None:
            return False

        # Quick check: if the "expired" indicator is visible, act immediately
        if self.screen.find_template("shield_expired", shot, threshold=0.75):
            logger.warning("Truce Agreement EXPIRED — activating replacement")
            return self._activate_shield()

        # Open inventory to read "Remaining Time: HH:MM:SS" from the Use Item panel
        if not self.nav.open_inventory():
            # Fallback: no dome icon = expired
            if not self.screen.find_template("shield_icon", shot, threshold=0.75):
                logger.warning("No Truce Agreement dome visible — activating")
                return self._activate_shield()
            logger.warning("Could not open inventory to read timer — dome present, assuming OK")
            return True

        time.sleep(0.8)
        inv_shot = self.screen.capture()
        if inv_shot is None:
            self.nav.close_panel()
            return True

        # The green "Remaining Time: HH:MM:SS" bar sits near the top of the Use Item panel
        timer_text = self.screen.read_text_region((0, 30, 700, 55), inv_shot)
        remaining = _parse_minutes(timer_text)
        threshold = self.cfg.get("refresh_threshold_minutes", 60)

        if remaining is None:
            logger.debug("Could not parse timer ('%s') — assuming Truce is active", timer_text)
            self.nav.close_panel()
            return True

        h, m = divmod(remaining, 60)
        logger.info("Truce Agreement: %dh %02dm remaining", h, m)

        if remaining <= threshold:
            logger.info("Below %dm threshold — renewing Truce Agreement", threshold)
            return self._activate_shield_from_inventory(inv_shot)

        self.nav.close_panel()
        return True

    # ── Internal ──────────────────────────────────────────────────────────

    def _activate_shield(self) -> bool:
        """Navigate to inventory then activate the best available Truce Agreement."""
        if not self.nav.open_inventory():
            logger.error("Cannot open inventory")
            return False
        time.sleep(0.8)
        return self._activate_shield_from_inventory(self.screen.capture())

    def _activate_shield_from_inventory(self, shot) -> bool:
        """
        Find and tap the correct Truce Agreement item + its Use button.
        The Use Item panel lists items vertically; each row has a green Use
        button on the right.  We match the Use button to the item row by
        comparing their vertical centre positions.
        """
        if shot is None:
            self.nav.close_panel()
            return False

        use_buttons = self.screen.find_all_templates("use_item_button", shot)
        preferred = self.cfg.get("preferred_shields", ["8h", "24h", "3d", "7d"])

        for shield_type in preferred:
            item_match = self.screen.find_template(f"shield_item_{shield_type}", shot)
            if not item_match:
                continue

            ix, iy, iw, ih, _ = item_match
            item_cy = iy + ih // 2

            # Pick the Use button whose vertical centre is closest to the item row
            row_btn = min(
                use_buttons,
                key=lambda b: abs((b[1] + b[3] // 2) - item_cy),
                default=None,
            )

            if row_btn and abs((row_btn[1] + row_btn[3] // 2) - item_cy) < ih * 2:
                bx, by, bw, bh, _ = row_btn
                self.adb.tap(bx + bw // 2, by + bh // 2)
            else:
                # Fallback: tap to the right of the item (where the Use button should be)
                self.adb.tap(ix + iw + 80, item_cy)

            time.sleep(0.4)
            self.screen.tap_template("confirm_button")
            time.sleep(1.0)
            logger.info("Truce Agreement '%s' activated", shield_type)
            self.nav.close_panel()
            return True

        logger.warning("No Truce Agreement items found in inventory")
        self.nav.close_panel()
        return False


def _parse_minutes(text: str) -> Optional[int]:
    """Convert a timer string to total minutes.

    Handles Evony's two timer formats:
    - Use Item panel green bar: "Remaining Time: 01:21:16"  (HH:MM:SS)
    - Generic text:             "2d 4h 30m", "1h 45m", "30m"
    """
    if not text:
        return None

    # HH:MM:SS  — the format shown in the Use Item / Truce Agreement panel
    m = re.search(r"(\d+):(\d{2}):(\d{2})", text)
    if m:
        hours, mins, secs = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Round up so a timer reading "00:00:45" still triggers a refresh
        return hours * 60 + mins + (1 if secs > 0 else 0)

    # d / h / m  — generic fallback
    total, found = 0, False
    for pattern, mult in [(r"(\d+)\s*d", 1440), (r"(\d+)\s*h", 60), (r"(\d+)\s*m", 1)]:
        m = re.search(pattern, text.lower())
        if m:
            total += int(m.group(1)) * mult
            found = True
    return total if found else None
