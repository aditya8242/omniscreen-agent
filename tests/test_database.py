import pytest
import os
import tempfile
from hub.database import (
    init_db,
    insert_sessions_idempotent,
    get_sessions_for_day,
    get_all_devices
)

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_database_idempotent_sync(temp_db):
    day_start = 1731801600.0
    
    # First sync: 2 sessions
    sessions_v1 = [
        {"start_ts": day_start + 100, "end_ts": day_start + 500, "app_name": "Chrome"},
        {"start_ts": day_start + 600, "end_ts": day_start + 900, "app_name": "VS Code"}
    ]
    
    ins1 = insert_sessions_idempotent(
        device_id="pc_test",
        device_name="Test PC",
        device_type="pc",
        sessions=sessions_v1,
        replace_day_start_ts=day_start,
        db_path=temp_db
    )
    assert ins1 == 2
    
    # Verify devices
    devs = get_all_devices(db_path=temp_db)
    assert len(devs) == 1
    assert devs[0]["device_id"] == "pc_test"
    
    # Second sync: replaces day with 3 sessions (simulating phone or pc pushing updated timeline)
    sessions_v2 = [
        {"start_ts": day_start + 100, "end_ts": day_start + 500, "app_name": "Chrome"},
        {"start_ts": day_start + 600, "end_ts": day_start + 900, "app_name": "VS Code"},
        {"start_ts": day_start + 1000, "end_ts": day_start + 1500, "app_name": "Spotify"}
    ]
    ins2 = insert_sessions_idempotent(
        device_id="pc_test",
        device_name="Test PC",
        device_type="pc",
        sessions=sessions_v2,
        replace_day_start_ts=day_start,
        db_path=temp_db
    )
    assert ins2 == 3
    
    # Query sessions back
    # All sessions should equal exactly 3 (no duplicates!)
    from hub.database import get_connection
    conn = get_connection(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sessions WHERE device_id='pc_test'")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 3

def test_database_deduplicates_reinstalled_mobile(temp_db):
    day1_start = 1731715200.0
    day2_start = 1731801600.0

    # Old APK build syncs yesterday + earlier today with old device_id
    insert_sessions_idempotent(
        device_id="android_old11111",
        device_name="Galaxy F17 5G",
        device_type="android",
        sessions=[
            {"start_ts": day1_start + 100, "end_ts": day1_start + 500, "app_name": "Instagram"},
            {"start_ts": day2_start + 100, "end_ts": day2_start + 900, "app_name": "StaleWrong"}
        ],
        replace_day_start_ts=None,
        db_path=temp_db
    )

    # Reinstalled APK build syncs today with new device_id and same phone name
    insert_sessions_idempotent(
        device_id="android_new22222",
        device_name="Galaxy F17 5G",
        device_type="android",
        sessions=[
            {"start_ts": day2_start + 100, "end_ts": day2_start + 400, "app_name": "Instagram"}
        ],
        replace_day_start_ts=day2_start,
        db_path=temp_db
    )

    devs = get_all_devices(db_path=temp_db)
    assert len(devs) == 1
    assert devs[0]["device_id"] == "android_new22222"

    # Yesterday history preserved under new ID; stale today session replaced
    from hub.database import get_connection
    conn = get_connection(temp_db)
    rows = conn.execute("SELECT device_id, app_name FROM sessions ORDER BY start_ts ASC").fetchall()
    conn.close()
    assert len(rows) == 2
    assert all(r["device_id"] == "android_new22222" for r in rows)
    assert [r["app_name"] for r in rows] == ["Instagram", "Instagram"]
