"""Tests for configuration management."""

import pytest
import json
import tempfile
from pathlib import Path

from src.utils.config import Config


class TestConfig:
    """Test cases for Config class."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "memory-vault"
            config_dir.mkdir()
            yield config_dir
    
    @pytest.fixture
    def mock_config(self, temp_config_dir, monkeypatch):
        """Create a Config instance with temporary directory."""
        monkeypatch.setattr(Config, "CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr(Config, "CONFIG_FILE", temp_config_dir / "config.json")
        return Config()
    
    def test_default_config_structure(self, mock_config):
        """Test that default config has correct structure."""
        assert "storage" in mock_config._config
        assert "devices" in mock_config._config
        assert "security" in mock_config._config
        assert "ui" in mock_config._config
    
    def test_get_value(self, mock_config):
        """Test getting configuration values."""
        mock_config.set("storage.bucket", "test-bucket")
        assert mock_config.get("storage.bucket") == "test-bucket"
    
    def test_get_nested_value(self, mock_config):
        """Test getting nested configuration values."""
        mock_config.set("storage.region", "eu-west-1")
        assert mock_config.get("storage.region") == "eu-west-1"
    
    def test_get_default_value(self, mock_config):
        """Test getting default value for missing key."""
        assert mock_config.get("nonexistent.key", "default") == "default"
    
    def test_set_value(self, mock_config):
        """Test setting configuration values."""
        mock_config.set("test.key", "test-value")
        assert mock_config.get("test.key") == "test-value"
    
    def test_save_and_load(self, mock_config):
        """Test saving and loading configuration."""
        mock_config.set("storage.bucket", "my-bucket")
        mock_config.save()
        
        # Create new instance to test loading
        new_config = Config()
        assert new_config.get("storage.bucket") == "my-bucket"
    
    def test_is_configured(self, mock_config):
        """Test configuration status check."""
        assert not mock_config.is_configured()
        
        mock_config.set("storage.bucket", "test")
        mock_config.set("storage.access_key", "key")
        mock_config.set("storage.secret_key", "secret")
        
        assert mock_config.is_configured()
    
    def test_device_config(self, mock_config):
        """Test device-specific configuration."""
        device_config = mock_config.get_device_config("test-host")
        assert "sync_folders" in device_config
        assert "last_snap" in device_config
    
    def test_update_device_config(self, mock_config):
        """Test updating device configuration."""
        new_config = {
            "sync_folders": ["/test/path"],
            "last_snap": "2026-04-25T10:00:00"
        }
        mock_config.update_device_config("test-host", new_config)
        
        retrieved = mock_config.get_device_config("test-host")
        assert retrieved["sync_folders"] == ["/test/path"]
