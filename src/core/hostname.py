"""Hostname detection for device identification."""

import socket


def get_hostname() -> str:
    """Get the system hostname."""
    return socket.gethostname()
