# OmniScreen: Cross-Device Screen Time Intelligence System

OmniScreen is a privacy-first, local-network cross-device screen time intelligence platform designed around the **"Three Independent Engines + Reality Hub"** decoupled architecture.

Designed to Apple Human Interface Guidelines standards with Cupertino dark aesthetics, OmniScreen collects real screen state intervals directly from verified OS APIs and synchronizes timestamped intervals over local Wi-Fi to an idempotent SQLite engine running on your PC.

Strict Architectural Principles:
- Zero Fake Data: No simulated profiles, mock intervals, or synthetic seed records. All analytics derive strictly from native OS APIs.
- Interval-Based Mathematics: Exact UNIX timestamp intervals (start_ts, end_ts) allow mathematical interval unions (True Combined Exposure) and intersections (Second-Screening Overlap).
- Second-Screening Index (SSI): Measures cognitive attention fragmentation caused by simultaneous multi-screen use.
- Zero-Configuration 1-Tap Pairing: UDP broadcast beacon auto-detects your PC Hub in under 100ms without manually typing IP addresses.
- Native Hardware-Accelerated Desktop Experience: Hardware-accelerated Apple dark dashboard operating smoothly at 60/120 FPS.
- Local Offline QR Pairing: QR code generated dynamically on-device with zero external cloud dependencies.
- In-UI Modals: Replaces browser popups with glassmorphic Cupertino modal dialogs for device renaming and deletion.
- Local Network Isolation: All telemetry stays on your local Wi-Fi network. No cloud accounts, external telemetry, or subscription servers.

---

## Architecture

```text
+-----------------------+     +------------------------+     +------------------------+
| Engine A: Windows PC  |     | Engine B: Android App  |     | Engine C: Smart TV/iOS |
| ctypes & psutil polls |     | Native UsageStats API  |     | TCP Port Ping & Webhook|
+-----------+-----------+     +-----------+------------+     +-----------+------------+
            |                             |                              |
            | (Loopback HTTP)             | (Local Wi-Fi POST)           | (LAN TCP / POST)
            +----------------------+      |      +-----------------------+
                                   |      |      |
                                   v      v      v
                       +---------------------------------------+
                       |   OmniScreen Reality Hub (Port 8765)  |
                       | - FastAPI + Uvicorn 0.0.0.0:8765      |
                       | - UDP Discovery Beacon (Port 8766)    |
                       | - SQLite WAL Database (omniscreen.db) |
                       | - Sweep-Line Interval Union Engine    |
                       | - Two-Pointer Overlap Intersector     |
                       | - Local Dynamic QR Generator (/api/qr)|
                       +-------------------+-------------------+
                                           |
                                           v
                       +---------------------------------------+
                       |     Apple macOS Desktop App Window    |
                       | - Hardware-Accelerated Direct3D/Blink |
                       | - SVG Radial Activity Gauge           |
                       | - Cognitive SSI Fragmentation Monitor |
                       | - In-UI Cupertino Glassmorphic Modals |
                       +---------------------------------------+
```

---

## Directory Structure

```text
omniscreen_v2/
|-- hub/
|   |-- dashboard.py         # Apple macOS Sequoia & iOS Screen Time HTML5/CSS3 interface
|   |-- database.py          # SQLite storage with idempotent interval replacement & WAL
|   |-- discovery.py         # UDP Auto-Discovery beacon responder (Port 8766)
|   |-- overlap.py           # Sweep-line union, intersection math & SSI fragmentation model
|   `-- server.py            # FastAPI ingestion, analytics, local QR, and TV endpoints
|-- agents/
|   |-- win32_agent.py       # Engine A: Native Windows ctypes active & idle tracker
|   `-- tv_sensor.py         # Engine C: Local network Smart TV port presence sensor
|-- android_agent/           # Engine B: Standalone Gradle Android project (Apple iOS UI)
|   |-- .github/workflows/
|   |   `-- build_apk.yml    # Automated cloud build workflow for GitHub Actions
|   |-- app/
|   |   |-- src/main/AndroidManifest.xml
|   |   `-- src/main/java/com/omniscreen/agent/
|   |       |-- MainActivity.kt   # iOS Screen Time UI, 1-tap UDP Auto-Detect, custom naming
|   |       |-- UsageExtractor.kt # Digital Wellbeing-grade screen-on extractor
|   |       `-- HubSyncWorker.kt  # Persistent device ID, stable sync, HttpURLConnection
|   |   `-- build.gradle.kts      # App module configuration (compileSdk 34)
|   |-- gradle/wrapper/           # Official Gradle wrapper binaries
|   |-- build.gradle.kts          # Root Gradle build script
|   |-- settings.gradle.kts       # Project repositories and configuration
|   `-- gradlew / gradlew.bat     # Gradle wrapper executables
|-- ui/
|   `-- widget.py            # Apple Dark Mode floating Tkinter widget (async non-blocking)
|-- tests/
|   |-- test_api.py          # API route tests with isolated test DB, QR & device fleet
|   |-- test_database.py     # Idempotent replacement verification
|   |-- test_discovery.py    # UDP Auto-Discovery verification test
|   `-- test_overlap.py      # Union and intersection mathematical tests
|-- config.json              # Smart TV IP and port configuration
|-- main.py                  # Master launcher (Hub + Discovery + Agents + App Window)
|-- run.bat                  # 1-click Windows startup script
|-- stop.bat                 # 1-click process shutdown script
|-- OmniScreenAgent.apk      # Compiled installable Android APK (Apple iOS styling)
|-- requirements.txt         # Python dependencies
`-- README.md                # System documentation
```

