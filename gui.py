#!/usr/bin/env python3
"""
Evony Bot — GUI Manager
Dark-themed control panel built with CustomTkinter.

Usage:
    python gui.py
"""

import logging
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

import customtkinter as ctk
import yaml

# Frozen-exe path fix (same as main.py / capture_templates.py)
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

CONFIG_PATH = "config.yaml"
PRESETS = [f"preset_{i}" for i in range(1, 6)]
STAMINA_ITEMS = ["small", "medium", "large"]

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

_FONT = ("Segoe UI", 13)
_MONO = ("Consolas", 11)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_cfg() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def _save_cfg(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)


class _QueueHandler(logging.Handler):
    """Forwards log records to a thread-safe queue."""
    def __init__(self, q: "queue.Queue[str]"):
        super().__init__()
        self.q = q

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.q.put_nowait(self.format(record))
        except Exception:
            pass


# ── Reusable widget helpers ───────────────────────────────────────────────────

class _Row(ctk.CTkFrame):
    """Transparent horizontal row used inside settings panels."""
    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color="transparent", **kw)
        self.pack(fill="x", padx=16, pady=4)


class LabeledSwitch:
    def __init__(self, parent: ctk.CTkFrame, label: str, default: bool):
        row = _Row(parent)
        ctk.CTkLabel(row, text=label, font=_FONT, anchor="w").pack(side="left", fill="x", expand=True)
        self._var = ctk.BooleanVar(value=default)
        sw = ctk.CTkSwitch(row, text="", variable=self._var, width=52)
        sw.pack(side="right")
        if default:
            sw.select()

    def get(self) -> bool:
        return self._var.get()


class LabeledEntry:
    def __init__(self, parent: ctk.CTkFrame, label: str, default, hint: str = "", width: int = 110):
        row = _Row(parent)
        ctk.CTkLabel(row, text=label, font=_FONT, anchor="w", width=300).pack(side="left")
        self._ent = ctk.CTkEntry(row, width=width)
        self._ent.insert(0, str(default))
        self._ent.pack(side="left")
        if hint:
            ctk.CTkLabel(row, text=f"  {hint}", font=ctk.CTkFont(size=10),
                         text_color="#888888").pack(side="left")

    def get(self) -> str:
        return self._ent.get()

    def get_int(self) -> int:
        try:
            return int(self._ent.get())
        except ValueError:
            return 0


class LabeledOption:
    def __init__(self, parent: ctk.CTkFrame, label: str, default: str, options: list[str]):
        row = _Row(parent)
        ctk.CTkLabel(row, text=label, font=_FONT, anchor="w", width=300).pack(side="left")
        self._menu = ctk.CTkOptionMenu(row, values=options, width=150)
        self._menu.set(default)
        self._menu.pack(side="left")

    def get(self) -> str:
        return self._menu.get()


def _save_btn(parent: ctk.CTkFrame, cmd) -> ctk.CTkButton:
    btn = ctk.CTkButton(parent, text="Save settings", width=140, command=cmd)
    btn.pack(anchor="w", padx=16, pady=(12, 8))
    return btn


def _separator(parent: ctk.CTkFrame) -> None:
    ctk.CTkFrame(parent, height=1, fg_color="#333333").pack(fill="x", padx=16, pady=8)


# ── Main Application ──────────────────────────────────────────────────────────

