"""Tests for hostname detection."""

import pytest

from src.core.hostname import get_hostname


class TestHostname:
    """Test cases for hostname detection."""
    
    def test_get_hostname(self):
        """Test that hostname is returned."""
        hostname = get_hostname()
        assert isinstance(hostname, str)
        assert len(hostname) > 0
        # Hostname should not contain spaces
        assert " " not in hostname
    
    def test_hostname_consistency(self):
        """Test that hostname is consistent across calls."""
        hostname1 = get_hostname()
        hostname2 = get_hostname()
        assert hostname1 == hostname2
