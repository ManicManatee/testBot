import logging
import time
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Pan directions (dx, dy) as swipe deltas at the reference 1920×1080 scale.
# Each pan shifts the world map view roughly one screen width/height.
_PAN_SEQUENCE = [
    (600, 0),    # right
    (0, 400),    # down
    (-600, 0),   # left
    (0, -400),   # up
]

_RESOURCE_TEMPLATES = ["resource_tile_food", "resource_tile_wood",
                       "resource_tile_stone", "resource_tile_iron"]

_TYPE_MAP = {
    "food": "resource_tile_food",
    "wood": "resource_tile_wood",
    "stone": "resource_tile_stone",
    "iron": "resource_tile_iron",
}


class ResourceCollector:
    """
    Sends gathering marches to resource tiles on the world map.

    Flow per run:
      1. Navigate to world map.
      2. Scan visible tiles for configured resource types.
      3. Tap each tile → tap Gather → select march preset → tap March.
      4. Optionally pan the map and repeat to fill remaining march slots.
      5. Stop when max_marches_per_run reached or no tiles remain.
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def run(self) -> int:
        logger.info("Sending resource gathering marches…")

        if not self.nav.go_to_world_map():
            return 0

        time.sleep(1.0)

        max_marches = self.cfg.get("max_marches_per_run", 5)
        pan = self.cfg.get("pan_map", True)
        sent = 0

        # First pass on the current view, then pan to cover surrounding area
        pan_steps = _PAN_SEQUENCE if pan else []
        for step_idx in range(len(pan_steps) + 1):
            shot = self.screen.capture()
            if shot is None:
                break

            tiles = self._find_resource_tiles(shot)
            for tx, ty, tw, th, _ in tiles:
                if sent >= max_marches:
                    break
                result = self._gather_tile(tx + tw // 2, ty + th // 2)
                if result:
                    sent += 1
                    logger.info("Gathering march sent (%d/%d)", sent, max_marches)
                    time.sleep(0.5)

            if sent >= max_marches or step_idx >= len(pan_steps):
                break

            # Pan to reveal the next map section
            dx, dy = pan_steps[step_idx]
            cx, cy = 540, 540  # swipe from centre of screen
            self.adb.swipe(cx, cy, cx - dx, cy - dy, duration_ms=600)
            time.sleep(1.2)

        if sent:
            logger.info("Resource gathering: %d march(es) sent this run", sent)
        else:
            logger.info("No gatherable resource tiles found")

        return sent

    # ── Internal ──────────────────────────────────────────────────────────

    def _find_resource_tiles(self, shot) -> list:
        """Return matches for all configured resource tile types."""
        types = self.cfg.get("resource_types", ["food", "wood", "stone", "iron"])
        results = []
        seen: List[Tuple[int, int]] = []

        for rtype in types:
            tmpl = _TYPE_MAP.get(rtype.lower())
            if not tmpl:
                continue
            for match in self.screen.find_all_templates(tmpl, shot):
                x, y, w, h, _ = match
                cx, cy = x + w // 2, y + h // 2
                # Deduplicate across template types
                if any(abs(cx - sx) < 50 and abs(cy - sy) < 50 for sx, sy in seen):
                    continue
                seen.append((cx, cy))
                results.append(match)

        return results

    def _gather_tile(self, cx: int, cy: int) -> bool:
        """Tap a tile, choose Gather, pick preset, march. Returns True on success."""
        self.adb.tap(cx, cy)
        time.sleep(0.9)

        shot = self.screen.capture()
        if shot is None:
            return False

        # The tile action menu must show a Gather option
        if not self.screen.find_template("gather_button", shot):
            # Could be occupied, wrong tile type, or already gathering
            self.nav.close_panel()
            return False

        self.screen.tap_template("gather_button")
        time.sleep(1.2)

        # Wait for the gather / march setup screen
        if not self.screen.wait_for_template("march_confirm_button", timeout=4):
            logger.debug("Gather setup screen did not appear at (%d, %d)", cx, cy)
            self.nav.close_panel()
            return False

        self._select_preset()

        # Confirm the march
        if not self.screen.tap_template("march_confirm_button"):
            logger.debug("March button not found on gather screen")
            self.nav.close_panel()
            return False

        time.sleep(0.8)

        # If a full-queue error popup appeared, dismiss it and report failure
        shot = self.screen.capture()
        if shot is not None and self.screen.find_template("march_confirm_button", shot):
            # Still on the gather screen — march was rejected (queue full or error)
            logger.info("March queue full or rejected — stopping gather run")
            self.nav.close_panel()
            return False

        return True

    def _select_preset(self) -> None:
        """Select the configured gather preset tab."""
        preset_str = self.cfg.get("march_preset", "preset_2")
        num = preset_str.replace("preset_", "")

        if self.screen.tap_template(f"march_preset_{num}"):
            time.sleep(0.4)
            return

        presets = self.screen.find_all_templates("march_preset_button")
        if presets and num.isdigit():
            idx = int(num) - 1
            if 0 <= idx < len(presets):
                px, py, pw, ph, _ = presets[idx]
                self.adb.tap(px + pw // 2, py + ph // 2)
                time.sleep(0.4)
