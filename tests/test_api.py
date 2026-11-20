import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from hub.server import app
from hub.database import init_db

@pytest.fixture(autouse=True)
def isolated_test_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("OMNISCREEN_DB_PATH", path)
    init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture
def client(isolated_test_db):
    return TestClient(app)

def test_api_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "live"
    assert "devices_connected" in data
    assert "lan_ip" in data

def test_api_dashboard_and_qr(client):
    # Test Apple Dashboard HTML
    res_dash = client.get("/")
    assert res_dash.status_code == 200
    assert "OmniScreen Reality" in res_dash.text
    assert "True Combined Screen Exposure" in res_dash.text

    # Test Local QR Code generation
    res_qr = client.get("/api/qr")
    assert res_qr.status_code == 200
    assert res_qr.headers["content-type"] == "image/png"
    assert res_qr.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert "no-store" in res_qr.headers.get("cache-control", "")

    # Test Mobile QR Pairing handoff page
    res_pair = client.get("/pair")
    assert res_pair.status_code == 200
    assert "Connected to " in res_pair.text
    assert "omniscreen://pair?host=" in res_pair.text
    assert "&name=" in res_pair.text

def test_api_sync_and_reality(client):
    # Sync PC session
    pc_payload = {
        "device_id": "test_pc_1",
        "device_name": "Workstation",
        "device_type": "pc",
        "sessions": [
            {"start_ts": 1731810000.0, "end_ts": 1731813600.0, "app_name": "VS Code"}
        ]
    }
    res_pc = client.post("/api/sync", json=pc_payload)
    assert res_pc.status_code == 200
    assert res_pc.json()["inserted_sessions"] == 1

    # Sync Android session (partially overlapping)
    android_payload = {
        "device_id": "test_android_1",
        "device_name": "Galaxy S23",
        "device_type": "android",
        "sessions": [
            {"start_ts": 1731811800.0, "end_ts": 1731815400.0, "app_name": "Instagram"}
        ]
    }
    res_android = client.post("/api/sync", json=android_payload)
    assert res_android.status_code == 200
    sync_body = res_android.json()
    assert sync_body["inserted_sessions"] == 1
    assert "pc_name" in sync_body
    assert isinstance(sync_body.get("reality"), dict)
    assert "true_exposure_formatted" in sync_body["reality"]
    assert "devices" in sync_body["reality"]

    from datetime import datetime
    date_str = datetime.fromtimestamp(1731810000.0).strftime("%Y-%m-%d")

    # Query reality for this specific date
    res_reality = client.get(f"/api/reality?date={date_str}")
    assert res_reality.status_code == 200
    reality = res_reality.json()
    assert reality["raw_total_seconds"] == 7200.0
    assert reality["true_exposure_seconds"] == 5400.0
    assert reality["second_screening_seconds"] == 1800.0
    assert "ssi_percent" in reality
    assert "ssi_status" in reality
    assert len(reality["devices"]) == 2

    # Verify device list endpoint
    res_devices = client.get("/api/devices")
    assert res_devices.status_code == 200
    assert len(res_devices.json()["devices"]) == 2

    # Test Rename Device (including apostrophe) and verify name stays locked on subsequent sync
    res_rename = client.post("/api/device/rename?device_id=test_pc_1&new_name=Aditya%27s%20Workstation")
    assert res_rename.status_code == 200
    res_dev_after_rename = client.get("/api/devices")
    names = [d["device_name"] for d in res_dev_after_rename.json()["devices"]]
    assert "Aditya's Workstation" in names

    # Re-sync PC with original default name; custom dashboard name must remain preserved
    res_pc_again = client.post("/api/sync", json=pc_payload)
    assert res_pc_again.status_code == 200
    names_after_resync = [d["device_name"] for d in client.get("/api/devices").json()["devices"]]
    assert "Aditya's Workstation" in names_after_resync

    # Test Delete Device
    res_del = client.post("/api/device/delete?device_id=test_android_1")
    assert res_del.status_code == 200
    res_dev_after_del = client.get("/api/devices")
    assert len(res_dev_after_del.json()["devices"]) == 1

    # Deleting already-removed device returns 404
    res_del_missing = client.post("/api/device/delete?device_id=test_android_1")
    assert res_del_missing.status_code == 404

def test_api_manual_tv_validation(client):
    res_bad = client.post("/api/tv/add", json={"device_name": "Living Room", "ip_address": "not-an-ip"})
    assert res_bad.status_code == 400

def test_api_export_csv_and_json(client):
    # Seed sessions via sync
    payload = {
        "device_id": "export_pc_1",
        "device_name": "Developer Machine",
        "device_type": "pc",
        "sessions": [
            {"start_ts": 1731810000.0, "end_ts": 1731813600.0, "app_name": "PyCharm"},
            {"start_ts": 1731814000.0, "end_ts": 1731815800.0, "app_name": "Chrome"}
        ]
    }
    sync_res = client.post("/api/sync", json=payload)
    assert sync_res.status_code == 200

    from datetime import datetime
    date_str = datetime.fromtimestamp(1731810000.0).strftime("%Y-%m-%d")

    # 1. Test CSV Export (default format)
    res_csv = client.get(f"/api/export?start_date={date_str}&end_date={date_str}")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "attachment; filename=" in res_csv.headers.get("content-disposition", "")
    lines = res_csv.text.strip().splitlines()
    assert len(lines) == 3  # Header + 2 rows
    assert lines[0] == "device_id,device_name,device_type,app_name,start_time,end_time,duration_seconds"
    assert "export_pc_1,Developer Machine,pc,PyCharm" in lines[1]
    assert "3600.0" in lines[1]
    assert "export_pc_1,Developer Machine,pc,Chrome" in lines[2]
    assert "1800.0" in lines[2]

    # 2. Test JSON Export
    res_json = client.get(f"/api/export?format=json&start_date={date_str}&end_date={date_str}")
    assert res_json.status_code == 200
    data = res_json.json()
    assert "sessions" in data
    assert data["count"] == 2
    assert len(data["sessions"]) == 2
    s1 = data["sessions"][0]
    assert s1["device_id"] == "export_pc_1"
    assert s1["device_name"] == "Developer Machine"
    assert s1["device_type"] == "pc"
    assert s1["app_name"] == "PyCharm"
    assert s1["duration_seconds"] == 3600.0
    assert "start_time" in s1
    assert "end_time" in s1

    # 3. Test Export with Out-of-Range Date Filter returns 0 records
    res_empty = client.get("/api/export?format=json&start_date=2020-01-01&end_date=2020-01-02")
    assert res_empty.status_code == 200
    assert res_empty.json()["count"] == 0
    assert res_empty.json()["sessions"] == []

    # 4. Test Invalid Format Validation
    res_invalid = client.get("/api/export?format=unsupported_format")
    assert res_invalid.status_code == 422


def test_api_reality_card_export_components(client):
    """Verify that the dashboard serves the Daily Reality Card HTML5 canvas and export actions."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # 1. Action Triggers
    assert "openRealityCardModal()" in html
    assert "Share Card" in html
    assert "Reality Card" in html

    # 2. Modal Structure
    assert 'id="realityCardModal"' in html
    assert 'id="realityCardCanvas"' in html
    assert 'width="1200"' in html
    assert 'height="675"' in html

    # 3. Client-Side Export Logic
    assert "renderRealityCardCanvas" in html
    assert "downloadRealityCardImage" in html
    assert "copyRealityCardImage" in html
    assert "OmniScreen-Reality-Card-" in html

