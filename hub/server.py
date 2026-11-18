import time
import io
import re
import json
import math
import socket
import threading
from pathlib import Path
from urllib.parse import quote
import qrcode
from typing import List, Optional, Callable
from fastapi import FastAPI, Query, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from contextlib import asynccontextmanager

from hub.database import (
    init_db,
    insert_sessions_idempotent,
    get_sessions_for_day,
    get_day_boundaries,
    get_all_devices,
    rename_device,
    delete_device
)
from hub.overlap import compute_reality
from hub.dashboard import DASHBOARD_HTML
from hub.network import get_active_lan_ip
from hub.paths import get_bundle_assets_dir

_tv_sensor_ref = None
_lan_ip_override: Optional[str] = None
_shutdown_callback: Optional[Callable[[], None]] = None

IPV4_RE = re.compile(r"^(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$")


def set_tv_sensor(sensor):
    global _tv_sensor_ref
    _tv_sensor_ref = sensor


def set_lan_ip(ip: Optional[str]):
    """Optional override (used in unit tests). Pass None to always auto-detect live LAN IP."""
    global _lan_ip_override
    _lan_ip_override = ip


def set_shutdown_callback(cb: Optional[Callable[[], None]]):
    global _shutdown_callback
    _shutdown_callback = cb


def get_lan_ip() -> str:
    if _lan_ip_override:
        return _lan_ip_override
    return get_active_lan_ip()


def get_pc_display_name() -> str:
    """
    Returns the user's friendly PC name from the Reality Hub database (if renamed),
    otherwise falls back cleanly to the PC hostname.
    """
    try:
        devices = get_all_devices()
        pcs = [d for d in devices if str(d.get("device_type", "")).lower() == "pc"]
        if pcs:
            pcs.sort(key=lambda d: float(d.get("last_sync_ts", 0.0)), reverse=True)
            name = str(pcs[0].get("device_name", "")).strip()
            if name:
                return name
    except Exception:
        pass
    return socket.gethostname() or "My PC"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="OmniScreen Reality Hub", version="0.9.0-beta", lifespan=lifespan)

# Strict local-only CORS prevents untrusted websites in the browser from reading
# localhost screen time data or invoking local Hub endpoints (CSRF protection).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "http://localhost:8765",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def require_localhost(request: Request):
    """
    Restricts administrative and destructive endpoints strictly to the local PC
    so untrusted devices on shared Wi-Fi cannot delete data, scan subnets, or stop the Hub.
    """
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(
            status_code=403,
            detail="This administrative action is only allowed directly from the host PC."
        )


class SessionItem(BaseModel):
    start_ts: float = Field(..., gt=0)
    end_ts: float = Field(..., gt=0)
    app_name: str = Field(default="Unknown", max_length=120)
    category: str = Field(default="screen_on", max_length=40)

    @field_validator("start_ts", "end_ts")
    @classmethod
    def check_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Timestamp must be a finite number")
        return v


class SyncPayload(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=64)
    device_name: str = Field(..., min_length=1, max_length=80)
    device_type: str = Field(..., pattern="^(pc|android|ios|tv)$")
    replace_day_start_ts: Optional[float] = Field(default=None, gt=0)
    sessions: List[SessionItem] = Field(default=[], max_length=5000)


class DeviceRenamePayload(BaseModel):
    device_id: Optional[str] = Field(default=None, max_length=64)
    new_name: Optional[str] = Field(default=None, max_length=80)


class DeviceDeletePayload(BaseModel):
    device_id: Optional[str] = Field(default=None, max_length=64)


class ManualTVPayload(BaseModel):
    device_name: Optional[str] = Field(default=None, max_length=80)
    ip_address: str = Field(..., min_length=7, max_length=15)


@app.get("/favicon.svg")
def get_favicon_svg():
    logo_path = get_bundle_assets_dir() / "logo.svg"
    if logo_path.exists():
        return Response(
            content=logo_path.read_text(encoding="utf-8"),
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=86400"}
        )
    raise HTTPException(status_code=404, detail="Logo not found")


@app.get("/", response_class=HTMLResponse)
def get_apple_dashboard():
    return HTMLResponse(
        content=DASHBOARD_HTML,
        headers={"Cache-Control": "no-store, max-age=0"}
    )


