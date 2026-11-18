import sys
import time
import socket
import logging
import threading
from typing import Optional, List, Dict, Any
import requests

logger = logging.getLogger("Win32Agent")

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes
    from ctypes import Structure, c_uint, sizeof, byref, c_ulong
    import psutil

    class LASTINPUTINFO(Structure):
        _fields_ = [
            ("cbSize", c_uint),
            ("dwTime", c_uint)
        ]

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.GetTickCount.restype = c_uint
else:
    user32 = None
    kernel32 = None
    psutil = None

LOCK_SCREEN_PROCESSES = {
    "lockapp.exe",
    "logonui.exe",
    "screensaver.scr",
}

FRIENDLY_EXE_NAMES = {
    "msedge.exe": "Microsoft Edge",
    "chrome.exe": "Google Chrome",
    "brave.exe": "Brave",
    "firefox.exe": "Firefox",
    "opera.exe": "Opera",
    "arc.exe": "Arc",
    "code.exe": "VS Code",
    "antigravity.exe": "Antigravity",
    "devenv.exe": "Visual Studio",
    "pycharm64.exe": "PyCharm",
    "idea64.exe": "IntelliJ IDEA",
    "windowsterminal.exe": "Terminal",
    "powershell.exe": "PowerShell",
    "pwsh.exe": "PowerShell",
    "cmd.exe": "Command Prompt",
    "explorer.exe": "File Explorer",
    "spotify.exe": "Spotify",
    "discord.exe": "Discord",
    "whatsapp.exe": "WhatsApp",
    "telegram.exe": "Telegram",
    "slack.exe": "Slack",
    "teams.exe": "Microsoft Teams",
    "ms-teams.exe": "Microsoft Teams",
    "zoom.exe": "Zoom",
    "notion.exe": "Notion",
    "obsidian.exe": "Obsidian",
    "vlc.exe": "VLC",
    "steam.exe": "Steam",
    "steamwebhelper.exe": "Steam",
    "winword.exe": "Microsoft Word",
    "excel.exe": "Microsoft Excel",
    "powerpnt.exe": "PowerPoint",
    "notepad.exe": "Notepad",
    "applicationframehost.exe": "Windows App",
}


def resolve_friendly_exe_name(raw_name: str) -> str:
    clean = (raw_name or "").strip()
    if not clean:
        return "System"
    low = clean.lower()
    if low in FRIENDLY_EXE_NAMES:
        return FRIENDLY_EXE_NAMES[low]
    if low.endswith(".exe"):
        clean = clean[:-4]
    if clean.islower():
        clean = clean.capitalize()
    return clean or "System"


