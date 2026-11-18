import sys
import os
import time
import socket
import logging
import threading
import subprocess
from pathlib import Path
import requests
import uvicorn

# Add omniscreen_v2 root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from hub.database import init_db
from hub.network import get_active_lan_ip
from hub.server import app, set_tv_sensor, set_lan_ip, set_shutdown_callback
from hub.discovery import UDPDiscoveryResponder
from agents.win32_agent import Win32ScreenAgent
from agents.tv_sensor import SmartTVSensor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("OmniScreen")


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
        self.config = uvicorn.Config(app=app, host=host, port=port, log_level="warning")
        self.server = uvicorn.Server(self.config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


def launch_apple_desktop_window(url: str):
    """
    Launches Edge/Chrome in standalone App Mode with an isolated user-data-dir.
    Isolating the profile guarantees the browser runs as its own dedicated process
    instead of handing off to an existing background Edge instance and exiting immediately.
    """
    profile_dir = BASE_DIR / "data" / "app_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    browser_candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
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
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(f"Launched standalone desktop app window via {os.path.basename(exe)}")
                return proc
            except Exception as e:
                logger.debug(f"Failed to launch with {exe}: {e}")
    return None


def main():
    print("=" * 72)
    print("      OMNISCREEN: CROSS-DEVICE SCREEN TIME INTELLIGENCE")
    print("      Architecture: Three Independent Engines + Reality Hub")
    print("      Design: Apple macOS Sequoia & iOS Screen Time")
    print("=" * 72)

    port = 8765
    if is_port_in_use(port):
        print(f"\n[ERROR] Port {port} is already in use by another process.")
        print("        Another OmniScreen Hub may already be running.")
        print("        Run 'stop.bat' first, or open http://127.0.0.1:8765 in your browser.\n")
        return

    # 1. Initialize local SQLite storage
    init_db()
    logger.info("Local SQLite Reality Hub storage initialized.")

    # Always resolve live LAN IP dynamically inside server & discovery
    set_lan_ip(None)
    lan_ip = get_active_lan_ip()

    shutdown_event = threading.Event()
    set_shutdown_callback(shutdown_event.set)

    # 2. Start UDP Auto-Discovery Responder (Port 8766)
    discovery_responder = UDPDiscoveryResponder(hub_port=port, discovery_port=8766, lan_ip=None)
    discovery_responder.start()

    # 3. Start FastAPI Server in background
    server_thread = UvicornServerThread(host="0.0.0.0", port=port)
    server_thread.start()

    if not wait_for_hub_ready(f"http://127.0.0.1:{port}", timeout_sec=6.0):
        logger.error("Reality Hub API server failed to start on port 8765.")
        discovery_responder.stop()
        server_thread.stop()
        return

    logger.info(f"Reality Hub API server ready on 0.0.0.0:{port}")

    print(f"\n[HUB ACTIVE] Local URL:   http://127.0.0.1:{port}")
    print(f"[HUB ACTIVE] Network LAN: http://{lan_ip}:{port}")
    print(f"[PAIRING]    QR Handoff:  http://{lan_ip}:{port}/pair")
    print("--> Tap 'Auto-Detect PC Hub' in your Android app, or scan the QR code.\n")

    # 4. Start Engine A: Win32 Desktop Agent
    win32_agent = Win32ScreenAgent(hub_url=f"http://127.0.0.1:{port}")
    win32_agent.start_background()

    # 5. Start Engine C: Smart TV Network Presence Sensor
    tv_sensor = SmartTVSensor(hub_url=f"http://127.0.0.1:{port}")
    set_tv_sensor(tv_sensor)
    tv_sensor.start_background()

    # 6. Launch Native Desktop App Window (unless headless mode requested)
    headless = "--headless" in sys.argv or os.environ.get("OMNISCREEN_HEADLESS") == "1"
    app_proc = None
    launch_ts = time.time()

    if not headless:
        app_proc = launch_apple_desktop_window(f"http://127.0.0.1:{port}/")

    if headless:
        print("[HUB RUNNING] Headless mode active. Press Ctrl+C to stop OmniScreen.")
        try:
            while not shutdown_event.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received.")
    elif not app_proc:
        logger.info("Starting Tkinter widget fallback...")
        from ui.widget import OmniScreenWidget
        widget = OmniScreenWidget(
            hub_url=f"http://127.0.0.1:{port}",
            win32_agent=win32_agent,
            tv_sensor=tv_sensor,
            lan_ip=lan_ip
        )
        try:
            widget.run()
        except KeyboardInterrupt:
            pass
    else:
        try:
            while not shutdown_event.is_set():
                if app_proc.poll() is not None:
                    elapsed = time.time() - launch_ts
                    if elapsed < 4.0:
                        # Browser handed off window to an existing browser process;
                        # keep the Reality Hub alive until user presses Ctrl+C!
                        logger.info(
                            "Desktop window attached to existing browser session. "
                            "Keeping Reality Hub active in this terminal (press Ctrl+C to stop)."
                        )
                        app_proc = None
                        while not shutdown_event.is_set():
                            time.sleep(0.5)
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received.")

    # Graceful shutdown
    print("\n[SHUTDOWN] Gracefully stopping OmniScreen services...")
    if app_proc and app_proc.poll() is None:
        try:
            app_proc.terminate()
        except Exception:
            pass

    discovery_responder.stop()
    win32_agent.stop()
    tv_sensor.stop()
    server_thread.stop()
    time.sleep(0.5)
    print("[SHUTDOWN] All services stopped. Port 8765 & 8766 freed. Goodbye.")


if __name__ == "__main__":
    main()
