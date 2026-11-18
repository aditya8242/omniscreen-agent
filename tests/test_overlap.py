import pytest
from hub.overlap import (
    merge_intervals,
    total_interval_seconds,
    intersect_intervals,
    compute_reality,
    format_duration
)

def test_format_duration():
    assert format_duration(0) == "0m"
    assert format_duration(59) == "1m"
    assert format_duration(3600) == "1h 0m"
    assert format_duration(3660) == "1h 1m"
    assert format_duration(7200) == "2h 0m"

def test_merge_intervals_disjoint():
    intervals = [(100.0, 200.0), (300.0, 400.0)]
    merged = merge_intervals(intervals)
    assert len(merged) == 2
    assert merged[0] == (100.0, 200.0)
    assert merged[1] == (300.0, 400.0)
    assert total_interval_seconds(merged) == 200.0

def test_merge_intervals_overlapping():
    # 100 to 250, and 200 to 350 -> union is 100 to 350 (250s)
    intervals = [(100.0, 250.0), (200.0, 350.0)]
    merged = merge_intervals(intervals)
    assert len(merged) == 1
    assert merged[0] == (100.0, 350.0)
    assert total_interval_seconds(merged) == 250.0

def test_merge_intervals_subset():
    # 100 to 500, and 200 to 300 -> union is 100 to 500
    intervals = [(100.0, 500.0), (200.0, 300.0)]
    merged = merge_intervals(intervals)
    assert len(merged) == 1
    assert merged[0] == (100.0, 500.0)
    assert total_interval_seconds(merged) == 400.0

def test_intersect_intervals():
    # Primary (PC): 1000 to 2000
    # Mobile (Phone): 1500 to 2500
    # Overlap should be 1500 to 2000 (500s)
    primary = [(1000.0, 2000.0)]
    mobile = [(1500.0, 2500.0)]
    intersections = intersect_intervals(primary, mobile)
    assert len(intersections) == 1
    assert intersections[0] == (1500.0, 2000.0)
    assert total_interval_seconds(intersections) == 500.0

def test_intersect_intervals_multiple():
    # Primary: [100, 200], [300, 400]
    # Mobile: [50, 150], [350, 500]
    # Intersections: [100, 150] (50s) and [350, 400] (50s) -> total 100s
    primary = [(100.0, 200.0), (300.0, 400.0)]
    mobile = [(50.0, 150.0), (350.0, 500.0)]
    intersections = intersect_intervals(primary, mobile)
    assert len(intersections) == 2
    assert intersections[0] == (100.0, 150.0)
    assert intersections[1] == (350.0, 400.0)
    assert total_interval_seconds(intersections) == 100.0

def test_compute_reality_end_to_end():
    day_start = 1000.0
    day_end = 5000.0
    
    sessions = [
        # PC: 1000 to 2000 (1000s)
        {"device_id": "pc1", "device_name": "Workstation PC", "device_type": "pc", "start_ts": 1000.0, "end_ts": 2000.0, "app_name": "VS Code"},
        # Phone: 1500 to 2500 (1000s)
        {"device_id": "phone1", "device_name": "Pixel 8", "device_type": "android", "start_ts": 1500.0, "end_ts": 2500.0, "app_name": "WhatsApp"},
        # TV: 3000 to 4000 (1000s)
        {"device_id": "tv1", "device_name": "Living Room TV", "device_type": "tv", "start_ts": 3000.0, "end_ts": 4000.0, "app_name": "Netflix"}
    ]
    
    res = compute_reality(sessions, day_start, day_end, "2026-11-17")
    
    # Raw total = 1000 (PC) + 1000 (Phone) + 1000 (TV) = 3000s
    assert res["raw_total_seconds"] == 3000.0
    
    # True exposure (union):
    # [1000, 2500] (1500s) + [3000, 4000] (1000s) = 2500s
    assert res["true_exposure_seconds"] == 2500.0
    
    # Second-screening overlap (intersection of [PC + TV] and [Phone]):
    # Primary = [1000, 2000] + [3000, 4000]
    # Mobile = [1500, 2500]
    # Intersection = [1500, 2000] = 500s
    assert res["second_screening_seconds"] == 500.0
    
    # 3 distinct devices
    assert res["device_count"] == 3
