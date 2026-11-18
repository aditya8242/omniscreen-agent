import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from hub.server import app, require_localhost
from hub.database import init_db
from starlette.requests import Request
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("OMNISCREEN_DB_PATH", path)
    init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def client(isolated_db):
    return TestClient(app)


def test_security_headers_present(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("referrer-policy") == "no-referrer"


def test_cors_blocks_untrusted_origins(client):
    res = client.get("/api/reality", headers={"Origin": "https://evil-site.example"})
    assert res.status_code == 200
    # Untrusted external origins must never receive Access-Control-Allow-Origin
    assert res.headers.get("access-control-allow-origin") is None


def test_require_localhost_blocks_remote_ip():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/shutdown",
        "headers": [],
        "client": ("10.175.204.222", 54321),
    }
    req = Request(scope)
    with pytest.raises(HTTPException) as exc:
        require_localhost(req)
    assert exc.value.status_code == 403


def test_sync_rejects_negative_or_oversized_payload(client):
    # Negative timestamps rejected
    bad_ts = {
        "device_id": "android_test",
        "device_name": "Test Phone",
        "device_type": "android",
        "sessions": [{"start_ts": -100.0, "end_ts": 50.0, "app_name": "Chrome"}]
    }
    res = client.post("/api/sync", json=bad_ts)
    assert res.status_code == 422

    # Oversized DoS session list (>5000 items) rejected
    dos_payload = {
        "device_id": "android_test",
        "device_name": "Test Phone",
        "device_type": "android",
        "sessions": [{"start_ts": 1000.0 + i, "end_ts": 1001.0 + i, "app_name": "A"} for i in range(5005)]
    }
    res_dos = client.post("/api/sync", json=dos_payload)
    assert res_dos.status_code == 422


def test_favicon_svg_served(client):
    res = client.get("/favicon.svg")
    assert res.status_code == 200
    assert "image/svg+xml" in res.headers.get("content-type", "")
    assert "<svg" in res.text
