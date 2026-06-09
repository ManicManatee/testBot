# 👑 Evony Bot — Because Your Kingdom Shouldn't Require Your Presence

> *"The best ruler is one whose subjects don't notice they're being governed by a Python script."*

You've built the walls. You've trained the troops. You've stared at the same world map tile for 45 minutes waiting for a level 4 monster to not move. **Enough.** Let the bot do it.

Evony Bot is a Windows automation tool for **Evony: The King's Return** that handles the tedious stuff — shield refreshes, monster rallies, scouting, daily tasks, stamina, alliance help, resource collection, Royal Thief invites — so you can get back to doing literally anything else with your life.

---

## ✨ What It Does

| Feature | What it means in practice |
|---|---|
| **Truce Agreement Monitor** | Checks your Truce Agreement timer and quietly uses a new one before enemies notice you're unprotected. Basically a babysitter for your city walls. |
| **Rally Joiner** | Opens the Alliance War → Monster War tab, spots active rally cards, and joins them by dispatching exactly **1 troop**. You get the kill credit; you spend nothing meaningful. |
| **Rally Starter** | Finds monsters on the map and launches rally attacks with your configured troop preset. The bot has more initiative than most alliance members. |
| **Monster Scanner** | Scans the world map, reads monster coordinates via OCR, and posts them to alliance chat. Your allies will think you never sleep. You won't correct them. |
| **Daily Tasks** | Opens the Daily Tasks panel and claims every completed reward. Optionally taps "Go" on incomplete tasks to kick them off. Never leave free loot on the table again. |
| **Royal Thief Invites** | Checks for an active Royal Thief event and sends rally invitations to online alliance members. The bot is more social than you are. |
| **Stamina Manager** | Reads your stamina counter and uses a restore item from inventory before it hits zero. Monsters don't stop spawning because you forgot to restock. |
| **Alliance Helper** | Detects pending alliance help requests and taps "Help All" instantly. Your alliance will wonder how you're always the first to help. |
| **Resource Collector** | Scans the world map for food, wood, stone, and iron tiles, then sends gathering marches to fill them. Pans the map to find more tiles until your march slots are full. Wood and food don't collect themselves. |

All features are configurable — enable only what you want, tune the intervals, and adjust thresholds. Everything lives in a plain `config.yaml` file you can edit with Notepad.

---

## 🖥️ GUI Manager

A dark-themed control panel (`EvonyBot.exe`) with live log output, per-feature toggles, stat cards, and a template status panel. No command line required unless you're into that kind of thing.

**Tabs:** Dashboard · Shield · Rally Joiner · Rally Starter · Scanner · Daily Tasks · Royal Thief · Stamina · Alliance · Resources · Templates · Settings

**Dashboard stat cards:** Shield timer · Rallies Joined · Monsters Found · Uptime · Tasks Claimed · RT Invites Sent · Alliance Helps · Resources Runs

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
Reads text from the screen (shield timers, monster coordinates, stamina counters, etc.).

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

**This is a one-time setup. Takes about 20–30 minutes.**

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

### Templates You'll Need to Capture (~55 total)

| Category | Examples |
|---|---|
| **UI Navigation** | City indicator, world map indicator, city/map/chat/inventory buttons, close button, confirm button |
| **Truce Agreements** | 8h / 24h / 3-day / 7-day Truce Agreement icons in the Use Item panel; the green "Use" button |
| **Alliance War** | Alliance War button, Monster War tab, Join button on rally cards |
| **Rally** | Rally option menu, Launch button, march preset tabs (I–VIII), troop Reset/+/− buttons, March button |
| **Regular Monsters** | Level 1–10 individual icons + a generic catch-all for Lv.11–23; the info popup |
| **Event Monsters** | One icon per type: Hydra (Lv.1–6), Ymir (Lv.1–6), Cerberus (Lv.1–5), Golem (Lv.1–7), Witch (Lv.1–7) |
| **Summoned Monsters** | Any summoned monster icon |
| **Daily Tasks** | Daily Tasks button, header, Claim button, Claim All button, Go button |
| **Royal Thief** | Events button, Royal Thief event banner, Invite button, active player indicator, per-player invite button |
| **Stamina** | Stamina icon (lightning bolt), small/medium/large stamina restore items |
| **Alliance Help** | Alliance help badge, Help All button, individual help button |
| **Resources** | "Gather" option in the tile action menu; food / wood / stone / iron tile icons on the world map |

> **Tip:** The tool skips already-captured templates by default. If something stops working, re-run it and just recapture that one template — you don't have to redo everything.

> **Evony terminology tip:** The game calls protection items **"Truce Agreements"** (8 Hour / 24 Hour / 3 Day / 7 Day). The timer is shown as `Remaining Time: HH:MM:SS` in the Use Item panel. The bot reads and parses this format automatically.

---

## ⚙️ Configuration

