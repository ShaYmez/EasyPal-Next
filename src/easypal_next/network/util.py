"""Network utilities for LAN gallery access."""

from __future__ import annotations

import socket


def get_primary_lan_ip() -> str | None:
    """Return the primary IPv4 address used for outbound LAN traffic."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # Does not send packets; used to pick the outbound interface.
            sock.connect(("192.168.1.1", 1))
            return sock.getsockname()[0]
    except OSError:
        pass

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                return ip
    except OSError:
        return None
    return None


def preferred_gallery_url(port: int) -> str:
    """Return LAN gallery URL when available, otherwise localhost."""
    local, lan = gallery_urls(port)
    return lan or local


def gallery_urls(port: int) -> tuple[str, str | None]:
    """Return (localhost_url, lan_url_or_none)."""
    local = f"http://localhost:{port}"
    lan_ip = get_primary_lan_ip()
    lan = f"http://{lan_ip}:{port}" if lan_ip else None
    return local, lan
