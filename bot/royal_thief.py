import logging
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

MatchResult = Tuple[int, int, int, int, float]


class RoyalThiefManager:
    """
    Opens the Royal Thief event and sends rally invitations to active
    alliance members.  Skips the event gracefully when it is not active.
    """

    def __init__(self, adb, screen, navigator, config: dict):
        self.adb = adb
        self.screen = screen
        self.nav = navigator
        self.cfg = config

    # ── Public API ────────────────────────────────────────────────────────

    def run(self) -> int:
        logger.info("Checking Royal Thief event…")

        if not self._open_royal_thief():
            return 0

        time.sleep(0.8)
        sent = self._send_invites()
        self.nav.close_panel()
        logger.info("Royal Thief: %d invite(s) sent", sent)
        return sent

    # ── Internal ──────────────────────────────────────────────────────────

    def _open_royal_thief(self) -> bool:
        if not self.nav.go_to_city():
            return False

        if not self.screen.tap_template("events_button"):
            logger.warning("Events button not found — cannot check Royal Thief")
            return False
        time.sleep(1.0)

        shot = self.screen.capture()
        if shot is None or not self.screen.find_template("royal_thief_event", shot):
            logger.info("Royal Thief event is not currently active")
            self.nav.close_panel()
            return False

        self.screen.tap_template("royal_thief_event")
        time.sleep(1.2)

        if not self.screen.wait_for_template("royal_thief_header", timeout=4):
            logger.warning("Royal Thief screen did not load")
            return False

        return True

    def _send_invites(self) -> int:
        active_only = self.cfg.get("invite_active_only", True)
        max_invites = self.cfg.get("max_invites_per_run", 5)
        sent = 0

        for _ in range(max_invites):
            shot = self.screen.capture()
            if shot is None:
                break

            if active_only:
                # Find the player marked as active/online, then pick the invite
                # button on the same row (closest vertical centre match).
                active_matches = self.screen.find_all_templates("active_player_indicator", shot)
                if not active_matches:
                    logger.info("No active alliance members visible in Royal Thief list")
                    break
                ax, ay, aw, ah, _ = active_matches[0]
                invite_btn = self._nearest_button("player_invite_button", ay + ah // 2, shot)
            else:
                invite_btn = self._nearest_button("royal_thief_invite_button", 0, shot)

            if not invite_btn:
                break

            bx, by, bw, bh, _ = invite_btn
            self.adb.tap(bx + bw // 2, by + bh // 2)
            time.sleep(0.8)
            self.screen.tap_template("confirm_button")
            time.sleep(0.5)
            sent += 1

            # Scroll player list down to expose the next candidate
            self.adb.swipe(540, 650, 540, 380, duration_ms=350)
            time.sleep(0.4)

        return sent

    def _nearest_button(self, template: str, target_cy: int, shot) -> Optional[MatchResult]:
        btns = self.screen.find_all_templates(template, shot)
        if not btns:
            return None
        if target_cy == 0:
            return btns[0]
        return min(btns, key=lambda b: abs((b[1] + b[3] // 2) - target_cy))
