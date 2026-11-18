import sqlite3
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "omniscreen.db"

def get_db_path(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        p = Path(custom_path)
    elif os.environ.get("OMNISCREEN_DB_PATH"):
        p = Path(os.environ["OMNISCREEN_DB_PATH"])
    else:
        p = DEFAULT_DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = get_db_path(db_path)
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn

def init_db(db_path: Optional[str] = None):
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_name TEXT NOT NULL,
                device_type TEXT NOT NULL,
                last_sync_ts REAL NOT NULL,
                custom_name_locked INTEGER NOT NULL DEFAULT 0
            )
            """)
            # Safe schema migration for existing databases
            cols = {row[1] for row in conn.execute("PRAGMA table_info(devices)").fetchall()}
            if "custom_name_locked" not in cols:
                conn.execute("ALTER TABLE devices ADD COLUMN custom_name_locked INTEGER NOT NULL DEFAULT 0")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                device_type TEXT NOT NULL,
                start_ts REAL NOT NULL,
                end_ts REAL NOT NULL,
                app_name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'screen_on',
                FOREIGN KEY (device_id) REFERENCES devices (device_id)
            )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_device ON sessions(device_id, start_ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_time ON sessions(start_ts, end_ts)")
    finally:
        conn.close()

def upsert_device(device_id: str, device_name: str, device_type: str, last_sync_ts: float, db_path: Optional[str] = None):
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("""
            INSERT INTO devices (device_id, device_name, device_type, last_sync_ts, custom_name_locked)
            VALUES (?, ?, ?, ?, 0)
            ON CONFLICT(device_id) DO UPDATE SET
                device_name = CASE
                    WHEN devices.custom_name_locked = 1 THEN devices.device_name
                    ELSE excluded.device_name
                END,
                device_type = excluded.device_type,
                last_sync_ts = excluded.last_sync_ts
            """, (device_id, device_name, device_type, last_sync_ts))
    finally:
        conn.close()

def insert_sessions_idempotent(
    device_id: str,
    device_name: str,
    device_type: str,
    sessions: List[Dict[str, Any]],
    replace_day_start_ts: Optional[float] = None,
    db_path: Optional[str] = None
) -> int:
    sync_now = time.time()
    upsert_device(device_id, device_name, device_type, sync_now, db_path=db_path)
    
    conn = get_connection(db_path)
    inserted_count = 0
    try:
        with conn:
            # Automatically deduplicate stale mobile records when an APK reinstall
            # generates a new signing-key-scoped device_id for the same phone name.
            if device_type in ("android", "ios") and device_name.strip():
                dups = conn.execute(
                    """
                    SELECT device_id FROM devices
                    WHERE device_type = ?
                      AND LOWER(TRIM(device_name)) = LOWER(TRIM(?))
                      AND device_id != ?
                    """,
                    (device_type, device_name, device_id)
                ).fetchall()
                for dup in dups:
                    old_id = dup["device_id"]
                    if replace_day_start_ts is not None:
                        conn.execute(
                            "DELETE FROM sessions WHERE device_id = ? AND start_ts >= ?",
                            (old_id, float(replace_day_start_ts))
                        )
                    conn.execute(
                        "UPDATE sessions SET device_id = ? WHERE device_id = ?",
                        (device_id, old_id)
                    )
                    conn.execute("DELETE FROM devices WHERE device_id = ?", (old_id,))

            if replace_day_start_ts is not None:
                conn.execute(
                    "DELETE FROM sessions WHERE device_id = ? AND start_ts >= ?",
                    (device_id, float(replace_day_start_ts))
                )
            
            rows = []
            for s in sessions:
                start_ts = float(s["start_ts"])
                end_ts = float(s["end_ts"])
                if end_ts <= start_ts:
                    continue
                app_name = str(s.get("app_name", "Unknown")).strip() or "Unknown"
                category = str(s.get("category", "screen_on")).strip() or "screen_on"
                rows.append((device_id, device_type, start_ts, end_ts, app_name, category))
            
            if rows:
                conn.executemany(
                    "INSERT INTO sessions (device_id, device_type, start_ts, end_ts, app_name, category) VALUES (?, ?, ?, ?, ?, ?)",
                    rows
                )
                inserted_count = len(rows)
    finally:
        conn.close()
        
    return inserted_count

def get_day_boundaries(date_str: Optional[str] = None) -> tuple[float, float, str]:
    if date_str:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        now = datetime.now()
        dt = datetime(now.year, now.month, now.day)
        
    start_dt = datetime(dt.year, dt.month, dt.day, 0, 0, 0)
    end_dt = datetime(dt.year, dt.month, dt.day, 23, 59, 59, 999999)
    day_str = start_dt.strftime("%Y-%m-%d")
    return start_dt.timestamp(), end_dt.timestamp(), day_str

def get_sessions_for_day(date_str: Optional[str] = None, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    start_ts, end_ts, _ = get_day_boundaries(date_str)
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.id, s.device_id, s.device_type, d.device_name, s.start_ts, s.end_ts, s.app_name, s.category
            FROM sessions s
            LEFT JOIN devices d ON s.device_id = d.device_id
            WHERE s.start_ts < ? AND s.end_ts > ?
            ORDER BY s.start_ts ASC
        """, (end_ts, start_ts))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "id": row["id"],
                "device_id": row["device_id"],
                "device_type": row["device_type"],
                "device_name": row["device_name"] or row["device_id"],
                "start_ts": row["start_ts"],
                "end_ts": row["end_ts"],
                "app_name": row["app_name"],
                "category": row["category"]
            })
        return results
    finally:
        conn.close()

def get_all_devices(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT device_id, device_name, device_type, last_sync_ts FROM devices ORDER BY device_name ASC")
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def rename_device(device_id: str, new_name: str, db_path: Optional[str] = None) -> bool:
    clean_name = new_name.strip()
    if not clean_name:
        return False
    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.execute(
                "UPDATE devices SET device_name = ?, custom_name_locked = 1 WHERE device_id = ?",
                (clean_name, device_id)
            )
            return cur.rowcount > 0
    finally:
        conn.close()

def delete_device(device_id: str, db_path: Optional[str] = None) -> bool:
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM sessions WHERE device_id = ?", (device_id,))
            cur = conn.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
            return cur.rowcount > 0
    finally:
        conn.close()
