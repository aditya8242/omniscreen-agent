import socket
import threading
import logging
from typing import Optional
from hub.network import get_active_lan_ip

logger = logging.getLogger("OmniDiscovery")

class UDPDiscoveryResponder:
    """
    Lightweight UDP broadcast beacon responder.
    Listens on UDP port 8766 for 'OMNISCREEN_DISCOVER' packets from mobile agents,
    and immediately replies with the PC Hub's live LAN IP and HTTP port.
    Enables zero-configuration, 1-tap mobile pairing over local Wi-Fi.
    """
    def __init__(self, hub_port: int = 8765, discovery_port: int = 8766, lan_ip: Optional[str] = None):
        self.hub_port = hub_port
        self.discovery_port = discovery_port
        self._pinned_lan_ip = lan_ip
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None

    @property
    def lan_ip(self) -> str:
        return self._pinned_lan_ip or get_active_lan_ip()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"UDP Auto-Discovery responder listening on UDP port {self.discovery_port}")

    def _run_loop(self):
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind(("0.0.0.0", self.discovery_port))
            self._socket.settimeout(2.0)
        except Exception as e:
            logger.error(f"Failed to bind UDP discovery port {self.discovery_port}: {e}")
            self._running = False
            return

        hostname = socket.gethostname()

        while self._running:
            try:
                data, addr = self._socket.recvfrom(1024)
                message = data.decode("utf-8", errors="ignore").strip()
                if message.startswith("OMNISCREEN_DISCOVER"):
                    reply = f"OMNISCREEN_OFFER|{self.lan_ip}|{self.hub_port}|{hostname}"
                    self._socket.sendto(reply.encode("utf-8"), addr)
                    logger.info(f"Answered discovery probe from {addr[0]}:{addr[1]} -> Offered {self.lan_ip}:{self.hub_port}")
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    logger.debug(f"Discovery socket error: {e}")
                break

        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass

    def stop(self):
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1.0)