All settings live in `config.yaml` in the install folder. Edit it with any text editor (there's an "Edit Config" shortcut in the Start Menu).

```yaml
adb:
  device: "127.0.0.1:5555"   # ← change this to match your emulator

shield:
  enabled: true
  check_interval_minutes: 15
  refresh_threshold_minutes: 60
  preferred_shields: [8h, 24h, 3d, 7d]

rally_joiner:
  enabled: true
  check_interval_seconds: 10
  march_preset: "preset_1"
  filters:                       # per-type; set enabled: false to skip a type entirely
    regular:   {enabled: true,  min_level: 1,  max_level: 23}
    hydra:     {enabled: true,  min_level: 1,  max_level: 6}
    ymir:      {enabled: true,  min_level: 1,  max_level: 6}
    cerberus:  {enabled: true,  min_level: 1,  max_level: 5}
    golem:     {enabled: true,  min_level: 1,  max_level: 7}
    witch:     {enabled: true,  min_level: 1,  max_level: 7}
    summoned:  {enabled: false, min_level: 1,  max_level: 99}

rally_starter:
  enabled: true
  march_preset: "preset_1"
  rally_time_minutes: 10
  auto_target_from_scanner: true

monster_scanner:
  enabled: true
  scan_interval_minutes: 30
  auto_share: true
  max_share_per_scan: 5
  filters:                       # same structure as rally_joiner filters
    regular:   {enabled: true,  min_level: 1,  max_level: 23}
    hydra:     {enabled: true,  min_level: 1,  max_level: 6}
    # ... etc

daily_tasks:
  enabled: true
  check_interval_minutes: 60
  claim_only: true             # false = also tap "Go" on incomplete tasks

royal_thief:
  enabled: true
  check_interval_minutes: 30
  invite_active_only: true     # only invite online players
  max_invites_per_run: 5

stamina:
  enabled: true
  check_interval_minutes: 15
  min_stamina: 10              # use a restore item when below this
  preferred_items: [small, medium, large]

alliance_helper:
  enabled: true
  check_interval_minutes: 20

resource_collector:
  enabled: true
  check_interval_minutes: 30
  resource_types: [food, wood, stone, iron]
  march_preset: "preset_2"         # keep this separate from your combat preset
  max_marches_per_run: 5           # stops when march queue is full anyway
  pan_map: true                    # pan the world map to find more tiles
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
├── gui.py                    # GUI manager (the thing you launch)
├── main.py                   # Headless CLI entry point
├── capture_templates.py      # Template capture wizard
├── config.yaml               # All your settings live here
├── requirements.txt          # Python dependencies
│
├── bot/
│   ├── adb_controller.py     # ADB: screenshot, tap, swipe, type
│   ├── screen_reader.py      # OpenCV template matching + OCR
│   ├── navigator.py          # Screen-state machine (city/map/chat/inventory)
│   ├── shield_manager.py     # Truce Agreement check + auto-renewal
│   ├── rally_joiner.py       # Join monster rallies with 1 troop
│   ├── rally_starter.py      # Launch rally attacks from scanner results
│   ├── monster_scanner.py    # Scan world map + share to alliance chat
│   ├── daily_tasks.py        # Claim daily task rewards
│   ├── royal_thief.py        # Send Royal Thief event invites
│   ├── stamina_manager.py    # Auto-restore stamina from inventory
│   ├── alliance_helper.py    # Help All alliance requests
│   └── resource_collector.py # Harvest resource buildings
│
├── templates/                # Your captured UI screenshots go here
│   ├── ui/
│   ├── shields/
│   ├── monsters/
│   ├── rally/
│   └── items/
│
├── logs/                     # Rotating log files
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

**Truce Agreement manager doesn't trigger**
The bot navigates to the city, then opens your inventory to read the `Remaining Time: HH:MM:SS` green bar. Make sure `shield_icon` (the blue dome), `inventory_button`, and the `shield_item_Xh/d` templates are all captured.

**Rally joiner joins but sends the wrong troop count**
The joiner always sends exactly 1 troop. If it's sending more, your `troop_reset_button` template probably isn't matching — recapture it. The bot taps Reset first, then `+` once.

**Daily Tasks panel doesn't open**
Recapture `daily_tasks_button`. Its position varies between game versions and server types.

**Royal Thief event not detected**
The bot only acts when it can see the `royal_thief_event` banner in the Events panel. If the event isn't running, it skips silently — that's expected. If it IS running and being missed, recapture the banner template.

**Stamina never restores**
Check that `stamina_icon` is captured (gives the bot an anchor for OCR). Also verify you have stamina restore items in your inventory and that `stamina_item_small/medium/large` templates are captured for the sizes you own.

**Resource collector sends 0 marches**
1. Make sure `gather_button` is captured — this is the "Gather" option in the tile action menu, not a building button
2. Capture at least one resource tile template (`resource_tile_food`, `resource_tile_wood`, etc.) for the types you enabled in config
3. The bot stops early if the march queue is full — that's intentional; it will retry next check interval

**pip install failed during setup**
Run it manually from the install folder:
```bash
cd "C:\Program Files\EvonyBot"
pip install -r requirements.txt
```

---

## 📄 License

Do whatever you want with this. Just don't use it to ruin anyone else's fun. And maybe share your monsters with the alliance — that's literally one of the features.
