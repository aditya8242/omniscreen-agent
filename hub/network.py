import socket


def get_active_lan_ip() -> str:
    """
    Detects the PC's currently active local Wi-Fi or Ethernet IPv4 address.
    Uses a non-sending UDP connect probe so zero packets leave the machine.
    Falls back safely to 127.0.0.1 only when completely offline.
    """
    candidates = ["10.255.255.255", "192.168.255.255", "172.31.255.255", "8.8.8.8"]
    for dest in candidates:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(0.4)
                s.connect((dest, 1))
                ip = s.getsockname()[0]
                if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                    return ip
        except Exception:
            continue
    return "127.0.0.1"
