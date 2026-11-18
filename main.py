import sys
import os
import time
import atexit
import socket
import logging
from logging.handlers import RotatingFileHandler
import threading
import subprocess
from pathlib import Path
import requests
import uvicorn

# Add omniscreen_v2 root to sys.path when running from source
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from hub.paths import get_user_data_dir, is_frozen
from hub.database import init_db
from hub.network import get_active_lan_ip
from hub.server import app, set_tv_sensor, set_lan_ip, set_shutdown_callback
from hub.discovery import UDPDiscoveryResponder
from hub.tray import OmniScreenTray, ensure_default_autostart_once
from agents.win32_agent import Win32ScreenAgent
from agents.tv_sensor import SmartTVSensor


def _configure_logging():
    handlers = []
    try:
        log_file = get_user_data_dir() / "omniscreen.log"
        handlers.append(RotatingFileHandler(str(log_file), maxBytes=1_000_000, backupCount=2, encoding="utf-8"))
    except Exception:
        pass
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        handlers=handlers or None,
    )


_configure_logging()
logger = logging.getLogger("OmniScreen")


def _safe_print(msg: str):
    if sys.stdout is not None:
        try:
            print(msg, flush=True)
        except Exception:
            pass


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_hub_ready(url: str, timeout_sec: float = 6.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            res = requests.get(f"{url}/api/status", timeout=0.5)
            if res.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.15)
    return False


class UvicornServerThread(threading.Thread):
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        super().__init__(daemon=True)
        # CRITICAL for PyInstaller --noconsole: Uvicorn's default log_config calls
        # sys.stderr.isatty() which crashes when stdout/stderr are None.
        use_log_config = None if (sys.stderr is None or is_frozen()) else uvicorn.config.LOGGING_CONFIG
        self.config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="warning",
            log_config=use_log_config,
        )
        self.server = uvicorn.Server(self.config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


def launch_apple_desktop_window(url: str):
    """
    Launches Edge/Chrome in standalone App Mode with an isolated persistent user-data-dir.
    """
    profile_dir = get_user_data_dir() / "app_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    browser_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    for exe in browser_candidates:
        if os.path.exists(exe):
            try:
                cmd = [
                    exe,
                    f"--app={url}",
                    f"--user-data-dir={profile_dir}",
                    "--window-size=520,860",
                    "--no-first-run",
                    "--no-default-browser-check",
                ]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                )
                logger.info(f"Launched standalone desktop app window via {os.path.basename(exe)}")
                return proc
            except Exception as e:
                logger.debug(f"Failed to launch with {exe}: {e}")
    return None


def main():
    port = 8765
    local_url = f"http://127.0.0.1:{port}"
    background_only = "--background" in sys.argv
    headless = "--headless" in sys.argv or os.environ.get("OMNISCREEN_HEADLESS") == "1"

    # Single-instance behavior: if OmniScreen is already running in the tray,
    # simply open the Dashboard window cleanly instead of erroring out!
    if is_port_in_use(port):
        if not background_only and not headless:
            logger.info("OmniScreen Hub is already running. Opening Dashboard window.")
            launch_apple_desktop_window(f"{local_url}/")
        return

    _safe_print("=" * 72)
    _safe_print("      OMNISCREEN: CROSS-DEVICE SCREEN TIME INTELLIGENCE")
    _safe_print("      Architecture: Three Independent Engines + Reality Hub")
    _safe_print("      Design: Apple macOS Sequoia & iOS Screen Time")
    _safe_print("=" * 72)

    # 1. Initialize persistent SQLite storage & optional first-run Windows startup entry
    init_db()
    ensure_default_autostart_once()
    if sys.platform == "win32":
        try:
            import psutil
            psutil.Process(os.getpid()).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass
    logger.info(f"Local SQLite Reality Hub initialized in {get_user_data_dir()}")

    set_lan_ip(None)
    lan_ip = get_active_lan_ip()

    shutdown_event = threading.Event()
    tray_ref = [None]

    def trigger_shutdown():
        shutdown_event.set()
        if tray_ref[0] is not None:
            tray_ref[0].stop()

    set_shutdown_callback(trigger_shutdown)

    # 2. Start UDP Auto-Discovery Responder (Port 8766)
    discovery_responder = UDPDiscoveryResponder(hub_port=port, discovery_port=8766, lan_ip=None)
    discovery_responder.start()

    # 3. Start FastAPI Server in background
    server_thread = UvicornServerThread(host="0.0.0.0", port=port)
    server_thread.start()

    if not wait_for_hub_ready(local_url, timeout_sec=8.0):
        logger.error("Reality Hub API server failed to start on port 8765.")
        discovery_responder.stop()
        server_thread.stop()
        return

    logger.info(f"Reality Hub API server ready on 0.0.0.0:{port} (LAN: {lan_ip})")

    _safe_print(f"\n[HUB ACTIVE] Local URL:   {local_url}")
    _safe_print(f"[HUB ACTIVE] Network LAN: http://{lan_ip}:{port}")
    _safe_print(f"[PAIRING]    QR Handoff:  http://{lan_ip}:{port}/pair")
    _safe_print("--> Running quietly in System Tray. Right-click tray icon to open or quit.\n")

    # 4. Start Engine A: Win32 Desktop Agent (sleep/hibernation/lock-screen resilient)
    win32_agent = Win32ScreenAgent(hub_url=local_url)
    win32_agent.start_background()

    # 5. Start Engine C: Smart TV Network Presence Sensor
    tv_sensor = SmartTVSensor(hub_url=local_url)
    set_tv_sensor(tv_sensor)
    tv_sensor.start_background()

    # Ensure final flush happens even on sudden Windows shutdown/logoff
    def _emergency_flush():
        try:
            win32_agent.flush_now()
            tv_sensor.flush_now()
        except Exception:
            pass

    atexit.register(_emergency_flush)

    def open_dashboard():
        launch_apple_desktop_window(f"{local_url}/")

    # 6. Headless test mode vs. End-User System Tray Background Mode
    if headless:
        _safe_print("[HUB RUNNING] Headless mode active. Press Ctrl+C to stop OmniScreen.")
        try:
            while not shutdown_event.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received.")
    else:
        if not background_only:
            open_dashboard()

        tray = OmniScreenTray(on_open_dashboard=open_dashboard, on_quit=trigger_shutdown)
        tray_ref[0] = tray
        tray_started = tray.run_blocking()

        # Fallback wait loop if system tray is unavailable on a headless OS
        if not tray_started:
            try:
                while not shutdown_event.is_set():
                    time.sleep(0.5)
            except KeyboardInterrupt:
                logger.info("Shutdown signal received.")

    # Graceful shutdown
    _safe_print("\n[SHUTDOWN] Gracefully stopping OmniScreen services...")
    logger.info("Gracefully stopping OmniScreen services...")
    discovery_responder.stop()
    win32_agent.stop()
    tv_sensor.stop()
    server_thread.stop()
    time.sleep(0.4)
    _safe_print("[SHUTDOWN] All services stopped. Port 8765 & 8766 freed. Goodbye.")


if __name__ == "__main__":
    main()
