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

try:
    from PIL import Image
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "Pillow"], check=True)
    from PIL import Image


# ─── Templates to capture ─────────────────────────────────────────────────────
# (template_name, subdirectory, description of what to show in-game)
TEMPLATES = [
    # ── Screen indicators (used to detect which screen is active) ──
    ("city_indicator",          "ui",       "Any element that ONLY appears on the main city screen"),
    ("world_map_indicator",     "ui",       "Any element that ONLY appears on the world map"),
    ("alliance_chat_header",    "ui",       "The header/title bar of the alliance chat panel"),
    ("inventory_header",        "ui",       "The header/title of the inventory/items panel"),
    ("rally_setup_header",      "ui",       "The header/title of the rally configuration screen"),

    # ── Navigation buttons ──
    ("city_button",             "ui",       "Button to return to your city"),
    ("world_map_button",        "ui",       "Button to open the world map"),
    ("alliance_chat_button",    "ui",       "Button to open alliance chat"),
    ("inventory_button",        "ui",       "Button to open inventory / items bag"),
    ("close_button",            "ui",       "The × or close button used to dismiss most panels"),
    ("confirm_button",          "ui",       "Generic OK / Confirm button"),

    # ── Coordinate jump ──
    ("goto_coords_button",      "ui",       "Button to jump to specific coordinates on the world map"),
    ("coords_x_field",          "ui",       "The X coordinate text-input field"),
    ("coords_y_field",          "ui",       "The Y coordinate text-input field"),
    ("goto_confirm_button",     "ui",       "Confirm button after entering coordinates"),

    # ── Alliance chat input ──
    ("chat_input_field",        "ui",       "Text input area inside the alliance chat"),
    ("chat_send_button",        "ui",       "Send / Post button in the alliance chat"),

    # ── Shield ──
    ("shield_icon",             "ui",       "The shield icon on the city screen (active, with timer)"),
    ("shield_expired",          "ui",       "The shield icon when protection has expired (red / grey)"),
    ("use_item_button",         "ui",       "The 'Use' button shown when selecting an item in inventory"),
    ("shield_item_8h",          "shields",  "8-hour shield item tile inside the inventory"),
    ("shield_item_24h",         "shields",  "24-hour shield item tile"),
    ("shield_item_3d",          "shields",  "3-day shield item tile"),

    # ── Rally ──
    ("rally_join_button",       "rally",    "The 'Join' button on a rally invite (notifications or chat)"),
    ("rally_button",            "rally",    "The 'Rally' option that appears when you tap a monster"),
    ("rally_launch_button",     "rally",    "The Launch / Start button on the rally setup screen"),
    ("rally_timer_field",       "rally",    "The timer input field on the rally setup screen"),
    ("march_preset_button",     "rally",    "A single march-preset slot button (capture any one)"),
    ("march_preset_1",          "rally",    "March preset #1 slot specifically"),
    ("march_confirm_button",    "rally",    "Confirm / March button that sends your troops"),

    # ── Monster icons (world map) ──
    ("monster_level_1",         "monsters", "Level 1 monster icon on the world map"),
    ("monster_level_2",         "monsters", "Level 2 monster icon on the world map"),
    ("monster_level_3",         "monsters", "Level 3 monster icon on the world map"),
    ("monster_level_4",         "monsters", "Level 4 monster icon on the world map"),
    ("monster_level_5",         "monsters", "Level 5 monster icon on the world map"),
    ("monster_generic",         "monsters", "Generic / fallback monster icon (any type or level)"),
    ("monster_info_popup",      "monsters", "The info panel that opens when you tap a monster"),
]


# ─── ADB helpers ──────────────────────────────────────────────────────────────

def adb_connect(device: str) -> bool:
    r = subprocess.run(["adb", "connect", device], capture_output=True, text=True, timeout=10)
    return "connected" in r.stdout.lower()


def adb_screenshot(device: str) -> Image.Image | None:
    r = subprocess.run(
        ["adb", "-s", device, "exec-out", "screencap", "-p"],
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
