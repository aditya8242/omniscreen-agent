from typing import List, Tuple, Dict, Any

_LEGACY_EXE_MAP = {
    "msedge.exe": "Microsoft Edge",
    "chrome.exe": "Google Chrome",
    "brave.exe": "Brave",
    "firefox.exe": "Firefox",
    "code.exe": "VS Code",
    "antigravity.exe": "Antigravity",
    "windowsterminal.exe": "Terminal",
    "powershell.exe": "PowerShell",
    "pwsh.exe": "PowerShell",
    "cmd.exe": "Command Prompt",
    "explorer.exe": "File Explorer",
    "spotify.exe": "Spotify",
    "discord.exe": "Discord",
    "whatsapp.exe": "WhatsApp",
}

def _clean_app_display_name(app_name: str, dev_type: str) -> str:
    clean = (app_name or "Unknown").strip()
    if dev_type == "pc":
        low = clean.lower()
        if low in _LEGACY_EXE_MAP:
            return _LEGACY_EXE_MAP[low]
        if low.endswith(".exe"):
            stripped = clean[:-4]
            return stripped.capitalize() if stripped.islower() else stripped
    return clean or "Unknown"

def format_duration(seconds: float) -> str:
    s = max(0.0, float(seconds or 0.0))
    if s < 30.0:
        return "0m"
    total_minutes = int(round(s / 60.0))
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def merge_intervals(intervals: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    if not intervals:
        return []
    
    # Filter invalid intervals and sort by start timestamp
    valid = [(s, e) for s, e in intervals if e > s]
    if not valid:
        return []
        
    sorted_intervals = sorted(valid, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    
    for curr_start, curr_end in sorted_intervals[1:]:
        prev_start, prev_end = merged[-1]
        if curr_start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, curr_end))
        else:
            merged.append((curr_start, curr_end))
            
    return merged

def total_interval_seconds(intervals: List[Tuple[float, float]]) -> float:
    return sum(end - start for start, end in intervals)

def intersect_intervals(
    intervals_a: List[Tuple[float, float]],
    intervals_b: List[Tuple[float, float]]
) -> List[Tuple[float, float]]:
    merged_a = merge_intervals(intervals_a)
    merged_b = merge_intervals(intervals_b)
    
    intersections: List[Tuple[float, float]] = []
    i = 0
    j = 0
    
    while i < len(merged_a) and j < len(merged_b):
        a_start, a_end = merged_a[i]
        b_start, b_end = merged_b[j]
        
        start = max(a_start, b_start)
        end = min(a_end, b_end)
        
        if start < end:
            intersections.append((start, end))
            
        if a_end < b_end:
            i += 1
        else:
            j += 1
            
    return intersections

def compute_reality(
    sessions: List[Dict[str, Any]],
    day_start_ts: float,
    day_end_ts: float,
    date_str: str = ""
) -> Dict[str, Any]:
    device_data: Dict[str, Dict[str, Any]] = {}
    all_intervals: List[Tuple[float, float]] = []
    primary_intervals: List[Tuple[float, float]] = []
    mobile_intervals: List[Tuple[float, float]] = []
    
    for s in sessions:
        s_start = float(s["start_ts"])
        s_end = float(s["end_ts"])
        
        # Clamp to day boundary
        start = max(day_start_ts, s_start)
        end = min(day_end_ts, s_end)
        
        if end <= start:
            continue
            
        dev_id = str(s["device_id"])
        dev_type = str(s.get("device_type", "pc")).lower()
        dev_name = str(s.get("device_name", dev_id))
        app_name = _clean_app_display_name(str(s.get("app_name", "Unknown")), dev_type)
        
        if dev_id not in device_data:
            device_data[dev_id] = {
                "device_id": dev_id,
                "device_name": dev_name,
                "device_type": dev_type,
                "intervals": [],
                "app_durations": {}
            }
            
        device_data[dev_id]["intervals"].append((start, end))
        dur = end - start
        current_app_sec = device_data[dev_id]["app_durations"].get(app_name, 0.0)
        device_data[dev_id]["app_durations"][app_name] = current_app_sec + dur
        
        all_intervals.append((start, end))
        if dev_type in ("pc", "tv"):
            primary_intervals.append((start, end))
        elif dev_type in ("android", "ios"):
            mobile_intervals.append((start, end))

    # 1. Per-device merged totals and top apps
    devices_summary = []
    raw_total_seconds = 0.0
    
    for dev_id, d in sorted(device_data.items(), key=lambda x: x[1]["device_name"]):
        merged_dev = merge_intervals(d["intervals"])
        dev_active_sec = total_interval_seconds(merged_dev)
        raw_total_seconds += dev_active_sec
        
        sorted_apps = sorted(d["app_durations"].items(), key=lambda x: x[1], reverse=True)
        top_apps = [
            {"app_name": app, "seconds": sec, "formatted": format_duration(sec)}
            for app, sec in sorted_apps[:5]
        ]
        
        devices_summary.append({
            "device_id": dev_id,
            "device_name": d["device_name"],
            "device_type": d["device_type"],
            "seconds": dev_active_sec,
            "formatted": format_duration(dev_active_sec),
            "top_apps": top_apps
        })
        
    # 2. True Exposure (Interval Union across all devices)
    merged_all = merge_intervals(all_intervals)
    true_exposure_seconds = total_interval_seconds(merged_all)
    
    # 3. Second-Screening Overlap (Primary Screens vs Mobile Screens)
    second_screening_intersections = intersect_intervals(primary_intervals, mobile_intervals)
    second_screening_seconds = total_interval_seconds(second_screening_intersections)
    
    # 4. Second-Screening Index (SSI) & Cognitive Fragmentation Model (from Deep Research)
    if true_exposure_seconds > 0:
        ssi_percent = round(((raw_total_seconds - true_exposure_seconds) / true_exposure_seconds) * 100.0, 1)
    else:
        ssi_percent = 0.0

    if ssi_percent < 10.0:
        ssi_status = "Optimal Focus"
        ssi_description = "Low attention fragmentation. Devices were used primarily sequentially."
        ssi_color = "#30D158"
    elif ssi_percent <= 25.0:
        ssi_status = "Moderate Second-Screening"
        ssi_description = "Occasional simultaneous multitasking across phone and primary screens."
        ssi_color = "#FF9F0A"
    else:
        ssi_status = "High Attention Fragmentation"
        ssi_description = "Significant simultaneous screen multitasking and dopamine switching."
        ssi_color = "#FF453A"
    
    return {
        "date": date_str,
        "true_exposure_seconds": true_exposure_seconds,
        "true_exposure_formatted": format_duration(true_exposure_seconds),
        "raw_total_seconds": raw_total_seconds,
        "raw_total_formatted": format_duration(raw_total_seconds),
        "second_screening_seconds": second_screening_seconds,
        "second_screening_formatted": format_duration(second_screening_seconds),
        "ssi_percent": ssi_percent,
        "ssi_status": ssi_status,
        "ssi_description": ssi_description,
        "ssi_color": ssi_color,
        "devices": devices_summary,
        "device_count": len(devices_summary)
    }
