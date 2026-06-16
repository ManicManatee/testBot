#!/usr/bin/env python3
"""
Evony: The King's Return — Automation Bot
Entry point and main orchestration loop.

Usage:
    python main.py [--config config.yaml]
"""

import argparse
import logging
import logging.handlers
import os
import signal
import sys
import time

if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

import yaml

from bot import dependencies
from bot.adb_controller import ADBController
from bot.alliance_helper import AllianceHelper
from bot.daily_tasks import DailyTaskManager
from bot.monster_scanner import MonsterScanner
from bot.navigator import Navigator
from bot.rally_joiner import RallyJoiner
from bot.rally_starter import RallyStarter
from bot.resource_collector import ResourceCollector
from bot.royal_thief import RoyalThiefManager
from bot.screen_reader import ScreenReader
from bot.shield_manager import ShieldManager
from bot.stamina_manager import StaminaManager


def _setup_logging(cfg: dict) -> None:
    log_cfg = cfg.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO"), logging.INFO)
    log_file = log_cfg.get("log_file", "logs/evony_bot.log")
    max_bytes = log_cfg.get("max_file_size_mb", 10) * 1024 * 1024

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=3, encoding="utf-8"
        ),
    ]
    for h in handlers:
        h.setFormatter(fmt)

    logging.basicConfig(level=level, handlers=handlers, force=True)


