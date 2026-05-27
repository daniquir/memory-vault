"""Configuration management for The Memory Vault."""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Manages configuration stored in ~/.config/memory-vault/."""
    
    CONFIG_DIR = Path.home() / ".config" / "memory-vault"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    
    def __init__(self):
        """Initialize configuration manager."""
        self._config: Dict[str, Any] = {}
        self._load()
    
    def _load(self) -> None:
        """Load configuration from file."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self._config = self._get_default_config()
        else:
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration structure."""
        return {
            "storage": {
                "provider": "wasabi",
                "sync_bucket": "",
                "vault_bucket": "",
                "access_key": "",
                "secret_key": "",
                "sync_region": "us-east-1",
                "vault_region": "us-east-1"
            },
            "snapshots": {
                "keep_last": 3,
                "auto_snap_interval": "daily"
            },
            "devices": {},
            "security": {
                "rm_shield": False,
                "encryption_password": ""
            },
            "ui": {
                "language": "auto",
                "start_minimized": True
            }
        }
    
    def save(self) -> None:
        """Save configuration to file."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot-separated key."""
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def is_configured(self) -> bool:
        """Check if at least one functionality (sync or snapshots) is configured."""
        return self.is_sync_configured() or self.is_snapshots_configured()

    def is_sync_configured(self) -> bool:
        """Check if sync functionality is configured."""
        storage = self._config.get("storage", {})
        return bool(
            storage.get("sync_bucket") and
            storage.get("access_key") and
            storage.get("secret_key")
        )

    def is_snapshots_configured(self) -> bool:
        """Check if snapshots functionality is configured."""
        storage = self._config.get("storage", {})
        security = self._config.get("security", {})
        return bool(
            storage.get("vault_bucket") and
            storage.get("access_key") and
            storage.get("secret_key") and
            security.get("encryption_password")
        )
    
    def get_device_config(self, hostname: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for specific device."""
        if hostname is None:
            import socket
            hostname = socket.gethostname()
        
        devices = self._config.get("devices", {})
        if hostname not in devices:
            devices[hostname] = {
                "sync_folders": [],
                "last_snap": None
            }
            self._config["devices"] = devices
            self.save()
        
        return devices[hostname]
    
    def update_device_config(self, hostname: str, config: Dict[str, Any]) -> None:
        """Update configuration for specific device."""
        if "devices" not in self._config:
            self._config["devices"] = {}
        self._config["devices"][hostname] = config
        self.save()
    
    def get_all_devices(self) -> Dict[str, Any]:
        """Get all registered devices."""
        return self._config.get("devices", {})
