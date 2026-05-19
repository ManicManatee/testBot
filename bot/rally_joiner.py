import logging
import re
import time
from typing import List, Optional

logger = logging.getLogger(__name__)


class RallyJoiner:
    """
    Watches for monster rally invitations (in notifications or alliance chat)
    and automatically joins them using a configured march preset.
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def check_and_join(self) -> bool:
        shot = self.screen.capture()
        if shot is None:
            return False

        join_buttons = self.screen.find_all_templates("rally_join_button", shot)

        if not join_buttons:
            return False

        filters = self.cfg.get("filters", {})
        min_lvl = filters.get("min_monster_level", 1)
        max_lvl = filters.get("max_monster_level", 5)
        allowed_types = filters.get("monster_types", ["all"])

        joined_any = False
        for match in join_buttons:
            x, y, w, h, _ = match

            level = self._read_nearby_level(x, y, shot)
            if level is not None and not (min_lvl <= level <= max_lvl):
                logger.info("Skipping rally: level %d outside filter %d–%d", level, min_lvl, max_lvl)
                continue

            mtype = self._read_nearby_type(x, y, shot)
            if "all" not in allowed_types and mtype and mtype.lower() not in [t.lower() for t in allowed_types]:
                logger.info("Skipping rally: type '%s' not in filter", mtype)
                continue

            logger.info("Joining rally (level=%s type=%s) at (%d, %d)", level, mtype, x, y)
            self.adb.tap(x + w // 2, y + h // 2)
            time.sleep(1.5)

            self._select_preset()

            sent = (
                self.screen.tap_template("march_confirm_button")
                or self.screen.tap_template("confirm_button")
            )
            if sent:
                time.sleep(1.0)
                logger.info("Rally joined successfully")
                joined_any = True
            else:
                logger.warning("Could not confirm march — closing")
                self.nav.close_panel()

        return joined_any

    # ── Internal ──────────────────────────────────────────────────────────

    def _select_preset(self) -> None:
        preset_str = self.cfg.get("march_preset", "preset_1")
        num = preset_str.replace("preset_", "")

        # Try named preset template first
        if self.screen.tap_template(f"march_preset_{num}"):
            time.sleep(0.5)
            return

        # Fall back to finding all preset buttons and picking by index
        presets = self.screen.find_all_templates("march_preset_button")
        if presets and num.isdigit():
            idx = int(num) - 1
            if 0 <= idx < len(presets):
                px, py, pw, ph, _ = presets[idx]
                self.adb.tap(px + pw // 2, py + ph // 2)
                time.sleep(0.5)

    def _read_nearby_level(self, x: int, y: int, shot) -> Optional[int]:
        region = (max(0, x - 220), max(0, y - 60), 220, 120)
        text = self.screen.read_text_region(region, shot)
        return _extract_level(text)

    def _read_nearby_type(self, x: int, y: int, shot) -> Optional[str]:
        region = (max(0, x - 220), max(0, y - 60), 320, 60)
        return self.screen.read_text_region(region, shot) or None


def _extract_level(text: str) -> Optional[int]:
    m = re.search(r"lv\.?\s*(\d+)|level\s*(\d+)|(\d+)\s*\*", text.lower())
    if m:
        for g in m.groups():
            if g:
                return int(g)
    return None
