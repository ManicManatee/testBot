import logging
import time

logger = logging.getLogger(__name__)


class AllianceHelper:
    """
    Sends help to alliance members who have requested assistance with
    construction or research.  Taps 'Help All' if available, otherwise
    works through individual help requests.
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def run(self) -> int:
        logger.info("Sending alliance help…")

        if not self.nav.go_to_city():
            return 0

        # The help button is typically a badge icon near the alliance icon.
        # If it is not visible there are no pending requests.
        if not self.screen.find_template("alliance_help_button", self.screen.capture()):
            logger.info("No alliance help requests pending")
            return 0

        self.screen.tap_template("alliance_help_button")
        time.sleep(1.0)

        shot = self.screen.capture()
        if shot is None:
            self.nav.close_panel()
            return 0

        helped = 0

        if self.screen.find_template("help_all_button", shot):
            self.screen.tap_template("help_all_button")
            time.sleep(0.6)
            helped = 1
            logger.info("Tapped Help All")
        else:
            btns = self.screen.find_all_templates("individual_help_button", shot)
            for bx, by, bw, bh, _ in btns:
                self.adb.tap(bx + bw // 2, by + bh // 2)
                time.sleep(0.3)
                helped += 1
            if helped:
                logger.info("Helped %d alliance request(s) individually", helped)

        self.nav.close_panel()
        return helped
