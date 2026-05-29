# 👑 Evony Bot — Because Your Kingdom Shouldn't Require Your Presence

> *"The best ruler is one whose subjects don't notice they're being governed by a Python script."*

You've built the walls. You've trained the troops. You've stared at the same world map tile for 45 minutes waiting for a level 4 monster to not move. **Enough.** Let the bot do it.

Evony Bot is a Windows automation tool for **Evony: The King's Return** that handles the tedious stuff — shield refreshes, monster rallies, scouting — so you can get back to doing literally anything else with your life.

---

## ✨ What It Does

| Feature | What it means in practice |
|---|---|
| **Shield Monitor** | Checks your shield timer and quietly uses a new one before enemies notice you're unprotected. Basically a babysitter for your city walls. |
| **Rally Joiner** | Spots monster rally invites in alliance chat and joins them automatically. You get the glory; the bot does the commute. |
| **Rally Starter** | Finds monsters on the map and launches rally attacks with your configured troop preset. The bot has more initiative than most alliance members. |
| **Monster Scanner** | Scans the world map, reads monster coordinates via OCR, and posts them to alliance chat. Your allies will think you never sleep. You won't correct them. |

All features are configurable — enable only what you want, tune the intervals, filter by monster level, and pick your march preset. Everything lives in a plain `config.yaml` file you can edit with Notepad.

---

## 🖥️ GUI Manager

A dark-themed control panel (`EvonyBot.exe`) with live log output, per-feature toggles, stat cards, and a template status panel. No command line required unless you're into that kind of thing.

![Tabs: Dashboard · Shield · Rally Joiner · Rally Starter · Scanner · Templates · Settings]

---

## 📋 Prerequisites

Before installing the bot you need two free tools. The installer will remind you, but here they are:

### 1. Android Platform Tools (ADB)
The bot talks to your emulator over ADB.

