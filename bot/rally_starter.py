import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class RallyStarter:
    """
    Starts a monster rally from the world map.
    Accepts a monster info dict (as produced by MonsterScanner) and
    navigates to its location, opens the rally panel, configures troops,
    and launches.
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def start_rally(self, monster: dict) -> bool:
        name = monster.get("name", "monster")
        coords = monster.get("coords")
        level = monster.get("level", "?")
        logger.info("Starting rally vs %s Lv.%s at %s", name, level, coords)

        if not self.nav.go_to_world_map():
            logger.error("Cannot navigate to world map")
            return False

        if coords:
            self._jump_to_coords(coords)

        time.sleep(1.0)
        shot = self.screen.capture()

        # Try to tap the correct monster icon
        tapped = False
        for tmpl in self._candidate_templates(monster):
            match = self.screen.find_template(tmpl, shot)
            if match:
                x, y, w, h, _ = match
                self.adb.tap(x + w // 2, y + h // 2)
                tapped = True
                break

        if not tapped:
            logger.warning("Monster icon not found on screen — cannot start rally")
            return False

        time.sleep(1.0)

        if not self.screen.tap_template("rally_button"):
            logger.error("Rally button not found in monster action menu")
            self.nav.close_panel()
            return False

        time.sleep(1.0)
        self._configure_troops()
        self._set_rally_timer()

        launched = (
            self.screen.tap_template("rally_launch_button")
            or self.screen.tap_template("confirm_button")
        )
        if launched:
            time.sleep(1.0)
            logger.info("Rally launched")
            return True

        logger.error("Failed to confirm rally launch")
        return False

    # ── Internal ──────────────────────────────────────────────────────────

    def _jump_to_coords(self, coords: tuple) -> None:
        x_coord, y_coord = coords
        if not self.screen.tap_template("goto_coords_button"):
            return
        time.sleep(0.5)

        x_field = self.screen.find_template("coords_x_field")
        if x_field:
            fx, fy, fw, fh, _ = x_field
            self.adb.tap(fx + fw // 2, fy + fh // 2)
            time.sleep(0.3)
            self.adb.input_text(str(x_coord))

        y_field = self.screen.find_template("coords_y_field")
        if y_field:
            fy2, fy2y, fw2, fh2, _ = y_field
            self.adb.tap(fy2 + fw2 // 2, fy2y + fh2 // 2)
            time.sleep(0.3)
            self.adb.input_text(str(y_coord))

        self.screen.tap_template("goto_confirm_button")
        time.sleep(2.0)

    def _candidate_templates(self, monster: dict) -> list:
        level = monster.get("level", 1)
        mtype = monster.get("type", "")
        templates = []
        if mtype:
            templates.append(f"monster_{mtype.lower()}_level_{level}")
        templates.append(f"monster_level_{level}")
        templates.append("monster_generic")
        return templates

    def _configure_troops(self) -> None:
        troop_cfg = self.cfg.get("troop_config", {})
        if not troop_cfg.get("use_preset", True):
            return

        preset_str = self.cfg.get("march_preset", "preset_1")
        num = preset_str.replace("preset_", "")

        if self.screen.tap_template(f"march_preset_{num}"):
            time.sleep(0.5)
            return

        presets = self.screen.find_all_templates("march_preset_button")
        if presets and num.isdigit():
            idx = int(num) - 1
            if 0 <= idx < len(presets):
                px, py, pw, ph, _ = presets[idx]
                self.adb.tap(px + pw // 2, py + ph // 2)
                time.sleep(0.5)

    def _set_rally_timer(self) -> None:
        minutes = self.cfg.get("rally_time_minutes", 10)
        field = self.screen.find_template("rally_timer_field")
        if not field:
            return
        fx, fy, fw, fh, _ = field
        cx, cy = fx + fw // 2, fy + fh // 2
        self.adb.long_press(cx, cy, 800)
        time.sleep(0.3)
        self.adb.input_text(str(minutes))
        time.sleep(0.3)