@app.get("/pair", response_class=HTMLResponse)
def get_mobile_pair_page():
    """
    Apple-styled mobile pairing handoff page opened when scanning the PC QR code.
    Shows the friendly PC name prominently and deep-links straight into the Android app.
    """
    from html import escape as html_escape
    lan_ip = get_lan_ip()
    pc_name = get_pc_display_name()
    safe_pc_name = html_escape(pc_name)
    encoded_name = quote(pc_name, safe="")
    host_addr = f"{lan_ip}:8765"
    intent_url = (
        f"intent://pair?host={host_addr}&name={encoded_name}"
        f"#Intent;scheme=omniscreen;package=com.omniscreen.agent;end"
    )
    scheme_url = f"omniscreen://pair?host={host_addr}&name={encoded_name}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Connect to {safe_pc_name}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-font-smoothing: antialiased; }}
    body {{
      background: #000000;
      color: #FFFFFF;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px 18px;
    }}
    .card {{
      width: 100%;
      max-width: 400px;
      background: #141417;
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 24px;
      padding: 28px 22px;
      text-align: center;
      display: flex;
      flex-direction: column;
      gap: 16px;
      box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin: 0 auto;
      padding: 6px 14px;
      border-radius: 999px;
      background: rgba(48, 209, 88, 0.14);
      border: 1px solid rgba(48, 209, 88, 0.3);
      color: #30D158;
      font-size: 12px;
      font-weight: 600;
    }}
    .dot {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #30D158;
    }}
    h1 {{ font-size: 22px; font-weight: 700; letter-spacing: -0.4px; }}
    p {{ font-size: 13px; color: #8E8E93; line-height: 1.5; }}
    .pc-box {{
      background: #1C1C20;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .pc-name {{
      font-size: 17px;
      font-weight: 700;
      color: #FFFFFF;
      letter-spacing: -0.2px;
    }}
    .pc-sub {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 11px;
      color: #636366;
      user-select: all;
    }}
    .btn {{
      display: block;
      width: 100%;
      padding: 15px 18px;
      border-radius: 14px;
      border: none;
      font-size: 15px;
      font-weight: 600;
      text-decoration: none;
      cursor: pointer;
      font-family: inherit;
    }}
    .btn-primary {{ background: #0A84FF; color: #FFFFFF; }}
    .btn-secondary {{ background: #2C2C2E; color: #FFFFFF; }}
    .link-muted {{ color: #8E8E93; font-size: 12px; text-decoration: none; margin-top: 4px; }}
    #copyStatus {{ font-size: 12px; color: #30D158; min-height: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge"><span class="dot"></span>Connected to {safe_pc_name}</div>
    <h1>Pair with {safe_pc_name}</h1>
    <p>Your phone is connected to {safe_pc_name} over local Wi-Fi. Tap below to open the OmniScreen app and sync automatically.</p>
    <div class="pc-box">
      <div class="pc-name">{safe_pc_name}</div>
      <div class="pc-sub">Local Wi-Fi Hub &bull; {host_addr}</div>
    </div>
    <a class="btn btn-primary" id="openAppBtn" href="{intent_url}">Open &amp; Pair OmniScreen App</a>
    <button class="btn btn-secondary" onclick="copyAddr()">Copy Hub Address</button>
    <div id="copyStatus"></div>
    <a class="link-muted" href="/">View Live Dashboard in Mobile Browser</a>
  </div>
  <script>
    const HUB_ADDR = {json.dumps(host_addr)};
    const PC_DISPLAY_NAME = {json.dumps(pc_name)};
    const SCHEME_URL = {json.dumps(scheme_url)};
    function copyAddr() {{
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(HUB_ADDR).then(() => {{
          document.getElementById("copyStatus").innerText = "Copied address for " + PC_DISPLAY_NAME + ".";
        }}).catch(() => {{
          document.getElementById("copyStatus").innerText = "Hub Address: " + HUB_ADDR;
        }});
      }} else {{
        document.getElementById("copyStatus").innerText = "Hub Address: " + HUB_ADDR;
      }}
    }}
    document.getElementById("openAppBtn").addEventListener("click", function() {{
      setTimeout(function() {{
        window.location.href = SCHEME_URL;
      }}, 400);
    }});
  </script>
</body>
</html>"""
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store, max-age=0"})


@app.get("/api/status")
def get_status():
    devices = get_all_devices()
    lan_ip = get_lan_ip()
    return {
        "status": "live",
        "system": "OmniScreen Reality Hub",
        "pc_name": get_pc_display_name(),
        "timestamp": time.time(),
        "lan_ip": lan_ip,
        "hub_port": 8765,
        "discovery_port": 8766,
        "devices_connected": len(devices)
    }


@app.get("/api/qr")
def get_pairing_qr():
    """
    Generates a high-resolution QR Code locally on the PC with zero external cloud dependencies.
    Encodes the PC's live local Wi-Fi /pair handoff URL for instant camera pairing.
    """
    lan_ip = get_lan_ip()
    target_url = f"http://{lan_ip}:8765/pair"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#000000", back_color="#FFFFFF")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store, max-age=0"}
    )


@app.post("/api/sync")
def sync_device_sessions(payload: SyncPayload):
    try:
        session_dicts = [s.model_dump() for s in payload.sessions]
        inserted = insert_sessions_idempotent(
            device_id=payload.device_id,
            device_name=payload.device_name,
            device_type=payload.device_type,
            sessions=session_dicts,
            replace_day_start_ts=payload.replace_day_start_ts
        )
        # Bidirectional on-demand snapshot: only compute full cross-device reality
        # for mobile clients (PC/TV background flushes discard the response body).
        reality_snapshot = None
        if payload.device_type in ("android", "ios"):
            try:
                day_start_ts, day_end_ts, date_str = get_day_boundaries(None)
                today_sessions = get_sessions_for_day(date_str)
                reality_snapshot = compute_reality(today_sessions, day_start_ts, day_end_ts, date_str)
                reality_snapshot["pc_name"] = get_pc_display_name()
            except Exception:
                reality_snapshot = None

        return {
            "status": "ok",
            "message": f"Successfully synced {inserted} sessions for '{payload.device_name}'",
            "device_id": payload.device_id,
            "pc_name": get_pc_display_name(),
            "inserted_sessions": inserted,
            "timestamp": time.time(),
            "reality": reality_snapshot
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save sessions to local database: {str(e)}")


@app.get("/api/reality")
def get_reality(date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")):
    try:
        day_start_ts, day_end_ts, date_str = get_day_boundaries(date)
        sessions = get_sessions_for_day(date_str)
        reality = compute_reality(sessions, day_start_ts, day_end_ts, date_str)
        reality["lan_ip"] = get_lan_ip()
        reality["local_pc_id"] = f"pc_{(socket.gethostname() or 'pc').lower()}"
        return reality
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not compute reality metrics: {str(e)}")


@app.get("/api/devices")
def list_devices():
    return {"devices": get_all_devices()}


@app.post("/api/device/rename", dependencies=[Depends(require_localhost)])
def api_rename_device(
    device_id: Optional[str] = Query(None),
    new_name: Optional[str] = Query(None),
    body: Optional[DeviceRenamePayload] = None
):
    target_id = (device_id or (body.device_id if body else None) or "").strip()
    target_name = (new_name or (body.new_name if body else None) or "").strip()

    if not target_id or not target_name:
        raise HTTPException(status_code=400, detail="Please enter a valid device name.")

    success = rename_device(target_id, target_name)
    if not success:
        raise HTTPException(status_code=404, detail="This device could not be found in the Hub.")

    return {
        "status": "ok",
        "message": f"Device renamed to '{target_name}'",
        "device_id": target_id,
        "new_name": target_name
    }


@app.post("/api/device/delete", dependencies=[Depends(require_localhost)])
def api_delete_device(
    device_id: Optional[str] = Query(None),
    body: Optional[DeviceDeletePayload] = None
):
    target_id = (device_id or (body.device_id if body else None) or "").strip()

    if not target_id:
        raise HTTPException(status_code=400, detail="No device was selected for removal.")

    success = delete_device(target_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device was already removed or not found.")

    return {
        "status": "ok",
        "message": "Device and its recorded sessions have been removed.",
        "device_id": target_id
    }


@app.get("/api/tv/status")
def get_tv_status():
    if _tv_sensor_ref:
        return {"tvs": _tv_sensor_ref.get_status_summary()}
    return {"tvs": []}


@app.post("/api/tv/scan", dependencies=[Depends(require_localhost)])
def scan_tvs(lan_ip: Optional[str] = None):
    ip_to_scan = lan_ip or get_lan_ip()
    if _tv_sensor_ref:
        discovered = _tv_sensor_ref.scan_network_for_tvs(ip_to_scan)
        return {
            "status": "ok",
            "message": f"Wi-Fi scan complete. Found {len(discovered)} Smart TV device(s).",
            "discovered": discovered,
            "count": len(discovered)
        }
    return {"status": "ok", "message": "TV monitor is currently inactive.", "discovered": [], "count": 0}


@app.post("/api/tv/add", dependencies=[Depends(require_localhost)])
def add_tv_manually(payload: ManualTVPayload):
    ip = payload.ip_address.strip()
    if not IPV4_RE.match(ip):
        raise HTTPException(status_code=400, detail="Please enter a valid IPv4 address (for example, 192.168.1.50).")
    if not _tv_sensor_ref:
        raise HTTPException(status_code=503, detail="Smart TV monitor is not initialized.")
    entry = _tv_sensor_ref.add_manual_tv(payload.device_name or "", ip)
    return {
        "status": "ok",
        "message": f"Added '{entry['device_name']}' for automatic presence monitoring.",
        "tv": entry
    }


@app.post("/api/shutdown", dependencies=[Depends(require_localhost)])
def request_hub_shutdown():
    if _shutdown_callback:
        threading.Timer(0.2, _shutdown_callback).start()
    return {"status": "ok", "message": "Shutting down OmniScreen Reality Hub."}
