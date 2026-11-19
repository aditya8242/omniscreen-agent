# Contributing to OmniScreen

Thank you for your interest in contributing to OmniScreen.
OmniScreen is an open-source, local-first cross-device screen time platform licensed under the GNU General Public License v3.0 (GPL-3.0). Contributions of all kinds—bug fixes, architectural enhancements, native OS sensors, documentation, and UI refinements—are welcome.

---

## Who Can Contribute?
- Python developers interested in systems programming, Win32 APIs, FastAPI, or interval mathematics.
- Android developers experienced with Kotlin, Jetpack, UsageStats/UsageEvents, or AppWidgets.
- Systems and frontend engineers interested in local-first, zero-cloud software architecture.
- Anyone looking to improve documentation, test coverage, or multi-platform support (macOS, Linux).

---

## Getting Started

1. Fork the repository:
   Click **Fork** on `https://github.com/aditya8242/omniscreen-agent`.

2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/omniscreen-agent.git
   cd omniscreen-agent
   ```

3. Create a descriptive feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## Environment Setup & Running Locally

### 1. Python Reality Hub (PC Engine)
Prerequisites: Python 3.11+

```bash
# Create and activate virtual environment
python -m venv .venv

# On Windows:
.\.venv\Scripts\activate

# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the automated test suite
pytest tests/

# Launch the PC Hub
python main.py
```

The desktop Reality Hub runs locally at `http://127.0.0.1:8765`.

### 2. Android Agent (Mobile Engine)
Prerequisites: Android Studio / JDK 17

```bash
cd android_agent

# Run Android unit tests
./gradlew test

# Build debug APK
./gradlew assembleDebug

# Build release APK
./gradlew assembleRelease
```

---

## Core Architectural Principles

All contributions must strictly respect OmniScreen's local-first privacy guarantees:
1. **Zero External Cloud Telemetry:** Telemetry must never leave the user's local network. Never integrate third-party analytics SDKs, cloud trackers, or mandatory remote servers.
2. **Interval-Based Mathematics:** Screen events must be recorded as discrete timestamp intervals `[start_ts, end_ts]`. Never perform naive summation of raw daily minutes.
3. **Host-Locked Administration:** Destructive API endpoints (device deletion, database clearing, shutdown) must remain strictly restricted to localhost (`127.0.0.1`).

---

## Code Guidelines
- **Python:** Follow PEP 8 conventions. Maintain type annotations on public functions and keep methods focused.
- **Kotlin:** Follow standard Kotlin coding conventions. Ensure Android background workers run without excessive battery drain.
- **Testing:** Add or update unit tests in `tests/` for any new backend, calculation, or database logic. All tests must pass before submitting a pull request:
  ```bash
  pytest tests/
  ```

---

## Submitting a Pull Request

1. Commit your changes with a clear, structured commit message (e.g., `feat(hub): add export endpoint` or `fix(win32): handle session gap on hibernate`).
2. Push your feature branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
3. Open a Pull Request on GitHub against the `master` branch.
4. Clearly describe:
   - What changes were introduced.
   - Which operating systems or components were tested.
   - Any breaking changes or schema migrations.

---

## Need Help?
- Open an Issue on GitHub for bugs, architecture discussions, or feature suggestions.
- Ask questions directly within Pull Request discussions.
