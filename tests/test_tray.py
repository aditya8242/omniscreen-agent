import sys
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from PIL import Image

from hub.tray import (
    OmniScreenTray,
    _get_autostart_command,
    is_autostart_enabled,
    set_autostart,
    ensure_default_autostart_once,
    _load_tray_image,
)


def test_tray_tooltip_formatting():
    tray = OmniScreenTray(on_open_dashboard=lambda: None, on_quit=lambda: None)

    # 1. Default fallback when no stats available
    assert tray._format_tooltip(None) == "OmniScreen Reality Hub (Active)"
    assert tray._format_tooltip({}) == "OmniScreen Reality Hub (Active)"

    # 2. Formatted with 1 device
    stats_single = {
        "true_exposure_formatted": "1h 45m",
        "second_screening_formatted": "0m",
        "device_count": 1,
    }
    assert tray._format_tooltip(stats_single) == "OmniScreen: 1h 45m True Exposure (1 device)"

    # 3. Formatted with multiple devices
    stats_multi = {
        "true_exposure_formatted": "4h 12m",
        "second_screening_formatted": "1h 30m",
        "device_count": 3,
    }
    assert tray._format_tooltip(stats_multi) == "OmniScreen: 4h 12m True Exposure (3 devices)"


def test_tray_tooltip_truncation_and_edge_cases():
    """Elite boundary test: Windows Shell_NotifyIcon szTip has a strict 128-char limit (max 127 + null terminator)."""
    tray = OmniScreenTray(on_open_dashboard=lambda: None, on_quit=lambda: None)

    # Massive exposure string exceeding 127 characters
    oversized_stats = {
        "true_exposure_formatted": "9999999999 hours 59 minutes and 59 seconds of continuous intense multi-screening across fifty synchronized workstation displays",
        "device_count": 42,
    }
    tip = tray._format_tooltip(oversized_stats)
    assert len(tip) <= 127
    assert tip.startswith("OmniScreen:")

    # 0 devices boundary
    stats_zero = {
        "true_exposure_formatted": "0m",
        "device_count": 0,
    }
    assert tray._format_tooltip(stats_zero) == "OmniScreen: 0m True Exposure (0 devices)"

    # Null / missing fields handled gracefully without KeyError
    stats_empty_fields = {
        "true_exposure_formatted": "12m",
    }
    assert tray._format_tooltip(stats_empty_fields) == "OmniScreen: 12m True Exposure (1 device)"


def test_tray_menu_status_formatting():
    tray = OmniScreenTray(on_open_dashboard=lambda: None, on_quit=lambda: None)

    # 1. Fallback menu text
    assert tray._format_menu_status(None) == "Today: Calculating Reality..."

    # 2. Formatted menu text
    stats = {
        "true_exposure_formatted": "3h 20m",
        "second_screening_formatted": "45m",
        "device_count": 2,
    }
    assert tray._format_menu_status(stats) == "Today: 3h 20m True Exposure (45m Overlap)"

    # 3. Fallback when second_screening_formatted is omitted
    stats_no_overlap = {
        "true_exposure_formatted": "1h 00m",
    }
    assert tray._format_menu_status(stats_no_overlap) == "Today: 1h 00m True Exposure (0m Overlap)"


def test_tray_fetch_stats_resilience(monkeypatch):
    tray = OmniScreenTray(
        on_open_dashboard=lambda: None,
        on_quit=lambda: None,
        hub_url="http://127.0.0.1:8765",
    )

    # Simulate network failure -> returns None cleanly, zero uncaught exceptions
    monkeypatch.setattr("requests.get", MagicMock(side_effect=Exception("Connection refused")))
    assert tray._fetch_stats() is None

    # Simulate successful response -> returns parsed json
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"true_exposure_formatted": "2h"}
    monkeypatch.setattr("requests.get", MagicMock(return_value=mock_resp))
    assert tray._fetch_stats() == {"true_exposure_formatted": "2h"}


def test_tray_stop_lifecycle():
    tray = OmniScreenTray(on_open_dashboard=lambda: None, on_quit=lambda: None)
    mock_icon = MagicMock()
    tray._icon = mock_icon
    tray._running = True

    tray.stop()
    assert tray._running is False
    mock_icon.stop.assert_called_once()


