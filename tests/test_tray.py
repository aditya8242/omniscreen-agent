import pytest
from unittest.mock import MagicMock
from hub.tray import OmniScreenTray


def test_tray_tooltip_formatting():
    tray = OmniScreenTray(on_open_dashboard=lambda: None, on_quit=lambda: None)

    # 1. Default fallback when no stats available
    assert tray._format_tooltip(None) == "OmniScreen Reality Hub (Active)"
    assert tray._format_tooltip({}) == "OmniScreen Reality Hub (Active)"

    # 2. Formatted with 1 device
    stats_single = {
        "true_exposure_formatted": "1h 45m",
        "second_screening_formatted": "0m",
        "device_count": 1
    }
    assert tray._format_tooltip(stats_single) == "OmniScreen: 1h 45m True Exposure (1 device)"

    # 3. Formatted with multiple devices
    stats_multi = {
        "true_exposure_formatted": "4h 12m",
        "second_screening_formatted": "1h 30m",
        "device_count": 3
    }
    assert tray._format_tooltip(stats_multi) == "OmniScreen: 4h 12m True Exposure (3 devices)"


def test_tray_menu_status_formatting():
    tray = OmniScreenTray(on_open_dashboard=lambda: None, on_quit=lambda: None)

    # 1. Fallback menu text
    assert tray._format_menu_status(None) == "Today: Calculating Reality..."

    # 2. Formatted menu text
    stats = {
        "true_exposure_formatted": "3h 20m",
        "second_screening_formatted": "45m",
        "device_count": 2
    }
    assert tray._format_menu_status(stats) == "Today: 3h 20m True Exposure (45m Overlap)"


def test_tray_fetch_stats_resilience(monkeypatch):
    tray = OmniScreenTray(
        on_open_dashboard=lambda: None,
        on_quit=lambda: None,
        hub_url="http://127.0.0.1:8765"
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
