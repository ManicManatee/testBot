import logging
import time

logger = logging.getLogger(__name__)

_MAX_HARVEST_PASSES = 6


class ResourceCollector:
    """
    Collects resources from resource buildings (farms, sawmills, quarries,
    iron mines).  Uses a one-tap 'Collect All' shortcut when available;
    otherwise taps the harvest icons that appear above full buildings.
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def run(self) -> int:
        logger.info("Collecting resources…")

        if not self.nav.go_to_city():
            return 0

        shot = self.screen.capture()
        if shot is None:
            return 0

        collected = 0

        # Prefer a single shortcut button that collects everything at once
        if self.screen.find_template("collect_all_button", shot):
            self.screen.tap_template("collect_all_button")
            time.sleep(0.8)
            self.screen.tap_template("confirm_button")
            time.sleep(0.5)
            collected = 1
            logger.info("Collected all resources via shortcut")
            return collected

        # Fall back to tapping harvest icons over individual buildings
        for _ in range(_MAX_HARVEST_PASSES):
            shot = self.screen.capture()
            if shot is None:
                break
            icons = self.screen.find_all_templates("resource_harvest_icon", shot)
            if not icons:
                break
            for ix, iy, iw, ih, _ in icons:
                self.adb.tap(ix + iw // 2, iy + ih // 2)
                time.sleep(0.5)
                self.screen.tap_template("confirm_button")
                time.sleep(0.3)
                collected += 1

        if collected:
            logger.info("Resources collected: %d action(s)", collected)
        else:
            logger.info("No resource buildings ready to harvest")

        return collected