def test_tray_action_handlers():
    """Verify that tray menu callbacks invoke user callbacks and stop signals accurately."""
    mock_open = MagicMock()
    mock_quit = MagicMock()
    tray = OmniScreenTray(on_open_dashboard=mock_open, on_quit=mock_quit)
    mock_icon = MagicMock()
    tray._icon = mock_icon
    tray._running = True

    # 1. Open dashboard callback
    tray._handle_open(mock_icon, None)
    mock_open.assert_called_once()

    # 2. Quit callback triggers both on_quit and stop()
    tray._handle_quit(mock_icon, None)
    mock_quit.assert_called_once()
    assert tray._running is False
    mock_icon.stop.assert_called_once()


def test_tray_toggle_autostart(monkeypatch):
    """Verify autostart toggle flips registry state and refreshes tray menu."""
    tray = OmniScreenTray(on_open_dashboard=lambda: None, on_quit=lambda: None)
    mock_icon = MagicMock()

    # Mock autostart enabled -> disabled
    monkeypatch.setattr("hub.tray.is_autostart_enabled", lambda: True)
    mock_set = MagicMock()
    monkeypatch.setattr("hub.tray.set_autostart", mock_set)

    tray._toggle_autostart(mock_icon, None)
    mock_set.assert_called_once_with(False)
    mock_icon.update_menu.assert_called_once()


def test_autostart_command_resolution(monkeypatch):
    """Test autostart command string generation for frozen and source environments."""
    # 1. When frozen as OmniScreen.exe
    monkeypatch.setattr("hub.tray.is_frozen", lambda: True)
    cmd_frozen = _get_autostart_command()
    assert cmd_frozen.endswith('--background"') or cmd_frozen.endswith("--background'") or '--background' in cmd_frozen
    assert str(sys.executable) in cmd_frozen

    # 2. When running from Python source
    monkeypatch.setattr("hub.tray.is_frozen", lambda: False)
    cmd_source = _get_autostart_command()
    assert "main.py" in cmd_source
    assert "--background" in cmd_source


def test_autostart_registry_operations(monkeypatch):
    """Verify safe winreg handling, including exceptions and missing keys."""
    if sys.platform != "win32":
        pytest.skip("Windows only test")

    import winreg

    # 1. is_autostart_enabled: Value found
    mock_key = MagicMock()
    monkeypatch.setattr(winreg, "OpenKey", MagicMock(return_value=mock_key))
    monkeypatch.setattr(winreg, "QueryValueEx", MagicMock(return_value=('"C:\\OmniScreen.exe" --background', 1)))
    assert is_autostart_enabled() is True

    # 2. is_autostart_enabled: Key not found / exception
    monkeypatch.setattr(winreg, "OpenKey", MagicMock(side_effect=FileNotFoundError("Key not found")))
    assert is_autostart_enabled() is False

    # 3. set_autostart(True): Sets value in registry
    mock_set_val = MagicMock()
    monkeypatch.setattr(winreg, "OpenKey", MagicMock(return_value=mock_key))
    monkeypatch.setattr(winreg, "SetValueEx", mock_set_val)
    assert set_autostart(True) is True
    assert mock_set_val.called

    # 4. set_autostart(False): Deletes value safely
    mock_del_val = MagicMock()
    monkeypatch.setattr(winreg, "DeleteValue", mock_del_val)
    assert set_autostart(False) is True
    assert mock_del_val.called


def test_ensure_default_autostart_once(tmp_path, monkeypatch):
    """Verify first-run autostart initialization creates marker file and only runs once."""
    monkeypatch.setattr("hub.tray.is_frozen", lambda: True)
    monkeypatch.setattr("hub.tray.get_user_data_dir", lambda: tmp_path)
    mock_set = MagicMock(return_value=True)
    monkeypatch.setattr("hub.tray.set_autostart", mock_set)

    # First run: marker does not exist -> enables autostart and creates marker
    marker = tmp_path / ".autostart_initialized"
    assert not marker.exists()
    ensure_default_autostart_once()
    assert mock_set.call_count == 1
    assert marker.exists()

    # Second run: marker exists -> no-op, set_autostart not called again
    ensure_default_autostart_once()
    assert mock_set.call_count == 1


def test_load_tray_image_asset_and_fallback(tmp_path, monkeypatch):
    """Verify that _load_tray_image loads the PNG asset when present and falls back to generated RGBA."""
    # 1. Normal asset present
    img = _load_tray_image()
    assert isinstance(img, Image.Image)
    assert img.mode == "RGBA"

    # 2. Asset missing fallback
    monkeypatch.setattr("hub.tray.get_bundle_assets_dir", lambda: tmp_path)
    fallback_img = _load_tray_image()
    assert isinstance(fallback_img, Image.Image)
    assert fallback_img.mode == "RGBA"
    assert fallback_img.size == (64, 64)
