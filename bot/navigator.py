import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Screen state constants
CITY = "city"
WORLD_MAP = "world_map"
ALLIANCE_CHAT = "alliance_chat"
INVENTORY = "inventory"
RALLY_SETUP = "rally_setup"
UNKNOWN = "unknown"


class Navigator:
    """
    Tracks which game screen is visible and provides navigation helpers.
    All managers share this single instance so they don't conflict.
    """

    def __init__(self, adb, screen):
        self.adb = adb
        self.screen = screen
        self.current = UNKNOWN

    # ── Screen detection ──────────────────────────────────────────────────

    def detect(self) -> str:
        shot = self.screen.capture()
        if shot is None:
            return UNKNOWN

        checks = [
            (CITY,          "city_indicator"),
            (WORLD_MAP,     "world_map_indicator"),
            (ALLIANCE_CHAT, "alliance_chat_header"),
            (INVENTORY,     "inventory_header"),
            (RALLY_SETUP,   "rally_setup_header"),
        ]
        for state, tmpl in checks:
            if self.screen.find_template(tmpl, shot, threshold=0.75):
                self.current = state
                return state

        self.current = UNKNOWN
        return UNKNOWN

    # ── Navigation ────────────────────────────────────────────────────────

    def go_to_city(self) -> bool:
        if self.detect() == CITY:
            return True

        # Close open panels first
        for _ in range(4):
            self.adb.press_back()
            time.sleep(0.6)
            if self.detect() == CITY:
                return True

        # Try explicit city button
        if self.screen.tap_template("city_button"):
            time.sleep(1.2)
            return self.detect() == CITY

        logger.warning("Could not navigate to city")
        return False

    def go_to_world_map(self) -> bool:
        if self.detect() == WORLD_MAP:
            return True
        if not self.go_to_city():
            return False
        if self.screen.tap_template("world_map_button"):
            time.sleep(1.5)
            return self.detect() == WORLD_MAP
        logger.warning("World map button not found")
        return False

    def go_to_alliance_chat(self) -> bool:
        if self.detect() == ALLIANCE_CHAT:
            return True
        # Chat button is accessible from most screens
        if self.screen.tap_template("alliance_chat_button"):
            time.sleep(1.0)
            return True
        if self.go_to_city() and self.screen.tap_template("alliance_chat_button"):
            time.sleep(1.0)
            return True
        logger.warning("Alliance chat button not found")
        return False

    def open_inventory(self) -> bool:
        if not self.go_to_city():
            return False
        if self.screen.tap_template("inventory_button"):
            time.sleep(1.0)
            return self.detect() == INVENTORY
        logger.warning("Inventory button not found")
        return False

    def close_panel(self) -> None:
        if not self.screen.tap_template("close_button"):
            self.adb.press_back()
        time.sleep(0.5)
        self.current = UNKNOWN
