#!/usr/bin/env python3
"""
Template Capture Utility — Evony Bot

Run this script once (before running the bot) to capture screenshots of each
UI element. The bot uses these images for on-screen recognition.

Usage:
    python capture_templates.py [--device 127.0.0.1:5555]

Workflow for each template:
  1. Navigate inside the game until the element is visible.
  2. Press Enter here — the script takes a screenshot.
  3. Open 'screenshot_preview.png' with any image viewer.
  4. Note the X, Y position and W, H size of the element in pixels.
  5. Enter those values when prompted.
"""

import argparse
import io
import os
import subprocess
import sys

if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

try:
    from PIL import Image
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "Pillow"], check=True)
    from PIL import Image

# Resolve the adb executable the same way the bot does (bundled tools/, PATH…)
try:
    from bot import dependencies as _deps
    _deps.configure()
    ADB = _deps.adb_path()
except Exception:  # noqa: BLE001 — fall back to bare command if anything is off
    ADB = "adb"


# ─── Templates to capture ─────────────────────────────────────────────────────
# (template_name, subdirectory, description of what to show in-game)
TEMPLATES = [
    # ── Screen indicators ─────────────────────────────────────────────────────
    # Capture a small, unique UI element that is ONLY visible on that screen.
    # The bot uses these to detect which screen is currently showing.
    ("city_indicator",          "ui",       "A small element ONLY on the city screen — e.g. the resource bar icons (gold/food) at the top"),
    ("world_map_indicator",     "ui",       "A small element ONLY on the world map — e.g. the mini-map or coordinate bar (X:NNNN Y:NNNN) at the bottom"),
    ("alliance_chat_header",    "ui",       "The 'Alliance' or chat panel title/header bar"),
    ("inventory_header",        "ui",       "The 'Use Item' or inventory panel title — the gold/brown header bar at the top"),
    ("rally_setup_header",      "ui",       "The title bar of the rally attack setup screen"),

    # ── Navigation buttons ────────────────────────────────────────────────────
    ("city_button",             "ui",       "The button that returns you to your city (castle icon, usually bottom-left area)"),
    ("world_map_button",        "ui",       "The World Map button — bottom-left of the city screen"),
    ("alliance_chat_button",    "ui",       "The Alliance button — bottom-right of the main screen"),
    ("inventory_button",        "ui",       "The Items / Inventory bag icon — opens the Use Item panel"),
    ("close_button",            "ui",       "The × or back arrow used to close/dismiss panels"),
    ("confirm_button",          "ui",       "Generic green OK / Confirm / Yes button"),

    # ── Coordinate jump (world map) ───────────────────────────────────────────
    ("goto_coords_button",      "ui",       "The magnifying-glass or search icon to jump to specific coordinates on the world map"),
    ("coords_x_field",          "ui",       "The X coordinate input field in the jump-to-coordinates dialog"),
    ("coords_y_field",          "ui",       "The Y coordinate input field"),
    ("goto_confirm_button",     "ui",       "The Go / Confirm button in the jump-to-coordinates dialog"),

    # ── Alliance chat ─────────────────────────────────────────────────────────
    ("chat_input_field",        "ui",       "The text input box at the bottom of the alliance chat"),
    ("chat_send_button",        "ui",       "The Send button (paper-plane icon or 'Send' label) in alliance chat"),

    # ── Truce Agreement (Shield) ──────────────────────────────────────────────
    # In-game name: "Truce Agreement" — shown in Items > Use Item panel.
    # The active truce appears as a blue translucent dome over your city.
    ("shield_icon",             "ui",       "The blue translucent DOME over your city indicating an active Truce Agreement — capture this on the city screen"),
    ("shield_expired",          "ui",       "Your city WITHOUT the blue dome (no active Truce Agreement) — capture the city screen when unprotected"),
    ("use_item_button",         "ui",       "The green 'Use' button on the RIGHT side of each item row in the Use Item panel"),
    ("shield_item_8h",          "shields",  "The '8 Hour Truce Agreement' item icon (purple gem icon) in the Use Item panel"),
    ("shield_item_24h",         "shields",  "The '24 Hour Truce Agreement' item icon (orange/gold gem icon) in the Use Item panel"),
    ("shield_item_3d",          "shields",  "The '3 Day Truce Agreement' item icon (blue/purple gem icon) in the Use Item panel"),
    ("shield_item_7d",          "shields",  "The '7 Day Truce Agreement' item icon (white/dove icon) in the Use Item panel"),

    # ── Alliance War / Monster War ────────────────────────────────────────────
    ("alliance_war_button",     "ui",       "The Alliance War button on the city screen (sword/shield icon) that opens the Alliance War panel"),
    ("monster_war_tab",         "ui",       "The 'Monster War' sub-tab inside the Alliance War panel — tap this to see monster rally cards"),

    # ── Events / Royal Thief ──────────────────────────────────────────────────
    ("events_button",           "ui",       "The Events / Activities button on the city screen — opens the list of active events"),
    ("royal_thief_event",       "ui",       "The 'Royal Thief' entry in the events list — capture the event banner/icon"),
    ("royal_thief_header",      "ui",       "The header bar of the Royal Thief event screen — confirms the panel opened"),
    ("royal_thief_invite_button","ui",      "The 'Invite' button inside the Royal Thief panel (not per-player — the general invite action)"),
    ("active_player_indicator", "ui",       "The green online dot or 'Active' badge shown next to a player's name in the invite list"),
    ("player_invite_button",    "ui",       "The per-player 'Invite' button in the Royal Thief or alliance member list"),

    # ── Daily Tasks ───────────────────────────────────────────────────────────
    ("daily_tasks_button",      "ui",       "The Daily Tasks / Daily Quests button on the city screen (usually a scroll or star icon)"),
    ("daily_tasks_header",      "ui",       "The header bar of the Daily Tasks panel — confirms it opened"),
    ("task_claim_button",       "ui",       "The green 'Claim' button on a completed task row — there may be several in the list"),
    ("task_claim_all_button",   "ui",       "The 'Claim All' button at the top of the Daily Tasks panel (not all game versions have this)"),
    ("task_go_button",          "ui",       "The 'Go' button on an incomplete task row — navigates you to where that task is done"),

    # ── Stamina ───────────────────────────────────────────────────────────────
    ("stamina_icon",            "ui",       "The stamina icon (lightning bolt or flame) on the city screen, next to the stamina counter"),
    ("stamina_item_small",      "items",    "Small Stamina Potion / small stamina restore item icon in the Use Item inventory panel"),
    ("stamina_item_medium",     "items",    "Medium Stamina Potion icon in inventory"),
    ("stamina_item_large",      "items",    "Large Stamina Potion icon in inventory"),

    # ── Alliance Help ─────────────────────────────────────────────────────────
    ("alliance_help_button",    "ui",       "The alliance help notification badge — a button with a number showing pending help requests"),
    ("help_all_button",         "ui",       "The 'Help All' button that assists every alliance member's request in one tap"),
    ("individual_help_button",  "ui",       "The per-request 'Help' button when 'Help All' is not present"),

    # ── Resource Gathering (world map) ───────────────────────────────────────────
    # Resource tiles appear on the world map as small terrain icons.
    # Capture each type separately — the bot uses them to find gatherable tiles.
    ("gather_button",           "ui",       "The 'Gather' option in the action menu that appears when you tap a resource tile on the world map"),
    ("resource_tile_food",      "resources","A food / flat-land resource tile on the world map (green field icon)"),
    ("resource_tile_wood",      "resources","A lumber / forest resource tile on the world map (tree icon)"),
    ("resource_tile_stone",     "resources","A stone / quarry resource tile on the world map (grey rock icon)"),
    ("resource_tile_iron",      "resources","An iron / mine resource tile on the world map (dark ore icon)"),

    # ── Rally ─────────────────────────────────────────────────────────────────
    ("rally_join_button",       "rally",    "The active 'Join' button on a Monster War rally card — NOT the greyed-out 'Joined' state"),
    ("rally_button",            "rally",    "The 'Rally' option in the action menu that pops up when you tap a monster on the map"),
    ("rally_launch_button",     "rally",    "The 'Launch' or 'Start' button that sends the rally — final confirmation step"),
    ("rally_timer_field",       "rally",    "The timer input box on the rally setup screen (how many minutes to keep the rally open)"),
    ("march_preset_button",     "rally",    "Any one march-preset tab (labeled I–VIII) on the Select a Preset screen"),
    ("march_preset_1",          "rally",    "March preset tab #1 (labeled 'I') specifically on the Select a Preset screen"),
    ("march_confirm_button",    "rally",    "The 'March' button at the bottom of the Select a Preset / troop selection screen"),
    ("troop_reset_button",      "rally",    "The 'Reset' button on the troop selection screen — zeros all troop counts at once"),
    ("troop_plus_button",       "rally",    "The '+' button next to a troop type row — adds troops one at a time; capture just the + icon"),
    ("troop_minus_button",      "rally",    "The '−' button next to a troop type row — removes troops; capture just the − icon"),

    # ── Regular monsters (world map, levels 1–23) ─────────────────────────────
    # These are the standard pink/red creature icons with a white dotted ring.
    # Capture each level you want the bot to target — the art changes noticeably
    # at lower levels; higher levels are harder to distinguish so monster_regular
    # acts as the catch-all for anything above level 10.
    ("monster_level_1",         "monsters", "Regular monster Lv.1 icon (small pink/red creature with white dotted ring)"),
    ("monster_level_2",         "monsters", "Regular monster Lv.2 icon"),
    ("monster_level_3",         "monsters", "Regular monster Lv.3 icon"),
    ("monster_level_4",         "monsters", "Regular monster Lv.4 icon"),
    ("monster_level_5",         "monsters", "Regular monster Lv.5 icon"),
    ("monster_level_6",         "monsters", "Regular monster Lv.6 icon"),
    ("monster_level_7",         "monsters", "Regular monster Lv.7 icon"),
    ("monster_level_8",         "monsters", "Regular monster Lv.8 icon"),
    ("monster_level_9",         "monsters", "Regular monster Lv.9 icon"),
    ("monster_level_10",        "monsters", "Regular monster Lv.10 icon"),
    ("monster_regular",         "monsters", "Any regular monster above Lv.10 — capture a Lv.11+ icon as the catch-all"),

    # ── Event monsters ────────────────────────────────────────────────────────
    # Each event type has distinct art across all its levels.  Capture one icon
    # for each type; the bot reads the actual level from the info popup via OCR.
    ("monster_hydra",           "monsters", "Hydra event monster icon on the world map (Lv.1–6, blue sea-serpent appearance)"),
    ("monster_ymir",            "monsters", "Ymir event monster icon (Lv.1–6, large ice-giant silhouette)"),
    ("monster_cerberus",        "monsters", "Cerberus event monster icon (Lv.1–5, three-headed dog)"),
    ("monster_golem",           "monsters", "Ancient/Event Golem monster icon (Lv.1–7, stone construct — distinct from regular Stone Golems)"),
    ("monster_witch",           "monsters", "Dark/Evil Witch event monster icon (Lv.1–7, purple witch figure)"),

    # ── Summoned monsters ─────────────────────────────────────────────────────
    ("monster_summoned",        "monsters", "Summoned monster icon — capture any summoned monster as the generic template for this type"),

    # ── Shared ────────────────────────────────────────────────────────────────
    ("monster_generic",         "monsters", "Ultimate fallback — any monster icon not matched by the templates above"),
    ("monster_info_popup",      "monsters", "The popup card that appears when you tap a monster (shows name, level, coordinates)"),
]


