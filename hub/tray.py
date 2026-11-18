import sys
import logging
from typing import Callable, Optional
from PIL import Image, ImageDraw

from hub.paths import is_frozen, get_bundle_assets_dir, get_user_data_dir

logger = logging.getLogger("OmniTray")

AUTOSTART_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_VALUE_NAME = "OmniScreen"


def _get_autostart_command() -> str:
    if is_frozen():
        return f'"{sys.executable}" --background'
    # When running from source, prefer pythonw.exe (no terminal window) if available
    py_exe = sys.executable
    if py_exe.lower().endswith("python.exe"):
        pyw = py_exe[:-10] + "pythonw.exe"
        import os
        if os.path.exists(pyw):
            py_exe = pyw
    from hub.paths import get_project_root
    main_py = get_project_root() / "main.py"
    return f'"{py_exe}" "{main_py}" --background'


def is_autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, AUTOSTART_VALUE_NAME)
            return bool(val)
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, AUTOSTART_VALUE_NAME, 0, winreg.REG_SZ, _get_autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_VALUE_NAME)
                except FileNotFoundError:
                    pass
        logger.info(f"Windows startup auto-launch set to: {enabled}")
        return True
    except Exception as e:
        logger.warning(f"Could not update Windows startup setting: {e}")
        return False


def ensure_default_autostart_once():
    """
    On first run of packaged OmniScreen.exe, enables Start with Windows so PC tracking
    continues seamlessly after shutdown/reboot. Respects the user's choice if toggled off later.
    """
    if not is_frozen() or sys.platform != "win32":
        return
    marker = get_user_data_dir() / ".autostart_initialized"
    if not marker.exists():
        if set_autostart(True):
            try:
                marker.write_text("1", encoding="utf-8")
            except Exception:
                pass


def _load_tray_image() -> Image.Image:
    icon_path = get_bundle_assets_dir() / "icon-192.png"
    if icon_path.exists():
        try:
            return Image.open(icon_path).convert("RGBA")
        except Exception:
            pass
    # Crisp fallback icon matching official OmniScreen rings
    img = Image.new("RGBA", (64, 64), (14, 14, 18, 255))
    d = ImageDraw.Draw(img)
    d.ellipse([10, 16, 42, 48], outline=(10, 132, 255, 255), width=5)
    d.ellipse([22, 16, 54, 48], outline=(191, 90, 242, 255), width=5)
    d.ellipse([28, 28, 36, 36], fill=(48, 209, 88, 255))
    return img


class OmniScreenTray:
    """
    Native Windows System Tray controller.
    Keeps OmniScreen Reality Hub + Win32 PC tracking alive silently in the background
    when the user closes the dashboard window, with 1-click reopen, startup toggle, and clean quit.
    """

    def __init__(
        self,
        on_open_dashboard: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        self._on_open_dashboard = on_open_dashboard
        self._on_quit = on_quit
        self._icon = None

    def _toggle_autostart(self, icon, item):
        current = is_autostart_enabled()
        set_autostart(not current)
        try:
            icon.update_menu()
        except Exception:
            pass

    def _handle_open(self, icon, item):
        self._on_open_dashboard()

    def _handle_quit(self, icon, item):
        self._on_quit()
        try:
            icon.stop()
        except Exception:
            pass

    def run_blocking(self) -> bool:
        try:
            import pystray
        except Exception as e:
            logger.warning(f"System tray unavailable (pystray import failed): {e}")
            return False

        menu = pystray.Menu(
            pystray.MenuItem("Open OmniScreen Dashboard", self._handle_open, default=True),
            pystray.MenuItem(
                "Start with Windows",
                self._toggle_autostart,
                checked=lambda item: is_autostart_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit OmniScreen", self._handle_quit),
        )

        self._icon = pystray.Icon(
            name="OmniScreen",
            icon=_load_tray_image(),
            title="OmniScreen Reality Hub (Active)",
            menu=menu,
        )
        self._icon.run()
        return True

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