class Win32ScreenAgent:
    def __init__(
        self,
        hub_url: str = "http://127.0.0.1:8765",
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        poll_interval: float = 3.0,
        idle_threshold_seconds: float = 300.0,
        flush_interval_seconds: float = 60.0
    ):
        self.hub_url = hub_url.rstrip("/")
        hostname = socket.gethostname()
        self.device_id = device_id or f"pc_{hostname.lower()}"
        self.device_name = device_name or hostname
        self.device_type = "pc"

        self.poll_interval = poll_interval
        self.idle_threshold_sec = idle_threshold_seconds
        self.flush_interval_sec = flush_interval_seconds

        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._http = requests.Session()

        self._current_app: Optional[str] = None
        self._session_start_ts: Optional[float] = None
        self._is_idle: bool = False
        self._last_tick_ts: Optional[float] = None

        # Foreground process cache avoids repeated OpenProcess syscalls while staying in one window
        self._last_hwnd: Optional[int] = None
        self._last_pid: Optional[int] = None
        self._last_raw_exe: str = ""

        self._buffer: List[Dict[str, Any]] = []
        self._last_flush_ts = time.time()

    def _get_idle_seconds(self) -> float:
        if not IS_WINDOWS or not user32 or not kernel32:
            return 0.0
        try:
            info = LASTINPUTINFO()
            info.cbSize = sizeof(LASTINPUTINFO)
            if user32.GetLastInputInfo(byref(info)):
                # 32-bit unsigned difference handles uptime > 24.8 days (Fast Startup / Hibernation)
                millis = (kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF
                return max(0.0, millis / 1000.0)
        except Exception as e:
            logger.debug(f"Error checking idle: {e}")
        return 0.0

    def _is_workstation_locked(self) -> bool:
        """Detects Windows Lock Screen (Win+L) so locked PC time is never counted as active."""
        if not IS_WINDOWS or not user32:
            return False
        try:
            # OpenInputDesktop returns 0 when the secure Lock Screen desktop is active
            hdesk = user32.OpenInputDesktop(0, False, 0x0001)
            if not hdesk:
                return True
            user32.CloseDesktop(hdesk)
            return False
        except Exception:
            return False

    def _get_foreground_window_title(self, hwnd) -> str:
        if not IS_WINDOWS or not user32 or not hwnd:
            return ""
        try:
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return ""
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value or ""
        except Exception:
            return ""

    def _get_foreground_raw_exe(self) -> str:
        if not IS_WINDOWS or not user32 or not psutil:
            return "Windows Workstation"
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                self._last_hwnd = None
                self._last_pid = None
                self._last_raw_exe = ""
                return ""
            pid = c_ulong()
            user32.GetWindowThreadProcessId(hwnd, byref(pid))
            pid_val = pid.value

            # Fast path: same window & PID — reuse cached executable without OpenProcess syscall
            if hwnd == self._last_hwnd and pid_val == self._last_pid and self._last_raw_exe:
                return self._last_raw_exe

            title = self._get_foreground_window_title(hwnd)
            if "omniscreen reality hub" in title.lower():
                raw = "OmniScreen"
            elif pid_val:
                proc = psutil.Process(pid_val)
                raw = proc.name() or ""
            else:
                raw = ""

            self._last_hwnd = hwnd
            self._last_pid = pid_val
            self._last_raw_exe = raw
            return raw
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "System"
        except Exception as e:
            logger.debug(f"Foreground app error: {e}")
        return ""

    def _record_interval(self, app_name: str, start_ts: float, end_ts: float):
        if end_ts - start_ts < 1.0:
            return
        r_start = round(start_ts, 2)
        r_end = round(end_ts, 2)
        with self._lock:
            # Coalesce contiguous same-app slices (<=2s gap) to keep SQLite compact
            if (
                self._buffer
                and self._buffer[-1]["app_name"] == app_name
                and r_start - self._buffer[-1]["end_ts"] <= 2.0
            ):
                self._buffer[-1]["end_ts"] = max(self._buffer[-1]["end_ts"], r_end)
            else:
                self._buffer.append({
                    "start_ts": r_start,
                    "end_ts": r_end,
                    "app_name": app_name,
                    "category": "workstation"
                })
            logger.debug(f"Logged interval: {app_name} ({end_ts - start_ts:.1f}s)")

    def flush_now(self) -> int:
        now = time.time()
        with self._lock:
            if self._session_start_ts and not self._is_idle and self._current_app:
                # Cap open interval cleanly if a sleep gap hasn't been processed yet
                cap_end = now
                if self._last_tick_ts and (now - self._last_tick_ts > 20.0):
                    cap_end = self._last_tick_ts
                if cap_end > self._session_start_ts + 1.0:
                    self._buffer.append({
                        "start_ts": round(self._session_start_ts, 2),
                        "end_ts": round(cap_end, 2),
                        "app_name": self._current_app,
                        "category": "workstation"
                    })
                    self._session_start_ts = now if cap_end == now else None

            if not self._buffer:
                return 0

            payload = {
                "device_id": self.device_id,
                "device_name": self.device_name,
                "device_type": self.device_type,
                "sessions": list(self._buffer)
            }
            to_send = list(self._buffer)
            self._buffer.clear()
            self._last_flush_ts = now

        try:
            url = f"{self.hub_url}/api/sync"
            res = self._http.post(url, json=payload, timeout=3.0)
            if res.status_code == 200:
                logger.info(f"Flushed {len(to_send)} sessions to Hub successfully.")
                return len(to_send)
            else:
                logger.warning(f"Hub returned status {res.status_code} during flush.")
                with self._lock:
                    self._buffer = to_send + self._buffer
        except Exception as e:
            logger.warning(f"Failed to connect to Hub at {self.hub_url}: {e}")
            with self._lock:
                self._buffer = to_send + self._buffer
        return 0

    def tick(self):
        now = time.time()

        # 1. Detect Windows Sleep / Hibernation wall-clock jump (>20s between 2s ticks)
        sleep_gap_threshold = max(20.0, self.poll_interval * 8.0)
        if self._last_tick_ts is not None and (now - self._last_tick_ts) > sleep_gap_threshold:
            pre_sleep_end = self._last_tick_ts
            logger.info(
                f"Detected system resume from Sleep/Hibernation "
                f"(gap: {now - pre_sleep_end:.0f}s). Closing pre-sleep session cleanly."
            )
            if self._session_start_ts and self._current_app and pre_sleep_end > self._session_start_ts:
                self._record_interval(self._current_app, self._session_start_ts, pre_sleep_end)
            self._session_start_ts = None
            self._current_app = None
            self._is_idle = False
            self._last_tick_ts = now
            self.flush_now()
            return

        self._last_tick_ts = now

        # 2. Fast idle/lock check BEFORE expensive foreground process inspection
        idle_sec = self._get_idle_seconds()
        is_locked = self._is_workstation_locked()
        raw_exe = ""
        if not is_locked and idle_sec < self.idle_threshold_sec:
            raw_exe = self._get_foreground_raw_exe()
            if raw_exe.lower() in LOCK_SCREEN_PROCESSES:
                is_locked = True

        if is_locked or idle_sec >= self.idle_threshold_sec:
            if not self._is_idle:
                self._is_idle = True
                cut_ts = now if is_locked else max(self._session_start_ts or now, now - idle_sec)
                if self._session_start_ts and self._current_app and cut_ts > self._session_start_ts:
                    self._record_interval(self._current_app, self._session_start_ts, cut_ts)
                self._session_start_ts = None
                self._current_app = None
                reason = "workstation locked" if is_locked else f"idle {idle_sec:.0f}s"
                logger.info(f"Paused screen logging ({reason}).")
                self.flush_now()
            return

        # 3. User is active
        if self._is_idle:
            self._is_idle = False
            logger.info("User activity detected. Resuming active tracking.")

        active_app = resolve_friendly_exe_name(raw_exe) if raw_exe else "Desktop"

        if self._current_app is None:
            self._current_app = active_app
            self._session_start_ts = now
        elif active_app != self._current_app:
            if self._session_start_ts:
                self._record_interval(self._current_app, self._session_start_ts, now)
            self._current_app = active_app
            self._session_start_ts = now

        # 4. Periodic durable background flush every 15s (survives unexpected power loss)
        if now - self._last_flush_ts >= self.flush_interval_sec:
            self.flush_now()

    def run_loop(self):
        logger.info(f"Win32 Screen Agent started for device: {self.device_name} (Polling every {self.poll_interval}s)")
        self._running = True
        self._stop_event.clear()
        try:
            while self._running and not self._stop_event.is_set():
                self.tick()
                self._stop_event.wait(self.poll_interval)
        finally:
            self.flush_now()
            try:
                self._http.close()
            except Exception:
                pass
            logger.info("Win32 Screen Agent stopped.")

    def start_background(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [Win32Agent] %(message)s")
    agent = Win32ScreenAgent()
    try:
        agent.run_loop()
    except KeyboardInterrupt:
        agent.stop()
