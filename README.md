# OmniScreen

<p align="center">
  <strong>Local-first cross-device screen time intelligence for Windows and Android.</strong><br>
  Exact timestamp interval union mathematics. Zero cloud telemetry. 100% open source.
</p>

<p align="center">
  <a href="https://github.com/aditya8242/omniscreen-agent/releases/latest"><img src="https://img.shields.io/github/v/release/aditya8242/omniscreen-agent?color=0A84FF&label=Release" alt="Latest Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0-30D158.svg" alt="License: GPL-3.0"></a>
  <a href="https://github.com/aditya8242/omniscreen-agent/actions"><img src="https://img.shields.io/github/actions/workflow/status/aditya8242/omniscreen-agent/ci.yml?branch=master&label=CI" alt="Build Status"></a>
  <a href="https://getomniscreen.vercel.app"><img src="https://img.shields.io/badge/Website-getomniscreen.vercel.app-0A84FF" alt="Live Website"></a>
  <a href="https://www.virustotal.com/gui/file/30e6e335686682a15d28e7228a193bab2b833a39e9efb6d905389e5a98c4520f/detection"><img src="https://img.shields.io/badge/VirusTotal-Verified%20Clean-30D158" alt="VirusTotal Verified Clean"></a>
</p>

---

## The Problem With Modern Screen Time

Operating systems track your screen time in complete isolation:
- Your smartphone records when you look at your phone.
- Your PC records when you use your desktop.
- Your Smart TV records when the TV is on.

When you glance at your phone while sitting at your laptop, **naive screen time tools add the clocks together**, double-counting your day and hiding when your attention was fragmented.

OmniScreen collects verified UNIX timestamp intervals `[start_ts, end_ts]` from your operating systems and projects them into a continuous timeline over your private local Wi-Fi:
1. **True Combined Exposure:** The exact mathematical interval union ($A \cup B$) across all devices.
2. **Attention Fragmentation Index:** The exact overlap ($A \cap B$) where your attention was divided between multiple screens simultaneously.

All computed on your local machine. No cloud accounts. No external telemetry. No subscriptions.

---

## Downloads (Public Beta v0.9)