# ─── ADB helpers ──────────────────────────────────────────────────────────────

def adb_connect(device: str) -> bool:
    r = subprocess.run([ADB, "connect", device], capture_output=True, text=True, timeout=10)
    return "connected" in r.stdout.lower()


def adb_screenshot(device: str) -> Image.Image | None:
    r = subprocess.run(
        [ADB, "-s", device, "exec-out", "screencap", "-p"],
        capture_output=True, timeout=15,
    )
    if r.returncode == 0 and r.stdout:
        return Image.open(io.BytesIO(r.stdout))
    return None


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="127.0.0.1:5555")
    args = parser.parse_args()

    print("\n" + "=" * 62)
    print("  Evony Bot — Template Capture Utility")
    print("=" * 62)
    print(f"  Connecting to: {args.device}")

    if not adb_connect(args.device):
        sys.exit(
            "\nERROR: Could not connect to ADB device.\n"
            "Make sure your emulator is running and ADB debugging is on.\n"
            "Then re-run: python capture_templates.py --device <address>"
        )
    print("  Connected!\n")

    print("  For each template you will:")
    print("    1. Navigate in-game so the element is visible")
    print("    2. Press Enter — a screenshot is saved as screenshot_preview.png")
    print("    3. Open that image and find the element's pixel coordinates")
    print("    4. Type X  Y  W  H  (or just Enter to skip)\n")
    print("=" * 62 + "\n")

    captured = skipped = 0

    for name, subdir, description in TEMPLATES:
        out_path = os.path.join("templates", subdir, f"{name}.png")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # Skip already-captured unless user wants to redo
        if os.path.exists(out_path):
            ans = input(f"[EXISTS] {name}  — recapture? (y/N): ").strip().lower()
            if ans != "y":
                skipped += 1
                continue

        print(f"\n  ┌─ {name}")
        print(f"  │  Category   : {subdir}")
        print(f"  │  Show this  : {description}")
        print(f"  └─ ", end="", flush=True)
        input("Press Enter when element is visible…")

        img = adb_screenshot(args.device)
        if img is None:
            print("     Screenshot failed — skipping")
            skipped += 1
            continue

        img.save("screenshot_preview.png")
        print(f"     Screenshot saved  ({img.width} × {img.height} px)")
        print("     Open screenshot_preview.png and find the element's region.\n")

        try:
            x_str = input("     X (or Enter to skip): ").strip()
            if not x_str:
                print("     Skipped.")
                skipped += 1
                continue
            x = int(x_str)
            y = int(input("     Y: ").strip())
            w = int(input("     W (width): ").strip())
            h = int(input("     H (height): ").strip())
        except (ValueError, EOFError):
            print("     Invalid input — skipped.")
            skipped += 1
            continue

        cropped = img.crop((x, y, x + w, y + h))
        cropped.save(out_path)
        print(f"     Saved → {out_path}  ({w}×{h} px)")
        captured += 1

    print(f"\n{'=' * 62}")
    print(f"  Done.  Captured: {captured}   Skipped: {skipped}")
    print(f"  Templates folder: templates/")
    print(f"\n  Run the bot with:  python main.py")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
