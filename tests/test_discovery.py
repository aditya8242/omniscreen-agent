import socket
import time
from hub.discovery import UDPDiscoveryResponder

def test_udp_discovery():
    responder = UDPDiscoveryResponder(hub_port=8765, discovery_port=8767, lan_ip="10.175.204.103")
    responder.start()
    time.sleep(0.2)

    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(2.0)
    client.sendto(b"OMNISCREEN_DISCOVER", ("127.0.0.1", 8767))

    data, addr = client.recvfrom(1024)
    response = data.decode("utf-8")
    client.close()
    responder.stop()

    assert response.startswith("OMNISCREEN_OFFER|10.175.204.103|8765|")
