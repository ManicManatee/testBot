import logging
import re
import time
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Templates to search per monster type.
# Regular monsters use level-specific templates where available; a generic
# "monster_regular" catches any regular mob whose level-specific template
# hasn't been captured.  Event types each have one distinctive template
# (the bot taps the icon and reads the actual level from the popup).
_TYPE_TEMPLATES: dict[str, list[str]] = {
    "regular":  ["monster_level_1", "monster_level_2", "monster_level_3",
                 "monster_level_4", "monster_level_5", "monster_level_6",
                 "monster_level_7", "monster_level_8", "monster_level_9",
                 "monster_level_10", "monster_regular"],
    "hydra":    ["monster_hydra"],
    "ymir":     ["monster_ymir"],
    "cerberus": ["monster_cerberus"],
    "golem":    ["monster_golem"],
    "witch":    ["monster_witch"],
    "summoned": ["monster_summoned"],
    "_fallback": ["monster_generic"],
}

# Natural max level per type — used as the default upper bound when the
# user hasn't set a filter for that type
_TYPE_MAX: dict[str, int] = {
    "regular": 23, "hydra": 6, "ymir": 6,
    "cerberus": 5, "golem": 7, "witch": 7, "summoned": 99,
}


class MonsterScanner:
    """
    Scans the world map for all monster types, reads their details via OCR,
    and posts coordinates to alliance chat.  Supports per-type level filters.
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

        for mtype, templates in _TYPE_TEMPLATES.items():
            canonical = mtype if mtype != "_fallback" else None
            if canonical and not self._type_enabled(canonical):
                continue

            for tmpl in templates:
                for match in self.screen.find_all_templates(tmpl, shot):
                    x, y, w, h, _ = match
                    if self._is_duplicate(found, x, y):
                        continue

                    # For level-specific regular templates we already know the level
                    hint_lvl = _level_from_template(tmpl)
                    info = self._tap_and_read(x + w // 2, y + h // 2,
                                             hint_lvl, canonical)
                    if info and self._passes_filter(info):
                        found.append(info)

        return found

    def _tap_and_read(self, cx: int, cy: int,
                      hint_level: Optional[int],
                      hint_type: Optional[str]) -> Optional[dict]:
        self.adb.tap(cx, cy)
        time.sleep(0.9)

        shot = self.screen.capture()
        popup = self.screen.find_template("monster_info_popup", shot, threshold=0.75)
        if not popup:
            self.nav.close_panel()
            return None

        px, py, pw, ph, _ = popup

        name_text   = self.screen.read_text_region((px + 10, py + 8,  pw - 20, 36), shot)
        coords_text = self.screen.read_text_region((px + 10, py + ph - 46, pw - 20, 36), shot)
        lvl_text    = self.screen.read_text_region((px + 10, py + 44, pw // 2, 30), shot)

        level = hint_level or _parse_level(lvl_text)
        mtype = hint_type or _classify_type(name_text or "")

        self.nav.close_panel()
        time.sleep(0.4)

        return {
            "name":       name_text or f"{mtype.title()} Lv.{level}",
            "type":       mtype,
            "level":      level,
            "coords":     _parse_coords(coords_text),
            "screen_pos": (cx, cy),
        }

    def _type_enabled(self, mtype: str) -> bool:
        return self.cfg.get("filters", {}).get(mtype, {}).get("enabled", True)

    def _passes_filter(self, monster: dict) -> bool:
        mtype = monster.get("type") or "regular"
        level = monster.get("level")
        tf = self.cfg.get("filters", {}).get(mtype, {})
        if not tf.get("enabled", True):
            return False
        if level is not None:
            min_lvl = tf.get("min_level", 1)
            max_lvl = tf.get("max_level", _TYPE_MAX.get(mtype, 99))
            if not (min_lvl <= level <= max_lvl):
                return False
        return True

    def _share(self, monster: dict) -> bool:
        if not self.nav.go_to_alliance_chat():
            logger.warning("Cannot open alliance chat")
            return False
        time.sleep(0.5)

        name   = monster.get("name", "Monster")
        level  = monster.get("level", "?")
        coords = monster.get("coords")

        if coords:
            msg = f"[Scout] {name} Lv.{level}  X:{coords[0]} Y:{coords[1]}"
        else:
            msg = f"[Scout] {name} Lv.{level} — coordinates unknown"

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


# ── Module-level helpers ──────────────────────────────────────────────────────

def _classify_type(text: str) -> str:
    """Map monster name text → type key.  Falls back to 'regular'."""
    t = text.lower()
    for kw in ("hydra",):
        if kw in t:
            return "hydra"
    for kw in ("ymir",):
        if kw in t:
            return "ymir"
    for kw in ("cerberus", "cerberуs"):
        if kw in t:
            return "cerberus"
    # "Ancient Golem" / "Event Golem" are event mobs; plain "Golem" may be
    # a regular map monster, so require a qualifier word.
    if re.search(r"(ancient|event|boss)\s+golem|golem\s+(ancient|event|boss)", t):
        return "golem"
    for kw in ("dark witch", "evil witch", "ancient witch"):
        if kw in t:
            return "witch"
    if "summon" in t:
        return "summoned"
    return "regular"


def _level_from_template(tmpl: str) -> Optional[int]:
    m = re.match(r"monster_level_(\d+)$", tmpl)
    return int(m.group(1)) if m else None


def _parse_coords(text: str) -> Optional[Tuple[int, int]]:
    if not text:
        return None
    m = re.search(r"X[:\s](\d+)\s+Y[:\s](\d+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d{3,4})\s*[,xX]\s*(\d{3,4})", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def _parse_level(text: str) -> Optional[int]:
    if not text:
        return None
    m = re.search(r"lv\.?\s*(\d+)|level\s*(\d+)", text.lower())
    if m:
        return int(m.group(1) or m.group(2))
    return None
