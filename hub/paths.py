import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_project_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_bundle_assets_dir() -> Path:
    """Returns read-only bundled assets folder (works both in source and PyInstaller --onefile)."""
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        meipass_assets = Path(sys._MEIPASS) / "assets"
        if meipass_assets.exists():
            return meipass_assets
    return get_project_root() / "assets"


def get_user_data_dir() -> Path:
    """
    Returns persistent user data directory for SQLite DB, config.json, logs, and browser profile.
    - When packaged as OmniScreen.exe: %LOCALAPPDATA%/OmniScreen (survives upgrades & reboots!)
    - When running from Python source: <project_root>/data
    """
    if is_frozen():
        local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        data_dir = Path(local_app_data) / "OmniScreen"
    else:
        data_dir = get_project_root() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