class EvonyBotGUI(ctk.CTk):
    W, H = 1060, 720

    def __init__(self):
        super().__init__()
        self.title("Evony Bot Manager")
        self.geometry(f"{self.W}x{self.H}")
        self.minsize(860, 580)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.cfg = _load_cfg()
        self._log_q: "queue.Queue[str]" = queue.Queue()
        self._bot = None
        self._bot_thread: threading.Thread | None = None
        self._uptime_start: float | None = None
        self._rally_count = 0
        self._monster_count = 0
        self._task_count = 0
        self._invite_count = 0
        self._help_count = 0
        self._resource_count = 0

        self._setup_logging()
        self._build()
        self._poll_logs()

    # ── Logging ───────────────────────────────────────────────────────────

    def _setup_logging(self) -> None:
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        h = _QueueHandler(self._log_q)
        h.setFormatter(fmt)
        root = logging.getLogger()
        root.addHandler(h)
        root.setLevel(logging.DEBUG)

    def _poll_logs(self) -> None:
        try:
            while True:
                msg = self._log_q.get_nowait()
                self._log_box.configure(state="normal")
                self._log_box.insert("end", msg + "\n")
                self._log_box.see("end")
                self._log_box.configure(state="disabled")
                # Update stat cards from log hints
                ml = msg.lower()
                if "rally joined" in ml:
                    self._rally_count += 1
                    self._card_rallies.configure(text=str(self._rally_count))
                if "shared:" in ml or "monster" in ml and "found" in ml:
                    self._monster_count += 1
                    self._card_monsters.configure(text=str(self._monster_count))
                if "shield ok" in ml or "shield" in ml and "remaining" in ml:
                    import re
                    m = re.search(r"(\d+)m remaining", msg)
                    if m:
                        mins = int(m.group(1))
                        h2, rem = divmod(mins, 60)
                        self._card_shield.configure(text=f"{h2}h {rem:02d}m" if h2 else f"{rem}m")
                if "daily tasks:" in ml and "claimed" in ml:
                    import re
                    m = re.search(r"(\d+) reward", msg)
                    if m:
                        self._task_count += int(m.group(1))
                        self._card_tasks.configure(text=str(self._task_count))
                if "royal thief:" in ml and "invite" in ml:
                    import re
                    m = re.search(r"(\d+) invite", msg)
                    if m:
                        self._invite_count += int(m.group(1))
                        self._card_invites.configure(text=str(self._invite_count))
                if "alliance help:" in ml:
                    import re
                    m = re.search(r"(\d+) request|tapped help all", msg.lower())
                    if m:
                        self._help_count += 1
                        self._card_helps.configure(text=str(self._help_count))
                if "resources collected:" in ml:
                    import re
                    m = re.search(r"(\d+) action", msg)
                    if m:
                        self._resource_count += int(m.group(1))
                        self._card_resources.configure(text=str(self._resource_count))
        except queue.Empty:
            pass
        self.after(200, self._poll_logs)

    # ── Layout ────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_header()
        self._build_tabs()
        self._build_statusbar()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, height=58, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="  Evony Bot Manager",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=12, sticky="w")

        self._conn_lbl = ctk.CTkLabel(
            hdr, text="● Idle",
            font=ctk.CTkFont(size=13), text_color="#888888",
        )
        self._conn_lbl.grid(row=0, column=2, padx=16, sticky="e")

        btn_row = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_row.grid(row=0, column=3, padx=12)

        self._start_btn = ctk.CTkButton(
            btn_row, text="▶  Start Bot", width=120,
            fg_color="#1a5a96", hover_color="#0d3d69",
            command=self._start_bot,
        )
        self._start_btn.pack(side="left", padx=4)

        self._stop_btn = ctk.CTkButton(
            btn_row, text="■  Stop Bot", width=120,
            fg_color="#6b1f1f", hover_color="#4a1515",
            state="disabled", command=self._stop_bot,
        )
        self._stop_btn.pack(side="left", padx=4)

    def _build_tabs(self) -> None:
        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 0))

        for t in ["Dashboard", "Shield", "Rally Joiner", "Rally Starter", "Scanner",
                  "Daily Tasks", "Royal Thief", "Stamina", "Alliance", "Resources",
                  "Templates", "Settings"]:
            self._tabs.add(t)

        self._build_dashboard()
        self._build_shield_tab()
        self._build_joiner_tab()
        self._build_starter_tab()
        self._build_scanner_tab()
        self._build_daily_tab()
        self._build_thief_tab()
        self._build_stamina_tab()
        self._build_alliance_tab()
        self._build_resources_tab()
        self._build_templates_tab()
        self._build_settings_tab()

    def _build_statusbar(self) -> None:
        bar = ctk.CTkFrame(self, height=28, corner_radius=0)
        bar.grid(row=2, column=0, sticky="ew")
        self._status_lbl = ctk.CTkLabel(
            bar, text="Ready", font=ctk.CTkFont(size=11), text_color="#888888",
        )
        self._status_lbl.pack(side="left", padx=12)

    # ── Dashboard ─────────────────────────────────────────────────────────

    def _build_dashboard(self) -> None:
        tab = self._tabs.tab("Dashboard")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Stat cards — two rows of four
        cards = ctk.CTkFrame(tab, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew", pady=(4, 8))
        for i in range(4):
            cards.grid_columnconfigure(i, weight=1)

        self._card_shield    = self._stat_card(cards, "Shield",          "—", 0, 0)
        self._card_rallies   = self._stat_card(cards, "Rallies Joined",  "0", 1, 0)
        self._card_monsters  = self._stat_card(cards, "Monsters Found",  "0", 2, 0)
        self._card_uptime    = self._stat_card(cards, "Uptime",          "—", 3, 0)
        self._card_tasks     = self._stat_card(cards, "Tasks Claimed",   "0", 0, 1)
        self._card_invites   = self._stat_card(cards, "RT Invites Sent", "0", 1, 1)
        self._card_helps     = self._stat_card(cards, "Alliance Helps",  "0", 2, 1)
        self._card_resources = self._stat_card(cards, "Resources Runs",  "0", 3, 1)

        # Log pane
        log_frame = ctk.CTkFrame(tab)
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_frame, text="Live Log",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(6, 2))
        ctk.CTkButton(
            log_frame, text="Clear", width=70,
            command=lambda: (
                self._log_box.configure(state="normal"),
                self._log_box.delete("1.0", "end"),
                self._log_box.configure(state="disabled"),
            ),
        ).grid(row=0, column=1, padx=10, sticky="e")

        self._log_box = ctk.CTkTextbox(
            log_frame, font=ctk.CTkFont(family="Consolas", size=11), state="disabled",
        )
        self._log_box.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 8))

    def _stat_card(self, parent, title: str, value: str, col: int, row: int = 0) -> ctk.CTkLabel:
        f = ctk.CTkFrame(parent)
        f.grid(row=row, column=col, padx=5, pady=4, sticky="ew")
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=11), text_color="#aaaaaa").pack(pady=(8, 0))
        lbl = ctk.CTkLabel(f, text=value, font=ctk.CTkFont(size=22, weight="bold"))
        lbl.pack(pady=(0, 8))
        return lbl

    # ── Shield tab ────────────────────────────────────────────────────────

    def _build_shield_tab(self) -> None:
        f = self._panel(self._tabs.tab("Shield"))
        s = self.cfg.get("shield", {})

        self._sw_shield     = LabeledSwitch(f, "Enable shield monitor", s.get("enabled", True))
        self._en_sh_interval = LabeledEntry(f, "Check interval (minutes)", s.get("check_interval_minutes", 15))
        self._en_sh_thresh   = LabeledEntry(f, "Refresh shield when below (minutes)", s.get("refresh_threshold_minutes", 60))

        _separator(f)
        ctk.CTkLabel(f, text="Preferred shield order  (comma-separated: 8h, 24h, 3d)",
                     font=_FONT).pack(anchor="w", padx=16, pady=(4, 0))
        self._en_sh_order = ctk.CTkEntry(f, width=300)
        self._en_sh_order.insert(0, ", ".join(s.get("preferred_shields", ["8h", "24h", "3d"])))
        self._en_sh_order.pack(anchor="w", padx=16, pady=(4, 0))

        _save_btn(f, self._save_shield)

    # ── Rally Joiner tab ──────────────────────────────────────────────────

    def _build_joiner_tab(self) -> None:
        f = self._panel(self._tabs.tab("Rally Joiner"))
        j = self.cfg.get("rally_joiner", {})
        flt = j.get("filters", {})

        self._sw_joiner       = LabeledSwitch(f, "Enable rally joiner", j.get("enabled", True))
        self._en_j_interval   = LabeledEntry(f, "Check interval (seconds)", j.get("check_interval_seconds", 10))
        self._om_j_preset     = LabeledOption(f, "March preset", j.get("march_preset", "preset_1"), PRESETS)
        _separator(f)
        ctk.CTkLabel(f, text="Monster level filter", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=16, pady=(4, 0))
        self._en_j_min_lvl    = LabeledEntry(f, "Minimum level", flt.get("min_monster_level", 1), width=80)
        self._en_j_max_lvl    = LabeledEntry(f, "Maximum level", flt.get("max_monster_level", 5), width=80)

        _save_btn(f, self._save_joiner)

    # ── Rally Starter tab ─────────────────────────────────────────────────

    def _build_starter_tab(self) -> None:
        f = self._panel(self._tabs.tab("Rally Starter"))
        r = self.cfg.get("rally_starter", {})

        self._sw_starter      = LabeledSwitch(f, "Enable rally starter", r.get("enabled", True))
        self._sw_auto_target  = LabeledSwitch(f, "Auto-target monsters found by scanner", r.get("auto_target_from_scanner", True))
        self._om_s_preset     = LabeledOption(f, "March preset", r.get("march_preset", "preset_1"), PRESETS)
        self._en_s_timer      = LabeledEntry(f, "Rally open time (minutes)", r.get("rally_time_minutes", 10))

        _save_btn(f, self._save_starter)

    # ── Monster Scanner tab ───────────────────────────────────────────────

    def _build_scanner_tab(self) -> None:
        f = self._panel(self._tabs.tab("Scanner"))
        s = self.cfg.get("monster_scanner", {})

        self._sw_scanner     = LabeledSwitch(f, "Enable monster scanner", s.get("enabled", True))
        self._sw_auto_share  = LabeledSwitch(f, "Auto-share finds to alliance chat", s.get("auto_share", True))
        self._en_sc_interval = LabeledEntry(f, "Scan interval (minutes)", s.get("scan_interval_minutes", 30))
        _separator(f)
        self._en_sc_min      = LabeledEntry(f, "Min monster level to hunt", s.get("min_level", 1), width=80)
        self._en_sc_max      = LabeledEntry(f, "Max monster level to hunt", s.get("max_level", 5), width=80)
        self._en_sc_share    = LabeledEntry(f, "Max monsters shared per scan", s.get("max_share_per_scan", 5), width=80)

        _save_btn(f, self._save_scanner)

    # ── Daily Tasks tab ───────────────────────────────────────────────────

    def _build_daily_tab(self) -> None:
        f = self._panel(self._tabs.tab("Daily Tasks"))
        d = self.cfg.get("daily_tasks", {})

        self._sw_daily      = LabeledSwitch(f, "Enable daily task manager", d.get("enabled", True))
        self._en_dt_interval = LabeledEntry(f, "Check interval (minutes)", d.get("check_interval_minutes", 60))
        self._sw_claim_only = LabeledSwitch(f, "Claim only (don't tap Go buttons)", d.get("claim_only", True))

        _save_btn(f, self._save_daily)

    # ── Royal Thief tab ───────────────────────────────────────────────────

    def _build_thief_tab(self) -> None:
        f = self._panel(self._tabs.tab("Royal Thief"))
        t = self.cfg.get("royal_thief", {})

        self._sw_thief          = LabeledSwitch(f, "Enable Royal Thief invites", t.get("enabled", True))
        self._en_rt_interval    = LabeledEntry(f, "Check interval (minutes)", t.get("check_interval_minutes", 30))
        self._sw_active_only    = LabeledSwitch(f, "Only invite active/online members", t.get("invite_active_only", True))
        self._en_rt_max_invites = LabeledEntry(f, "Max invites per run", t.get("max_invites_per_run", 5), width=80)

        _save_btn(f, self._save_thief)

    # ── Stamina tab ───────────────────────────────────────────────────────

    def _build_stamina_tab(self) -> None:
        f = self._panel(self._tabs.tab("Stamina"))
        s = self.cfg.get("stamina", {})

        self._sw_stamina       = LabeledSwitch(f, "Enable stamina manager", s.get("enabled", True))
        self._en_st_interval   = LabeledEntry(f, "Check interval (minutes)", s.get("check_interval_minutes", 15))
        self._en_st_min        = LabeledEntry(f, "Restore when stamina below", s.get("min_stamina", 10), width=80)
        _separator(f)
        ctk.CTkLabel(f, text="Preferred restore items  (comma-separated: small, medium, large)",
                     font=_FONT).pack(anchor="w", padx=16, pady=(4, 0))
        self._en_st_items = ctk.CTkEntry(f, width=260)
        self._en_st_items.insert(0, ", ".join(s.get("preferred_items", ["small", "medium", "large"])))
        self._en_st_items.pack(anchor="w", padx=16, pady=(4, 0))

        _save_btn(f, self._save_stamina)

    # ── Alliance tab ──────────────────────────────────────────────────────

    def _build_alliance_tab(self) -> None:
        f = self._panel(self._tabs.tab("Alliance"))
        h = self.cfg.get("alliance_helper", {})

        ctk.CTkLabel(f, text="Alliance Helper",
                     font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="w", padx=16, pady=(12, 2))
        self._sw_helper      = LabeledSwitch(f, "Enable alliance helper (Help All)", h.get("enabled", True))
        self._en_h_interval  = LabeledEntry(f, "Check interval (minutes)", h.get("check_interval_minutes", 20))

        _save_btn(f, self._save_alliance)

    # ── Resources tab ─────────────────────────────────────────────────────

    def _build_resources_tab(self) -> None:
        f = self._panel(self._tabs.tab("Resources"))
        r = self.cfg.get("resource_collector", {})

        self._sw_resources    = LabeledSwitch(f, "Enable resource collector", r.get("enabled", True))
        self._en_rc_interval  = LabeledEntry(f, "Check interval (minutes)", r.get("check_interval_minutes", 30))
        self._om_rc_preset    = LabeledOption(f, "March preset for gathering", r.get("march_preset", "preset_2"), PRESETS)
        self._en_rc_max       = LabeledEntry(f, "Max marches per run", r.get("max_marches_per_run", 5), width=80)
        self._sw_rc_pan       = LabeledSwitch(f, "Pan map to find more tiles", r.get("pan_map", True))
        _separator(f)
        ctk.CTkLabel(f, text="Resource types to gather  (comma-separated: food, wood, stone, iron)",
                     font=_FONT).pack(anchor="w", padx=16, pady=(4, 0))
        self._en_rc_types = ctk.CTkEntry(f, width=300)
        self._en_rc_types.insert(0, ", ".join(r.get("resource_types", ["food", "wood", "stone", "iron"])))
        self._en_rc_types.pack(anchor="w", padx=16, pady=(4, 0))

        _save_btn(f, self._save_resources)

    # ── Templates tab ─────────────────────────────────────────────────────

    def _build_templates_tab(self) -> None:
        tab = self._tabs.tab("Templates")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            tab,
            text="Templates teach the bot what each UI element looks like.\n"
                 "Green ● = captured   Red ○ = missing (bot cannot use this feature until captured)",
            font=ctk.CTkFont(size=12), text_color="#aaaaaa", justify="left",
        ).grid(row=0, column=0, padx=16, pady=(12, 6), sticky="w")

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="w")
        ctk.CTkButton(btn_row, text="▶  Launch Capture Tool", width=200,
                      command=self._launch_capture).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_row, text="↻  Refresh", width=110,
                      fg_color="transparent", border_width=1,
                      command=self._refresh_templates).pack(side="left")

        self._tmpl_scroll = ctk.CTkScrollableFrame(tab, label_text="Template status")
        self._tmpl_scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 8))

        self._refresh_templates()

    def _refresh_templates(self) -> None:
        for w in self._tmpl_scroll.winfo_children():
            w.destroy()

        from capture_templates import TEMPLATES
        for name, subdir, description in TEMPLATES:
            exists = (Path("templates") / subdir / f"{name}.png").exists()
            color = "#2ecc71" if exists else "#e74c3c"
            row = ctk.CTkFrame(self._tmpl_scroll, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text="●" if exists else "○",
                         text_color=color, width=22,
                         font=ctk.CTkFont(size=13)).pack(side="left")
            ctk.CTkLabel(row, text=f" {name:<35}",
                         font=ctk.CTkFont(family="Consolas", size=11),
                         anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=description,
                         font=ctk.CTkFont(size=10), text_color="#888888",
                         anchor="w").pack(side="left", fill="x")

    def _launch_capture(self) -> None:
        if getattr(sys, "frozen", False):
            exe = Path(sys.executable).parent / "capture_templates.exe"
            subprocess.Popen(
                [str(exe)],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
            )
        else:
            subprocess.Popen([sys.executable, "capture_templates.py"])

    # ── Settings tab ──────────────────────────────────────────────────────

    def _build_settings_tab(self) -> None:
        f = self._panel(self._tabs.tab("Settings"))
        a = self.cfg.get("adb", {})
        l = self.cfg.get("logging", {})

        ctk.CTkLabel(f, text="ADB Device Address", font=_FONT).pack(
            anchor="w", padx=16, pady=(16, 0))
        ctk.CTkLabel(
            f,
            text="BlueStacks 5: 127.0.0.1:5555  |  MuMu: 127.0.0.1:7555  "
                 "|  LDPlayer: 127.0.0.1:5554  |  Nox: 127.0.0.1:62001",
            font=ctk.CTkFont(size=10), text_color="#666666",
        ).pack(anchor="w", padx=16)

        dev_row = _Row(f)
        self._en_device = ctk.CTkEntry(dev_row, width=280)
        self._en_device.insert(0, a.get("device", "127.0.0.1:5555"))
        self._en_device.pack(side="left")
        ctk.CTkButton(dev_row, text="Test", width=80,
                      command=self._test_adb).pack(side="left", padx=8)
        self._adb_lbl = ctk.CTkLabel(dev_row, text="", font=ctk.CTkFont(size=12))
        self._adb_lbl.pack(side="left")

        _separator(f)
        self._om_log_level = LabeledOption(
            f, "Log level", l.get("level", "INFO"), ["DEBUG", "INFO", "WARNING", "ERROR"]
        )

        _save_btn(f, self._save_settings)

    def _test_adb(self) -> None:
        device = self._en_device.get().strip()
        try:
            r = subprocess.run(
                ["adb", "connect", device], capture_output=True, text=True, timeout=8
            )
            ok = "connected" in r.stdout.lower()
            self._adb_lbl.configure(
                text="✓ Connected" if ok else "✗ Failed",
                text_color="#2ecc71" if ok else "#e74c3c",
            )
            self._conn_lbl.configure(
                text=f"● {device}" if ok else "● Failed",
                text_color="#2ecc71" if ok else "#e74c3c",
            )
            self._set_status(f"ADB: {r.stdout.strip()}")
        except FileNotFoundError:
            self._adb_lbl.configure(text="✗ adb not found", text_color="#e74c3c")
            self._set_status("adb.exe not in PATH — install Android Platform Tools")
        except Exception as e:
            self._set_status(f"ADB error: {e}")

    # ── Bot lifecycle ─────────────────────────────────────────────────────

    def _start_bot(self) -> None:
        if self._bot_thread and self._bot_thread.is_alive():
            return

        self._apply_all()
        cfg = _load_cfg()

        from main import EvonyBot
        self._bot = EvonyBot(cfg)

        self._bot_thread = threading.Thread(
            target=self._bot.start, daemon=True, name="EvonyBot"
        )
        self._bot_thread.start()

        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._conn_lbl.configure(text="● Running", text_color="#2ecc71")
        self._set_status("Bot started")
        self._uptime_start = time.time()
        self._tick_uptime()
        self._rally_count = 0
        self._monster_count = 0
        self._task_count = 0
        self._invite_count = 0
        self._help_count = 0
        self._resource_count = 0

    def _stop_bot(self) -> None:
        if self._bot:
            self._bot.running = False
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._conn_lbl.configure(text="● Stopped", text_color="#e67e22")
        self._set_status("Bot stopped")
        self._uptime_start = None

    def _tick_uptime(self) -> None:
        if self._uptime_start is None:
            return
        elapsed = int(time.time() - self._uptime_start)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        self._card_uptime.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
        self.after(1000, self._tick_uptime)

    # ── Save handlers ─────────────────────────────────────────────────────

    def _apply_all(self) -> None:
        for fn in [self._save_shield, self._save_joiner, self._save_starter,
                   self._save_scanner, self._save_daily, self._save_thief,
                   self._save_stamina, self._save_alliance, self._save_resources,
                   self._save_settings]:
            fn()

    def _save_shield(self) -> None:
        self.cfg.setdefault("shield", {}).update({
            "enabled": self._sw_shield.get(),
            "check_interval_minutes": self._en_sh_interval.get_int(),
            "refresh_threshold_minutes": self._en_sh_thresh.get_int(),
            "preferred_shields": [s.strip() for s in self._en_sh_order.get().split(",") if s.strip()],
        })
        _save_cfg(self.cfg)
        self._set_status("Shield settings saved")

    def _save_joiner(self) -> None:
        self.cfg.setdefault("rally_joiner", {}).update({
            "enabled": self._sw_joiner.get(),
            "check_interval_seconds": self._en_j_interval.get_int(),
            "march_preset": self._om_j_preset.get(),
            "filters": {
                "min_monster_level": self._en_j_min_lvl.get_int(),
                "max_monster_level": self._en_j_max_lvl.get_int(),
                "monster_types": ["all"],
            },
        })
        _save_cfg(self.cfg)
        self._set_status("Rally joiner settings saved")

    def _save_starter(self) -> None:
        self.cfg.setdefault("rally_starter", {}).update({
            "enabled": self._sw_starter.get(),
            "auto_target_from_scanner": self._sw_auto_target.get(),
            "march_preset": self._om_s_preset.get(),
            "rally_time_minutes": self._en_s_timer.get_int(),
        })
        _save_cfg(self.cfg)
        self._set_status("Rally starter settings saved")

    def _save_scanner(self) -> None:
        self.cfg.setdefault("monster_scanner", {}).update({
            "enabled": self._sw_scanner.get(),
            "auto_share": self._sw_auto_share.get(),
            "scan_interval_minutes": self._en_sc_interval.get_int(),
            "min_level": self._en_sc_min.get_int(),
            "max_level": self._en_sc_max.get_int(),
            "max_share_per_scan": self._en_sc_share.get_int(),
        })
        _save_cfg(self.cfg)
        self._set_status("Scanner settings saved")

    def _save_daily(self) -> None:
        self.cfg.setdefault("daily_tasks", {}).update({
            "enabled": self._sw_daily.get(),
            "check_interval_minutes": self._en_dt_interval.get_int(),
            "claim_only": self._sw_claim_only.get(),
        })
        _save_cfg(self.cfg)
        self._set_status("Daily tasks settings saved")

    def _save_thief(self) -> None:
        self.cfg.setdefault("royal_thief", {}).update({
            "enabled": self._sw_thief.get(),
            "check_interval_minutes": self._en_rt_interval.get_int(),
            "invite_active_only": self._sw_active_only.get(),
            "max_invites_per_run": self._en_rt_max_invites.get_int(),
        })
        _save_cfg(self.cfg)
        self._set_status("Royal Thief settings saved")

    def _save_stamina(self) -> None:
        items = [s.strip() for s in self._en_st_items.get().split(",") if s.strip()]
        self.cfg.setdefault("stamina", {}).update({
            "enabled": self._sw_stamina.get(),
            "check_interval_minutes": self._en_st_interval.get_int(),
            "min_stamina": self._en_st_min.get_int(),
            "preferred_items": items,
        })
        _save_cfg(self.cfg)
        self._set_status("Stamina settings saved")

    def _save_alliance(self) -> None:
        self.cfg.setdefault("alliance_helper", {}).update({
            "enabled": self._sw_helper.get(),
            "check_interval_minutes": self._en_h_interval.get_int(),
        })
        _save_cfg(self.cfg)
        self._set_status("Alliance helper settings saved")

    def _save_resources(self) -> None:
        types = [s.strip() for s in self._en_rc_types.get().split(",") if s.strip()]
        self.cfg.setdefault("resource_collector", {}).update({
            "enabled": self._sw_resources.get(),
            "check_interval_minutes": self._en_rc_interval.get_int(),
            "march_preset": self._om_rc_preset.get(),
            "max_marches_per_run": self._en_rc_max.get_int(),
            "pan_map": self._sw_rc_pan.get(),
            "resource_types": types,
        })
        _save_cfg(self.cfg)
        self._set_status("Resource collector settings saved")

    def _save_settings(self) -> None:
        self.cfg.setdefault("adb", {})["device"] = self._en_device.get().strip()
        self.cfg.setdefault("logging", {})["level"] = self._om_log_level.get()
        _save_cfg(self.cfg)
        self._set_status("Settings saved")

    # ── Misc ──────────────────────────────────────────────────────────────

    def _panel(self, tab: ctk.CTkFrame) -> ctk.CTkScrollableFrame:
        """Scrollable panel that fills a tab."""
        f = ctk.CTkScrollableFrame(tab)
        f.pack(fill="both", expand=True, padx=4, pady=4)
        f.grid_columnconfigure(0, weight=1)
        return f

    def _set_status(self, msg: str) -> None:
        self._status_lbl.configure(text=msg)

    def _on_close(self) -> None:
        if self._bot:
            self._bot.running = False
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    app = EvonyBotGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
