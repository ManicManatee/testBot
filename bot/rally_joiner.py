import logging
import re
import time
from typing import List, Optional

logger = logging.getLogger(__name__)

# Natural max level per type — default upper bound when no filter is set
_TYPE_MAX: dict[str, int] = {
    "regular": 23, "hydra": 6, "ymir": 6,
    "cerberus": 5, "golem": 7, "witch": 7, "summoned": 99,
}


class RallyJoiner:
    """
    Monitors the Alliance War → Monster War tab for active rally invitations
    and joins each one by dispatching exactly 1 troop.
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def check_and_join(self) -> bool:
        if not self._go_to_monster_war():
            return False

        time.sleep(0.8)
        shot = self.screen.capture()
        if shot is None:
            return False

        join_buttons = self.screen.find_all_templates("rally_join_button", shot)
        if not join_buttons:
            logger.info("No joinable rallies visible in Monster War")
            self.nav.close_panel()
            return False

        joined_any = False
        for match in join_buttons:
            x, y, w, h, _ = match

            nearby = self.screen.read_text_region(
                (max(0, x - 300), max(0, y - 80), 400, 160), shot
            )
            level = _extract_level(nearby)
            mtype = _classify_type(nearby)

            if not self._passes_filter(mtype, level):
                logger.info("Skipping rally: %s Lv.%s filtered out", mtype, level)
                continue

            logger.info("Joining rally (type=%s level=%s)", mtype, level)
            self.adb.tap(x + w // 2, y + h // 2)
            time.sleep(1.5)

            if self._dispatch_single_troop():
                logger.info("Rally joined successfully with 1 troop")
                joined_any = True
                time.sleep(1.0)
            else:
                logger.warning("Could not dispatch troop — closing screen")
                self.nav.close_panel()
                time.sleep(0.5)

            # Refresh screenshot; if Monster War is gone we're done
            shot = self.screen.capture()
            if shot is None:
                break
            if not self.screen.find_template("rally_join_button", shot):
                break

        self.nav.close_panel()
        return joined_any

    # ── Internal ──────────────────────────────────────────────────────────

    def _go_to_monster_war(self) -> bool:
        """Navigate to Alliance War → Monster War tab."""
        if not self.nav.go_to_city():
            return False

        if not self.screen.tap_template("alliance_war_button"):
            logger.warning("Alliance War button not found — cannot check for rallies")
            return False
        time.sleep(1.2)

        # Switch to Monster War sub-tab when the Alliance War panel opens
        shot = self.screen.capture()
        if shot is not None and self.screen.find_template("monster_war_tab", shot):
            self.screen.tap_template("monster_war_tab")
            time.sleep(0.8)

        return True

    def _dispatch_single_troop(self) -> bool:
        """
        Handle the Select-a-Preset / march-setup screen that appears after
        tapping a Join button.

        Steps:
          1. Wait for the March button to confirm the screen loaded.
          2. Select the configured preset tab (I–VIII).
          3. Tap Reset to zero all troop counts; fall back to draining manually.
          4. Tap the first visible + button once to add exactly 1 troop.
          5. Tap March.
        """
        if not self.screen.wait_for_template("march_confirm_button", timeout=4):
            logger.warning("March setup screen did not appear after tapping Join")
            return False

        self._select_preset()

        shot = self.screen.capture()

        # Zero all troop counts
        if self.screen.find_template("troop_reset_button", shot):
            self.screen.tap_template("troop_reset_button")
            time.sleep(0.5)
            shot = self.screen.capture()
        else:
            self._zero_all_troops(shot)
            time.sleep(0.3)
            shot = self.screen.capture()

        # Add exactly 1 troop via the first visible + button
        plus_btns = self.screen.find_all_templates("troop_plus_button", shot)
        if plus_btns:
            bx, by, bw, bh, _ = plus_btns[0]
            self.adb.tap(bx + bw // 2, by + bh // 2)
            time.sleep(0.3)
            logger.debug("Troop count set to 1")
        else:
            logger.warning("No troop + button found — marching with whatever count is set")

        if self.screen.tap_template("march_confirm_button"):
            time.sleep(0.5)
            return True

        logger.warning("March button not found after setting troops")
        return False

    def _select_preset(self) -> None:
        """Tap the configured preset tab on the Select a Preset screen."""
        preset_str = self.cfg.get("march_preset", "preset_1")
        num = preset_str.replace("preset_", "")

        if self.screen.tap_template(f"march_preset_{num}"):
            time.sleep(0.5)
            return

        # Fall back to positional index among all visible preset tabs
        presets = self.screen.find_all_templates("march_preset_button")
        if presets and num.isdigit():
            idx = int(num) - 1
            if 0 <= idx < len(presets):
                px, py, pw, ph, _ = presets[idx]
                self.adb.tap(px + pw // 2, py + ph // 2)
                time.sleep(0.5)
                return

        logger.warning("Could not select march preset '%s' — using current preset", preset_str)

    def _zero_all_troops(self, shot) -> None:
        """Tap each visible − button repeatedly to drain troop counts to 0."""
        minus_btns = self.screen.find_all_templates("troop_minus_button", shot)
        for bx, by, bw, bh, _ in minus_btns:
            for _ in range(20):
                self.adb.tap(bx + bw // 2, by + bh // 2)
                time.sleep(0.04)

    def _passes_filter(self, mtype: str, level: Optional[int]) -> bool:
        tf = self.cfg.get("filters", {}).get(mtype, {})
        if not tf.get("enabled", True):
            return False
        if level is not None:
            min_lvl = tf.get("min_level", 1)
            max_lvl = tf.get("max_level", _TYPE_MAX.get(mtype, 99))
            if not (min_lvl <= level <= max_lvl):
                return False
        return True


def _classify_type(text: str) -> str:
    """Map rally-card OCR text → monster type key."""
    t = text.lower()
    if "hydra" in t:
        return "hydra"
    if "ymir" in t:
        return "ymir"
    if "cerberus" in t:
        return "cerberus"
    if re.search(r"(ancient|event|boss)\s+golem|golem\s+(ancient|event|boss)", t):
        return "golem"
    if re.search(r"(dark|evil|ancient)\s+witch", t):
        return "witch"
    if "summon" in t:
        return "summoned"
    return "regular"


def _extract_level(text: str) -> Optional[int]:
    m = re.search(r"lv\.?\s*(\d+)|level\s*(\d+)|(\d+)\s*\*", text.lower())
    if m:
        for g in m.groups():
            if g:
                return int(g)
    return None
