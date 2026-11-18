from agents.win32_agent import Win32ScreenAgent, resolve_friendly_exe_name


def test_friendly_exe_names():
    assert resolve_friendly_exe_name("msedge.exe") == "Microsoft Edge"
    assert resolve_friendly_exe_name("Code.exe") == "VS Code"
    assert resolve_friendly_exe_name("WindowsTerminal.exe") == "Terminal"
    assert resolve_friendly_exe_name("mytool.exe") == "Mytool"


def test_sleep_hibernation_gap_does_not_inflate_time(monkeypatch):
    agent = Win32ScreenAgent(poll_interval=2.0, idle_threshold_seconds=120.0, flush_interval_seconds=9999.0)
    flushed = []
    monkeypatch.setattr(agent, "flush_now", lambda: flushed.append(list(agent._buffer)) or 0)
    monkeypatch.setattr(agent, "_is_workstation_locked", lambda: False)
    monkeypatch.setattr(agent, "_get_idle_seconds", lambda: 0.0)
    monkeypatch.setattr(agent, "_get_foreground_raw_exe", lambda: "chrome.exe")

    fake_now = [1000.0]
    monkeypatch.setattr("agents.win32_agent.time.time", lambda: fake_now[0])

    # Active at t=1000..1010 (10s of Chrome)
    agent.tick()
    fake_now[0] = 1010.0
    agent.tick()

    # Laptop sleeps for 4 hours (14400s), wakes at t=15410
    fake_now[0] = 15410.0
    agent.tick()

    assert len(agent._buffer) == 1
    iv = agent._buffer[0]
    assert iv["app_name"] == "Google Chrome"
    assert iv["start_ts"] == 1000.0
    assert iv["end_ts"] == 1010.0  # Strictly capped at pre-sleep moment, NOT 15410!


def test_lock_screen_pauses_tracking_immediately(monkeypatch):
    agent = Win32ScreenAgent(poll_interval=2.0, idle_threshold_seconds=120.0, flush_interval_seconds=9999.0)
    monkeypatch.setattr(agent, "flush_now", lambda: 0)
    monkeypatch.setattr(agent, "_get_idle_seconds", lambda: 0.0)

    locked = [False]
    raw_exe = ["Code.exe"]
    monkeypatch.setattr(agent, "_is_workstation_locked", lambda: locked[0])
    monkeypatch.setattr(agent, "_get_foreground_raw_exe", lambda: raw_exe[0])

    fake_now = [2000.0]
    monkeypatch.setattr("agents.win32_agent.time.time", lambda: fake_now[0])

    agent.tick()
    fake_now[0] = 2010.0
    agent.tick()
    fake_now[0] = 2020.0
    agent.tick()
    fake_now[0] = 2030.0
    locked[0] = True
    raw_exe[0] = "LockApp.exe"
    agent.tick()

    assert agent._is_idle is True
    assert len(agent._buffer) == 1
    assert agent._buffer[0]["app_name"] == "VS Code"
    assert agent._buffer[0]["end_ts"] - agent._buffer[0]["start_ts"] == 30.0
