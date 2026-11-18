import json
import socket
import time
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("TVSensor")

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

TV_PORT_PROFILES = {
    8001: "Samsung Smart TV",
    8002: "Samsung Smart TV (SSL)",
    3000: "LG webOS Smart TV",
    3001: "LG webOS Smart TV (SSL)",
    8060: "Roku TV / Player",
    7000: "Apple TV (AirPlay)",
    5000: "Apple TV (AirTunes)",
    8008: "Android TV / Chromecast",
    8009: "Android TV / Chromecast (SSL)",
    6466: "Android TV Remote",
    80: "Smart TV / Media Player (DLNA)"
}

def load_or_create_config(path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        default_cfg = {"smart_tvs": []}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default_cfg, f, indent=2)
        return default_cfg
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading TV config: {e}. Using empty.")
        return {"smart_tvs": []}

def save_config(config_data: Dict[str, Any], path: Path = DEFAULT_CONFIG_PATH):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving TV config: {e}")

class SmartTVSensor:
    def __init__(
        self,
        hub_url: str = "http://127.0.0.1:8765",
        config_path: Path = DEFAULT_CONFIG_PATH,
        check_interval_seconds: float = 15.0
    ):
        self.hub_url = hub_url.rstrip("/")
        self.config_path = config_path
        self.check_interval_sec = check_interval_seconds
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # State tracking: device_id -> {"device_name": str, "ip_address": str, "is_online": bool, "session_start": float, "last_seen": float}
        self._tv_states: Dict[str, Dict[str, Any]] = {}
        self._completed_sessions: List[Dict[str, Any]] = []

    def _is_host_reachable(self, ip: str, ports: List[int], timeout: float = 0.8) -> bool:
        for port in ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    if s.connect_ex((ip, port)) == 0:
                        return True
            except Exception:
                continue
        return False

    def check_tvs(self):
        config = load_or_create_config(self.config_path)
        tvs = config.get("smart_tvs", [])
        now = time.time()
        
        for tv in tvs:
            dev_id = tv.get("device_id")
            dev_name = tv.get("device_name", dev_id)
            ip = tv.get("ip_address")
            ports = tv.get("check_ports", [8001, 3000, 8060, 8008, 7000, 80])
            
            if not dev_id or not ip:
                continue
                
            is_online = self._is_host_reachable(ip, ports)
            
            with self._lock:
                state = self._tv_states.get(dev_id)
                if state is None:
                    self._tv_states[dev_id] = {
                        "device_name": dev_name,
                        "ip_address": ip,
                        "is_online": is_online,
                        "session_start": now if is_online else None,
                        "last_seen": now if is_online else None
                    }
                    if is_online:
                        logger.info(f"Smart TV detected online: {dev_name} ({ip})")
                    continue
                
                prev_online = state["is_online"]
                if is_online:
                    state["last_seen"] = now
                    if not prev_online:
                        state["is_online"] = True
                        state["session_start"] = now
                        logger.info(f"Smart TV powered ON: {dev_name} ({ip})")
                else:
                    if prev_online:
                        state["is_online"] = False
                        start = state.get("session_start")
                        last = state.get("last_seen") or now
                        if start and last > start + 5.0:
                            self._completed_sessions.append({
                                "device_id": dev_id,
                                "device_name": dev_name,
                                "device_type": "tv",
                                "start_ts": round(start, 2),
                                "end_ts": round(last, 2),
                                "app_name": "Smart TV Streaming",
                                "category": "screen_on"
                            })
                            logger.info(f"Smart TV powered OFF: {dev_name} (Duration: {last - start:.0f}s)")
                        state["session_start"] = None

    def _ssdp_discover_tvs(self, timeout: float = 1.6) -> List[Dict[str, Any]]:
        """
        Sends an SSDP M-SEARCH multicast probe for DIAL/Smart TV services on the LAN.
        Finds Samsung, LG, Sony Bravia, Fire TV, Roku, and Android TV devices that advertise UPnP.
        """
        found: Dict[str, Dict[str, Any]] = {}
        msg = (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1900\r\n"
            "MAN: \"ssdp:discover\"\r\n"
            "MX: 1\r\n"
            "ST: urn:dial-multiscreen-org:service:dial:1\r\n\r\n"
        ).encode("utf-8")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(timeout)
                sock.sendto(msg, ("239.255.255.250", 1900))
                deadline = time.time() + timeout
                while time.time() < deadline:
                    try:
                        data, addr = sock.recvfrom(2048)
                        ip = addr[0]
                        if ip in found or ip.startswith("127."):
                            continue
                        text = data.decode("utf-8", errors="ignore")
                        server_line = ""
                        for line in text.splitlines():
                            if line.lower().startswith("server:"):
                                server_line = line.split(":", 1)[1].strip()
                                break
                        label = "Smart TV"
                        low = (server_line + " " + text).lower()
                        if "samsung" in low or "tizen" in low:
                            label = "Samsung Smart TV"
                        elif "webos" in low or "lge" in low:
                            label = "LG webOS Smart TV"
                        elif "roku" in low:
                            label = "Roku TV"
                        elif "android" in low or "chromecast" in low or "google" in low or "bravia" in low:
                            label = "Android TV / Cast"
                        elif "fire" in low or "amazon" in low:
                            label = "Fire TV"
                        found[ip] = {
                            "device_id": f"tv_{ip.replace('.', '_')}",
                            "device_name": f"{label} ({ip})",
                            "ip_address": ip,
                            "check_ports": [8001, 8002, 3000, 8060, 8008, 8009, 7000, 80]
                        }
                    except socket.timeout:
                        break
        except Exception as e:
            logger.debug(f"SSDP discovery skipped or unavailable: {e}")
        return list(found.values())

    def add_manual_tv(self, device_name: str, ip_address: str) -> Dict[str, Any]:
        clean_ip = ip_address.strip()
        clean_name = (device_name or "").strip() or f"Smart TV ({clean_ip})"
        entry = {
            "device_id": f"tv_{clean_ip.replace('.', '_')}",
            "device_name": clean_name,
            "ip_address": clean_ip,
            "check_ports": [8001, 8002, 3000, 3001, 8060, 8008, 8009, 7000, 80]
        }
        cfg = load_or_create_config(self.config_path)
        tvs = cfg.setdefault("smart_tvs", [])
        tvs = [t for t in tvs if t.get("ip_address") != clean_ip]
        tvs.append(entry)
        cfg["smart_tvs"] = tvs
        save_config(cfg, self.config_path)
        self.check_tvs()
        return entry

    def scan_network_for_tvs(self, lan_ip: str) -> List[Dict[str, Any]]:
        """
        Actively probes the local Wi-Fi subnet via SSDP multicast + Smart TV TCP ports.
        Returns a list of discovered TV candidates.
        """
        parts = lan_ip.split(".")
        if len(parts) != 4 or lan_ip.startswith("127."):
            return []

        discovered_by_ip: Dict[str, Dict[str, Any]] = {}

        # 1. SSDP DIAL Multicast Discovery
        for tv in self._ssdp_discover_tvs():
            if tv["ip_address"] != lan_ip:
                discovered_by_ip[tv["ip_address"]] = tv

        # 2. Subnet Smart TV Port Sweep
        subnet_prefix = f"{parts[0]}.{parts[1]}.{parts[2]}."
        common_ports = [8001, 8002, 3000, 3001, 8060, 8008, 8009, 7000]

        def probe_ip(host_num: int):
            target_ip = f"{subnet_prefix}{host_num}"
            if target_ip == lan_ip or target_ip in discovered_by_ip:
                return None
            for port in common_ports:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(0.22)
                        if s.connect_ex((target_ip, port)) == 0:
                            brand = TV_PORT_PROFILES.get(port, "Smart TV")
                            return {
                                "device_id": f"tv_{target_ip.replace('.', '_')}",
                                "device_name": f"{brand} ({target_ip})",
                                "ip_address": target_ip,
                                "check_ports": [port, 80]
                            }
                except Exception:
                    continue
            return None

        with ThreadPoolExecutor(max_workers=48) as executor:
            results = executor.map(probe_ip, range(1, 255))
            for res in results:
                if res:
                    discovered_by_ip[res["ip_address"]] = res

        discovered = list(discovered_by_ip.values())

        # Auto-merge discovered TVs into config.json and refresh status immediately
        if discovered:
            cfg = load_or_create_config(self.config_path)
            existing_ips = {tv.get("ip_address") for tv in cfg.get("smart_tvs", [])}
            added = False
            for disc in discovered:
                if disc["ip_address"] not in existing_ips:
                    cfg.setdefault("smart_tvs", []).append(disc)
                    added = True
            if added:
                save_config(cfg, self.config_path)
                logger.info(f"Auto-registered {len(discovered)} Smart TVs to configuration.")
            self.check_tvs()

        return discovered

    def get_status_summary(self) -> List[Dict[str, Any]]:
        with self._lock:
            summary = []
            for did, st in self._tv_states.items():
                summary.append({
                    "device_id": did,
                    "device_name": st["device_name"],
                    "ip_address": st.get("ip_address", "Unknown"),
                    "is_online": st["is_online"],
                    "status_label": "Active (Streaming)" if st["is_online"] else "Standby (Screen Off)"
                })
            return summary

    def flush_now(self) -> int:
        now = time.time()
        sessions_to_push = []
        
        with self._lock:
            for dev_id, state in self._tv_states.items():
                if state["is_online"] and state.get("session_start"):
                    start = state["session_start"]
                    if now > start + 5.0:
                        sessions_to_push.append({
                            "device_id": dev_id,
                            "device_name": state["device_name"],
                            "device_type": "tv",
                            "start_ts": round(start, 2),
                            "end_ts": round(now, 2),
                            "app_name": "Smart TV Streaming",
                            "category": "screen_on"
                        })
                        state["session_start"] = now
                        
            sessions_to_push.extend(self._completed_sessions)
            self._completed_sessions.clear()

        if not sessions_to_push:
            return 0

        grouped: Dict[str, Dict[str, Any]] = {}
        for s in sessions_to_push:
            did = s["device_id"]
            if did not in grouped:
                grouped[did] = {
                    "device_id": did,
                    "device_name": s["device_name"],
                    "device_type": "tv",
                    "sessions": []
                }
            grouped[did]["sessions"].append({
                "start_ts": s["start_ts"],
                "end_ts": s["end_ts"],
                "app_name": s["app_name"],
                "category": s["category"]
            })

        total_synced = 0
        for did, payload in grouped.items():
            try:
                res = requests.post(f"{self.hub_url}/api/sync", json=payload, timeout=2.5)
                if res.status_code == 200:
                    total_synced += len(payload["sessions"])
            except Exception as e:
                logger.warning(f"Failed to sync TV sessions for {did}: {e}")

        return total_synced

    def run_loop(self):
        logger.info(f"Smart TV Sensor started. Checking network presence every {self.check_interval_sec}s")
        self._running = True
        try:
            while self._running:
                self.check_tvs()
                self.flush_now()
                time.sleep(self.check_interval_sec)
        finally:
            self.flush_now()
            logger.info("Smart TV Sensor stopped.")

    def start_background(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.5)