Pre-compiled standalone binaries are available directly on the [**Latest GitHub Release**](https://github.com/aditya8242/omniscreen-agent/releases/latest) or on our [**Official Website**](https://getomniscreen.vercel.app):

| Platform | Download Link | Type | Notes |
| :--- | :--- | :--- | :--- |
| **Windows 10 / 11** | [**OmniScreen-Windows-Beta.zip**](https://github.com/aditya8242/omniscreen-agent/releases/latest/download/OmniScreen-Windows-Beta.zip) | Portable ZIP | Zero terminal window, System Tray daemon, sleep gap clamp |
| **Windows 10 / 11** | [**OmniScreen.exe**](https://github.com/aditya8242/omniscreen-agent/releases/latest/download/OmniScreen.exe) | Standalone EXE | Direct x64 executable |
| **Android 8.0 – 15** | [**OmniScreenAgent-release.apk**](https://github.com/aditya8242/omniscreen-agent/releases/latest/download/OmniScreenAgent-release.apk) | Signed APK | Digital Wellbeing parity, Obsidian 4x2 Home Screen Widget |
| **Checksums** | [**checksums.txt**](https://github.com/aditya8242/omniscreen-agent/releases/latest/download/checksums.txt) | SHA-256 | Cryptographic integrity digests |

---

## Architectural Principles

```text
+-----------------------+     +------------------------+     +------------------------+
| Engine A: Windows PC  |     | Engine B: Android App  |     | Engine C: Smart TV     |
| ctypes & psutil polls |     | Native UsageEvents API |     | SSDP Multicast & Ports |
+-----------+-----------+     +-----------+------------+     +-----------+------------+
            |                             |                              |
            | (Loopback HTTP)             | (Local Wi-Fi POST)           | (LAN UDP / TCP)
            +----------------------+      |      +-----------------------+
                                   |      |      |
                                   v      v      v
                       +---------------------------------------+
                       |   OmniScreen Reality Hub (Port 8765)  |
                       | - FastAPI Engine (127.0.0.1:8765)     |
                       | - UDP Discovery Beacon (Port 8766)    |
                       | - SQLite WAL Database (omniscreen.db) |
                       | - Sweep-Line Interval Union Engine    |
                       | - Attention Fragmentation Intersector |
                       | - On-Device Dynamic QR Generator      |
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       |      Obsidian Instrument UI           |
                       | - System Tray Daemon (pystray)        |
                       | - Hardware-Accelerated Webview        |
                       | - Monotonic Tick Gap Sleep Clamp      |
                       | - Windows Lock Screen (Win+L) Pause   |
                       +---------------------------------------+
```

- **Zero Fake Data:** No simulated profiles, synthetic seed records, or guesswork. Telemetry derives strictly from operating system kernel events.
- **Local Network Isolation:** Synchronization occurs directly between devices on your local Wi-Fi network (or mobile hotspot) over LAN HTTP. No data ever leaves your room.
- **Host-Locked Administration:** Destructive API routes (device removal, database purge, TV scans, hub shutdown) are cryptographically restricted to `127.0.0.1` with strict CORS enforcement.
- **Full Data Portability:** Download your entire cross-device session history in RFC 4180 CSV or structured JSON anytime via the dashboard or `/api/export`.

---

## Quick Setup (2 Minutes)

### 1. Windows Setup
1. Extract `OmniScreen-Windows-Beta.zip` and double-click `OmniScreen.exe`.
2. On first launch, Windows SmartScreen may show an unknown publisher dialog (as an unsigned open-source beta). Click **More info &rarr; Run anyway**.
3. OmniScreen opens the Reality Hub dashboard and docks quietly into your Windows System Tray (next to your taskbar clock).

### 2. Android Setup
1. Download and install `OmniScreenAgent-release.apk` on your phone (allow **Install unknown apps**).
2. Tap **Grant Usage Access**:
   - On Android 13/14, if the system shows *Restricted setting*: Open phone **Settings &rarr; Apps &rarr; OmniScreen Agent &rarr; tap the 3 dots (top right) &rarr; Allow restricted settings**, enter your PIN, and grant Usage Access.
3. Tap **Auto-Detect PC Hub** (or tap **+ Pair Mobile** on your PC to scan the local QR code).
4. Tap **Sync Reality to PC Now** anytime to update your timeline.
5. Long-press your phone's home screen and add the **OmniScreen 4x2 Widget** for live daily metrics.

---

## Running From Source (For Developers)

### Prerequisites
- Python 3.11+
- Android Studio / JDK 17 (for Android agent builds)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/aditya8242/omniscreen-agent.git
cd omniscreen-agent
```

### 2. Setup Python Environment
```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Run the Automated Test Suite
```bash
pytest tests/
```

### 4. Start the Development Hub
```bash
python main.py
```

### 5. Build the Android Agent
```bash
cd android_agent
./gradlew assembleRelease
```

---

## Mathematical Foundation

$$\text{True Exposure} = \mu\left(\bigcup_{i=1}^{n} I_i\right)$$

$$\text{Attention Fragmentation Index} = \frac{\sum_{i=1}^{n} \text{Duration}(I_i) - \text{True Exposure}}{\text{True Exposure}} \times 100\%$$

- **Optimal Focus (< 10%):** Screens are consumed sequentially. Single-task cognitive focus.
- **Moderate Multitasking (10% – 25%):** Occasional simultaneous mobile and primary screen use.
- **High Attention Fragmentation (> 25%):** Chronic second-screening (e.g. social scrolling while attending meetings or consuming desktop media).

---

## Security & Independent Verification

Every binary distributed in releases is cryptographically hashed and scanned across independent antivirus engines:

- **Android APK:** 0/66 Detections on VirusTotal (100% clean).
- **Windows Executable:** 68/71 Clean on VirusTotal (Microsoft Defender, Google, Bitdefender, Malwarebytes, Kaspersky verified clean; 3 generic unsigned PyInstaller heuristic flags).
- **Source Code Integrity:** Reviewable by anyone under the GNU General Public License v3.0.

---

## Roadmap

- [x] Windows 10/11 Win32 background agent with sleep and lock-screen detection
- [x] Android raw `UsageEvents` extractor matching Digital Wellbeing
- [x] Native 4x2 Obsidian Home Screen Widget for Android
- [x] SSDP Multicast and local port Smart TV presence sensor
- [x] Fast sweep-line interval union and fragmentation mathematics
- [x] Idempotent local SQLite storage with WAL mode
- [x] CSV and JSON raw session export engine with date range filtering (#3)
- [ ] **OmniLock:** Open-source cross-device synchronized focus enforcement protocol
- [ ] Native macOS (Quartz/CoreGraphics) foreground agent
- [ ] Native Linux (X11/Wayland) foreground agent
- [ ] F-Droid official repository submission for Android

---

## Contributing

Contributions are welcome! Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) for local environment setup, testing, and pull request procedures.

---

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.  
See the [`LICENSE`](LICENSE) file for details.
