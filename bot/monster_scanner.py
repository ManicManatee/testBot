import logging
import re
import time
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class MonsterScanner:
    """
    Scans the world map for monster icons, reads their details via OCR,
    and posts coordinates to alliance chat.
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def scan_and_share(self) -> List[dict]:
        logger.info("Scanning world map for monsters…")

        if not self.nav.go_to_world_map():
            logger.error("Cannot navigate to world map")
            return []

        time.sleep(1.0)
        monsters = self._collect_monsters()

        if not monsters:
            logger.info("No monsters found in current view")
            return []

        logger.info("Found %d monster(s)", len(monsters))

        if self.cfg.get("auto_share", True):
            limit = self.cfg.get("max_share_per_scan", 5)
            for m in monsters[:limit]:
                self._share(m)

        return monsters

    # ── Internal ──────────────────────────────────────────────────────────

    def _collect_monsters(self) -> List[dict]:
        shot = self.screen.capture()
        if shot is None:
            return []

        found: List[dict] = []
        min_lvl = self.cfg.get("min_level", 1)
        max_lvl = self.cfg.get("max_level", 5)

        # Level-specific templates
        for lvl in range(min_lvl, max_lvl + 1):
            for match in self.screen.find_all_templates(f"monster_level_{lvl}", shot):
                x, y, w, h, _ = match
                if self._is_duplicate(found, x, y):
                    continue
                info = self._tap_and_read(x + w // 2, y + h // 2, lvl)
                if info:
                    found.append(info)

        # Generic monster template for any type not covered above
        for match in self.screen.find_all_templates("monster_generic", shot):
            x, y, w, h, _ = match
            if self._is_duplicate(found, x, y):
                continue
            info = self._tap_and_read(x + w // 2, y + h // 2, None)
            if info:
                found.append(info)

        return found

    def _tap_and_read(self, cx: int, cy: int, level: Optional[int]) -> Optional[dict]:
        self.adb.tap(cx, cy)
        time.sleep(0.9)

        shot = self.screen.capture()
        popup = self.screen.find_template("monster_info_popup", shot, threshold=0.75)
        if not popup:
            self.nav.close_panel()
            return None

        px, py, pw, ph, _ = popup

        name_text = self.screen.read_text_region((px + 10, py + 8, pw - 20, 36), shot)
        coords_text = self.screen.read_text_region((px + 10, py + ph - 46, pw - 20, 36), shot)

        if level is None:
            lvl_text = self.screen.read_text_region((px + 10, py + 44, pw // 2, 30), shot)
            level = _parse_level(lvl_text)

        self.nav.close_panel()
        time.sleep(0.4)

        return {
            "name": name_text or f"Monster Lv.{level}",
            "level": level,
            "coords": _parse_coords(coords_text),
            "screen_pos": (cx, cy),
        }

    def _share(self, monster: dict) -> bool:
        if not self.nav.go_to_alliance_chat():
            logger.warning("Cannot open alliance chat")
            return False
        time.sleep(0.5)

        name = monster.get("name", "Monster")
        level = monster.get("level", "?")
        coords = monster.get("coords")

        if coords:
            msg = f"{name} Lv.{level} @ ({coords[0]},{coords[1]}) — Auto Scout"
        else:
            msg = f"{name} Lv.{level} spotted — Auto Scout"

        if not self.screen.tap_template("chat_input_field"):
            logger.warning("Chat input field not found")
            self.nav.close_panel()
            return False

        time.sleep(0.3)
        self.adb.input_text(msg)
        time.sleep(0.3)

        if self.screen.tap_template("chat_send_button"):
            time.sleep(0.5)
            logger.info("Shared: %s", msg)
            self.nav.close_panel()
            return True

        logger.warning("Could not send chat message")
        self.nav.close_panel()
        return False

    @staticmethod
    def _is_duplicate(found: List[dict], x: int, y: int, tol: int = 60) -> bool:
        for m in found:
            mx, my = m.get("screen_pos", (0, 0))
            if abs(mx - x) < tol and abs(my - y) < tol:
                return True
        return False


def _parse_coords(text: str) -> Optional[Tuple[int, int]]:
    m = re.search(r"(\d+)\s*[,xX]\s*(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _parse_level(text: str) -> Optional[int]:
    m = re.search(r"lv\.?\s*(\d+)|level\s*(\d+)", text.lower())
    if m:
        return int(m.group(1) or m.group(2))
    return None