1. Download from [developer.android.com/tools/releases/platform-tools](https://developer.android.com/tools/releases/platform-tools)
2. Extract the zip anywhere (e.g. `C:\platform-tools\`)
3. Add that folder to your **system PATH**
   - Search → "Edit the system environment variables" → Environment Variables → Path → New
4. Open a new terminal and verify: `adb version`

### 2. Tesseract OCR
Reads text from the screen (shield timers, monster coordinates, etc.).

1. Download the Windows installer from [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
2. Run it — the default install path (`C:\Program Files\Tesseract-OCR\`) is fine
3. No PATH setup needed; pytesseract finds it automatically

### 3. A Supported Android Emulator
The bot connects to your emulator via ADB. Any of these work:

| Emulator | Default ADB address |
|---|---|
| BlueStacks 5 | `127.0.0.1:5555` |
| LDPlayer | `127.0.0.1:5554` |
| MuMu Player | `127.0.0.1:7555` |
| NoxPlayer | `127.0.0.1:62001` |

---

## 📦 Installation

### Option A — Windows Installer (recommended)

1. Grab `EvonyBot_Setup_v1.0.0.exe` from [`windows_installers/v1/`](windows_installers/v1/)
2. Run it, click through the wizard
3. The installer will:
   - Copy all bot files to `C:\Program Files\EvonyBot\` (or wherever you choose)
   - Detect your Python installation and run `pip install -r requirements.txt` automatically
   - Create Start Menu shortcuts for the GUI, CLI, and template capture tool
4. Done — launch **Evony Bot** from the Start Menu

> **Note:** The installer needs Python 3.10+ already on your machine. If it's not found, it'll tell you and give you the link. Python is free, takes two minutes.

---

### Option B — Manual (Python already installed)

```bash
# 1. Clone the repo
git clone https://github.com/manicmanatee/testbot.git
cd testbot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the GUI
python gui.py

# or run headless (CLI only)
python main.py
```

---

## 🎨 First-Time Setup — Capture Your Templates

The bot uses image recognition to find buttons and icons on screen. It needs reference screenshots ("templates") of your specific game UI — because resolution, skin, and game version all affect pixel layout.

**This is a one-time setup. Takes about 10–15 minutes.**

### Steps

1. Start your emulator and open Evony
2. Run the template capture tool:
   - **From Start Menu:** Evony Bot → Capture Templates
   - **From installer folder:** double-click `capture_templates.bat`
   - **From source:** `python capture_templates.py`
3. For each template, the tool will:
   - Tell you what UI element to show on screen
   - Take a screenshot when you press Enter (saved as `screenshot_preview.png`)
   - Ask you for the `X  Y  Width  Height` of that element in pixels
   - Save the cropped region as a template PNG
4. Open `screenshot_preview.png` in any image viewer to find the coordinates

### Templates You'll Need to Capture (~30 total)

| Category | Examples |
|---|---|
| **UI Navigation** | Shield icon, city button, world map button, alliance chat button, inventory button, close button |
| **Shields** | 8h shield item, 24h shield item, 3-day shield item (in your inventory) |
| **Rally** | Rally join button, rally attack button, march preset buttons, confirm button |
| **Monsters** | Level 1–5 monster icons on the world map, monster info popup |

> **Tip:** If a template isn't working well, just re-run the capture tool and choose to recapture that one item. The tool skips already-captured templates by default.

---

## ⚙️ Configuration

All settings live in `config.yaml` in the install folder. Edit it with any text editor (there's an "Edit Config" shortcut in the Start Menu).

```yaml
# Which emulator to connect to
adb:
  device: "127.0.0.1:5555"   # ← change this to match your emulator

shield:
  enabled: true
  check_interval_minutes: 15     # check every 15 minutes
  refresh_threshold_minutes: 60  # use a new shield when < 1 hour remains
  preferred_shields: [8h, 24h, 3d]  # try 8h first, then 24h, then 3d

rally_joiner:
  enabled: true
  check_interval_seconds: 10
  march_preset: "preset_1"       # which march preset to send
  filters:
    min_monster_level: 1
    max_monster_level: 5

rally_starter:
  enabled: true
  march_preset: "preset_1"
  rally_time_minutes: 10
  auto_target_from_scanner: true  # rally the monsters the scanner finds

monster_scanner:
  enabled: true
  scan_interval_minutes: 30
  auto_share: true               # post finds to alliance chat
  min_level: 1
  max_level: 5
  max_share_per_scan: 5
```

Changes take effect the next time you start the bot. The GUI's Save buttons also write directly to this file.

---

## 🚀 Running the Bot

### GUI (recommended)
- **Start Menu → Evony Bot**, or double-click `launch_gui.vbs` in the install folder
- Hit **▶ Start Bot** — all settings are auto-saved first
- Watch the live log on the Dashboard tab
- **■ Stop Bot** when you're done

### Headless CLI
```bash
python main.py
# or from the install folder:
launch_cli.bat
```
Logs go to both the console and `logs/evony_bot.log`.

---

## 🗂️ Project Structure

```
EvonyBot/
├── gui.py                  # GUI manager (the thing you launch)
├── main.py                 # Headless CLI entry point
├── capture_templates.py    # Template capture wizard
├── config.yaml             # All your settings live here
├── requirements.txt        # Python dependencies
│
├── bot/
│   ├── adb_controller.py   # ADB: screenshot, tap, swipe, type
│   ├── screen_reader.py    # OpenCV template matching + OCR
│   ├── navigator.py        # Screen-state machine (city/map/chat/inventory)
│   ├── shield_manager.py   # Shield check + auto-renewal
│   ├── rally_joiner.py     # Detect and join rally invites
│   ├── rally_starter.py    # Launch rally attacks
│   └── monster_scanner.py  # Scan map + share to alliance chat
│
├── templates/              # Your captured UI screenshots go here
│   ├── ui/
│   ├── shields/
│   ├── monsters/
│   └── rally/
│
├── logs/                   # Rotating log files
│
└── windows_installers/
    └── v1/
        └── EvonyBot_Setup_v1.0.0.exe
```

---

## 🔧 Building the Installer Yourself

If you want to rebuild the installer after making changes:

**On Windows:**
```bash
pip install -r requirements.txt
choco install innosetup upx -y
python build.py --installer
# → installer/output/EvonyBot_Setup_vX.Y.Z.exe
```

**Via GitHub Actions (any OS):**
Go to **Actions → Build Windows Installer → Run workflow**, enter a version number, and download the artifact when the job finishes. Pushing a `v*` tag triggers a full GitHub Release automatically.

**On Linux (what built this v1):**
```bash
apt install nsis
makensis EvonyBot_Setup.nsi
```

---

## ❓ Troubleshooting

**"adb not found"**
Make sure Android Platform Tools is downloaded and the folder is in your PATH. Restart your terminal after adding it.

**"Template not found" warnings in the log**
A template PNG is missing. Re-run the capture tool and capture that element. The Templates tab in the GUI shows which ones are missing (red ○).

**Bot connects but doesn't do anything**
1. Make sure Evony is the active window in your emulator (not minimized or behind another app)
2. Check that your emulator's ADB address in `config.yaml` matches
3. Enable DEBUG logging to see exactly what the bot is looking for

**Shield manager doesn't trigger**
It only activates when your city view is visible. If you're on the world map when the check runs, it navigates to the city first — make sure the `city_indicator` template is captured.

**pip install failed during setup**
Run it manually from the install folder:
```bash
cd "C:\Program Files\EvonyBot"
pip install -r requirements.txt
```

---

## 📄 License

Do whatever you want with this. Just don't use it to ruin anyone else's fun. And maybe share your monsters with the alliance — that's literally one of the features.