def _load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class EvonyBot:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.running = False
        self.log = logging.getLogger(self.__class__.__name__)

        adb_cfg = cfg.get("adb", {})
        self.adb = ADBController(device=adb_cfg.get("device", "127.0.0.1:5555"))
        self.screen = ScreenReader(self.adb, templates_dir="templates")
        self.nav = Navigator(self.adb, self.screen)

        # Feature managers
        self.shield    = ShieldManager(self.adb, self.screen, self.nav, cfg.get("shield", {}))
        self.joiner    = RallyJoiner(self.adb, self.screen, self.nav, cfg.get("rally_joiner", {}))
        self.starter   = RallyStarter(self.adb, self.screen, self.nav, cfg.get("rally_starter", {}))
        self.scanner   = MonsterScanner(self.adb, self.screen, self.nav, cfg.get("monster_scanner", {}))
        self.daily     = DailyTaskManager(self.adb, self.screen, self.nav, cfg.get("daily_tasks", {}))
        self.thief     = RoyalThiefManager(self.adb, self.screen, self.nav, cfg.get("royal_thief", {}))
        self.stamina   = StaminaManager(self.adb, self.screen, self.nav, cfg.get("stamina", {}))
        self.helper    = AllianceHelper(self.adb, self.screen, self.nav, cfg.get("alliance_helper", {}))
        self.resources = ResourceCollector(self.adb, self.screen, self.nav, cfg.get("resource_collector", {}))

        # Timestamps for interval tracking (0 = overdue, run on first tick)
        self._t_shield    = 0.0
        self._t_rally     = 0.0
        self._t_scan      = 0.0
        self._t_daily     = 0.0
        self._t_thief     = 0.0
        self._t_stamina   = 0.0
        self._t_helper    = 0.0
        self._t_resources = 0.0

        signal.signal(signal.SIGINT, self._on_signal)
        signal.signal(signal.SIGTERM, self._on_signal)

    def start(self) -> None:
        self.log.info("Starting Evony Bot")

        if not self.adb.connect():
            self.log.error(
                "ADB connection failed. "
                "Make sure your emulator is running and ADB is enabled."
            )
            return

        self.running = True
        self.log.info("Bot running — press Ctrl+C to stop")

        while self.running:
            now = time.time()
            self._tick_shield(now)
            self._tick_rally_join(now)
            self._tick_scan(now)
            self._tick_stamina(now)
            self._tick_daily(now)
            self._tick_thief(now)
            self._tick_helper(now)
            self._tick_resources(now)
            time.sleep(1)

        self.log.info("Bot stopped")

    # ── Periodic ticks ────────────────────────────────────────────────────

    def _tick_shield(self, now: float) -> None:
        scfg = self.cfg.get("shield", {})
        if not scfg.get("enabled", True):
            return
        interval = scfg.get("check_interval_minutes", 15) * 60
        if now - self._t_shield < interval:
            return
        self._t_shield = now
        try:
            self.shield.check_and_refresh()
        except Exception:
            self.log.exception("Shield manager error")

    def _tick_rally_join(self, now: float) -> None:
        jcfg = self.cfg.get("rally_joiner", {})
        if not jcfg.get("enabled", True):
            return
        interval = jcfg.get("check_interval_seconds", 10)
        if now - self._t_rally < interval:
            return
        self._t_rally = now
        try:
            self.joiner.check_and_join()
        except Exception:
            self.log.exception("Rally joiner error")

    def _tick_scan(self, now: float) -> None:
        scfg = self.cfg.get("monster_scanner", {})
        rcfg = self.cfg.get("rally_starter", {})
        if not scfg.get("enabled", True):
            return
        interval = scfg.get("scan_interval_minutes", 30) * 60
        if now - self._t_scan < interval:
            return
        self._t_scan = now
        try:
            monsters = self.scanner.scan_and_share()
            if monsters and rcfg.get("enabled", True) and rcfg.get("auto_target_from_scanner", True):
                self.starter.start_rally(monsters[0])
        except Exception:
            self.log.exception("Monster scanner / rally starter error")

    def _tick_stamina(self, now: float) -> None:
        scfg = self.cfg.get("stamina", {})
        if not scfg.get("enabled", True):
            return
        interval = scfg.get("check_interval_minutes", 15) * 60
        if now - self._t_stamina < interval:
            return
        self._t_stamina = now
        try:
            self.stamina.check_and_restore()
        except Exception:
            self.log.exception("Stamina manager error")

    def _tick_daily(self, now: float) -> None:
        dcfg = self.cfg.get("daily_tasks", {})
        if not dcfg.get("enabled", True):
            return
        interval = dcfg.get("check_interval_minutes", 60) * 60
        if now - self._t_daily < interval:
            return
        self._t_daily = now
        try:
            self.daily.run()
        except Exception:
            self.log.exception("Daily tasks error")

    def _tick_thief(self, now: float) -> None:
        tcfg = self.cfg.get("royal_thief", {})
        if not tcfg.get("enabled", True):
            return
        interval = tcfg.get("check_interval_minutes", 30) * 60
        if now - self._t_thief < interval:
            return
        self._t_thief = now
        try:
            self.thief.run()
        except Exception:
            self.log.exception("Royal Thief error")

    def _tick_helper(self, now: float) -> None:
        hcfg = self.cfg.get("alliance_helper", {})
        if not hcfg.get("enabled", True):
            return
        interval = hcfg.get("check_interval_minutes", 20) * 60
        if now - self._t_helper < interval:
            return
        self._t_helper = now
        try:
            self.helper.run()
        except Exception:
            self.log.exception("Alliance helper error")

    def _tick_resources(self, now: float) -> None:
        rcfg = self.cfg.get("resource_collector", {})
        if not rcfg.get("enabled", True):
            return
        interval = rcfg.get("check_interval_minutes", 45) * 60
        if now - self._t_resources < interval:
            return
        self._t_resources = now
        try:
            self.resources.run()
        except Exception:
            self.log.exception("Resource collector error")

    # ── Signal handling ───────────────────────────────────────────────────

    def _on_signal(self, signum, frame) -> None:
        self.log.info("Shutdown signal received")
        self.running = False


def main() -> None:
    parser = argparse.ArgumentParser(description="Evony automation bot")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    args = parser.parse_args()

    cfg = _load_config(args.config)
    _setup_logging(cfg)
    # Point this process at the bundled tools (adb / tesseract) deploy.py set up
    dependencies.configure()
    EvonyBot(cfg).start()


if __name__ == "__main__":
    main()
