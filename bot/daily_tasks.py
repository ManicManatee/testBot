import logging
import time

logger = logging.getLogger(__name__)

_MAX_SCROLL_PASSES = 8


class DailyTaskManager:
    """
    Opens the Daily Tasks / Quests panel and claims all completed rewards.
    When claim_only is False, also taps 'Go' buttons on incomplete tasks.
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def run(self) -> int:
        logger.info("Checking daily tasks…")

        if not self._open_daily_tasks():
            return 0

        time.sleep(0.8)
        claimed = self._claim_all()

        if not self.cfg.get("claim_only", True):
            self._tap_go_buttons()

        self.nav.close_panel()
        logger.info("Daily tasks: %d reward(s) claimed", claimed)
        return claimed

    # ── Internal ──────────────────────────────────────────────────────────

    def _open_daily_tasks(self) -> bool:
        if not self.nav.go_to_city():
            return False
        if not self.screen.tap_template("daily_tasks_button"):
            logger.warning("Daily Tasks button not found")
            return False
        time.sleep(1.2)
        if not self.screen.wait_for_template("daily_tasks_header", timeout=4):
            logger.warning("Daily Tasks panel did not open")
            return False
        return True

    def _claim_all(self) -> int:
        shot = self.screen.capture()
        if shot is None:
            return 0

        # Prefer one-tap "Claim All" shortcut
        if self.screen.find_template("task_claim_all_button", shot):
            self.screen.tap_template("task_claim_all_button")
            time.sleep(0.8)
            self.screen.tap_template("confirm_button")
            time.sleep(0.5)
            logger.info("Tapped Claim All")
            return 1

        # Claim individually, scrolling down to find more
        claimed = 0
        for _ in range(_MAX_SCROLL_PASSES):
            shot = self.screen.capture()
            if shot is None:
                break
            btns = self.screen.find_all_templates("task_claim_button", shot)
            if not btns:
                break
            for bx, by, bw, bh, _ in btns:
                self.adb.tap(bx + bw // 2, by + bh // 2)
                time.sleep(0.6)
                self.screen.tap_template("confirm_button")
                time.sleep(0.3)
                claimed += 1
            # Scroll down to reveal more tasks
            self.adb.swipe(540, 700, 540, 380, duration_ms=400)
            time.sleep(0.5)

        return claimed

    def _tap_go_buttons(self) -> None:
        """Navigate to each incomplete task and return — limit to 3 to avoid deep loops."""
        for _ in range(3):
            shot = self.screen.capture()
            if shot is None:
                return
            btns = self.screen.find_all_templates("task_go_button", shot)
            if not btns:
                return
            bx, by, bw, bh, _ = btns[0]
            self.adb.tap(bx + bw // 2, by + bh // 2)
            time.sleep(2.5)
            # Return to daily tasks to continue
            self.nav.go_to_city()
            if not self._open_daily_tasks():
                return
            time.sleep(0.8)