---

## Quick Start Guide

### Step 1: Start the PC Reality Hub

Double-click `run.bat` in `omniscreen_v2/` (or run in PowerShell):

```powershell
cd C:\Users\Aditya\.gemini\antigravity\scratch\omniscreen_v2
.\.venv\Scripts\python.exe main.py
```

The launcher initializes the SQLite storage, starts the UDP Auto-Discovery beacon on port 8766, launches the Win32 tracker and Smart TV sensor, and opens the native Apple desktop application window.

### Step 2: Install the Mobile App on Android

The pre-compiled APK is already placed in your workspace:
[`omniscreen_v2/OmniScreenAgent.apk`](file:///C:/Users/Aditya/.gemini/antigravity/scratch/omniscreen_v2/OmniScreenAgent.apk)

1. Transfer `OmniScreenAgent.apk` to your phone and install it.
2. Open **OmniScreen Agent** on your phone.
3. Tap **Grant Usage Access**:
   - If on Android 13/14 and the toggle says *"Restricted setting"*: Open phone **Settings** -> **Apps** -> **OmniScreen Agent** -> tap the **three dots** in the top-right corner -> tap **Allow restricted settings** -> enter your PIN. Return to the app and grant Usage Access.
4. Set your preferred **Device Display Name** (e.g. "Aditya's Galaxy", "Personal Phone") right at the top of the screen.

---

## 1-Tap Zero-Configuration Pairing & Local QR

1. Ensure your phone and PC are connected to the same Wi-Fi network (or phone Mobile Hotspot).
2. **Method 1 (1-Tap Auto-Detect):** In the Android app, tap **Auto-Detect PC Hub**. The app checks your saved address, broadcasts UDP probes across all Wi-Fi and Hotspot interfaces (port 8766), and falls back to a parallel TCP port 8765 subnet sweep if UDP is blocked by a firewall.
3. **Method 2 (Camera QR Pairing):** Click **+ Pair Mobile** on the PC dashboard. Scan the locally generated QR code with your phone's standard camera app to open `http://<LAN_IP>:8765/pair`, then tap **Open & Pair OmniScreen App** to auto-fill your PC address and sync immediately.
4. Tap **Sync Reality to PC Now** anytime to update your daily timeline.

---

## Second-Screening Index (SSI) & TV Intelligence

OmniScreen measures multi-screen cognitive attention fragmentation:

$$\text{SSI} = \frac{\text{Raw Total} - \text{True Exposure}}{\text{True Exposure}} \times 100\%$$

- **Optimal Focus (<10%):** Low simultaneous screen use. Screens are consumed sequentially.
- **Moderate Second-Screening (10% - 25%):** Occasional simultaneous mobile and primary screen use.
- **High Attention Fragmentation (>25%):** Heavy simultaneous multitasking (e.g. scrolling social media while watching TV or working).

---

## Device Fleet Management

From the PC desktop dashboard:
- **Rename:** Click **Rename** on any device row to change its label in a glassmorphic Cupertino modal dialog.
- **Remove:** Click **Remove** to delete a stale or retired device and purge its sessions without browser alerts.
