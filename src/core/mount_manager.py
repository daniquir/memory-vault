"""FUSE mount manager using rclone mount."""

import subprocess
import threading
import time
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List
from .binary_detector import BinaryDetector


class MountManager:
    """Manages FUSE mounting using rclone mount."""
    
    def __init__(self, config: dict, output_callback=None):
        """Initialize mount manager with configuration.
        
        Args:
            config: Configuration dictionary with Wasabi credentials
            output_callback: Optional callback function for output (receives line)
        """
        self.config = config
        self.output_callback = output_callback
        self.mount_process: Optional[subprocess.Popen] = None
        self.mount_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._ensure_dependencies()
    
    def _ensure_dependencies(self) -> None:
        """Ensure required dependencies are available."""
        if not BinaryDetector.check_binary("rclone"):
            success, msg = BinaryDetector.install_binary("rclone")
            if not success:
                raise RuntimeError(f"Failed to install rclone: {msg}")
        
        if not BinaryDetector.check_binary("fusermount3"):
            success, msg = BinaryDetector.install_binary("fuse3")
            if not success:
                raise RuntimeError(f"Failed to install fuse3: {msg}")
    
    def _get_env(self) -> dict:
        """Get environment variables for rclone with Wasabi credentials."""
        storage = self.config.get("storage", {})
        region = storage.get("sync_region", "us-east-1")
        
        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = storage.get("access_key", "")
        env["AWS_SECRET_ACCESS_KEY"] = storage.get("secret_key", "")
        env["AWS_ENDPOINT_URL_S3"] = f"https://{region}.wasabisys.com"
        
        return env
    
    def _create_rclone_config(self) -> str:
        """Create rclone config file with Wasabi configuration.
        
        Returns:
            Path to config file
        """
        storage = self.config.get("storage", {})
        bucket = storage.get("sync_bucket", "")
        region = storage.get("sync_region", "us-east-1")
        endpoint = f"s3.{region}.wasabisys.com"
        
        config_content = f"""[wasabi]
type = s3
provider = Wasabi
access_key_id = {storage.get("access_key", "")}
secret_access_key = {storage.get("secret_key", "")}
region = {region}
endpoint = https://{endpoint}
acl = private
"""
        
        # Use persistent config file in user's home directory
        config_dir = Path.home() / ".config" / "memory-vault"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "rclone.conf"
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        return str(config_path)
    
    def _get_rclone_mount_cmd(self, mount_point: str, config_path: str) -> List[str]:
        """Build rclone mount command."""
        storage = self.config.get("storage", {})
        bucket = storage.get("sync_bucket", "")

        return [
            "rclone",
            "--config",
            config_path,
            "mount",
            f"wasabi:{bucket}",
            mount_point,
            "--vfs-cache-mode",
            "full",
            "--daemon",
            "--log-level",
            "ERROR",
            "--no-check-certificate"
        ]
    
    def is_mounted(self, mount_point: str) -> bool:
        """Check if mount point is currently mounted.
        
        Args:
            mount_point: Path to check
        
        Returns:
            True if mounted, False otherwise
        """
        mount_path = Path(mount_point)
        if not mount_path.exists():
            return False
        
        try:
            result = subprocess.run(
                ["mountpoint", "-q", mount_point],
                capture_output=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            # mountpoint not available, try /proc/mounts
            try:
                with open("/proc/mounts", "r") as f:
                    return mount_point in f.read()
            except IOError:
                return False
    
    def mount(self, mount_point: str = "~/Vault") -> Tuple[bool, str]:
        """Mount Wasabi bucket to local directory.
        
        Args:
            mount_point: Local directory path (default: ~/Vault)
        
        Returns:
            Tuple of (success, message)
        """
        # Expand path
        mount_point = Path(mount_point).expanduser()
        
        # Check if already mounted
        if self.is_mounted(str(mount_point)):
            if self.output_callback:
                self.output_callback(f"Already mounted at {mount_point}")
            return True, f"Already mounted at {mount_point}"
        
        # Create mount point if it doesn't exist
        mount_point.mkdir(parents=True, exist_ok=True)
        
        # Create persistent config file
        config_path = self._create_rclone_config()
        
        # Get mount command
        cmd = self._get_rclone_mount_cmd(str(mount_point), config_path)
        
        if self.output_callback:
            self.output_callback(f"Mounting: {' '.join(cmd)}")
        
        try:
            # Run rclone mount
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if self.output_callback:
                self.output_callback(f"Mount command output: {result.stdout}")
                if result.stderr:
                    self.output_callback(f"Mount command stderr: {result.stderr}")
            
            # Wait a moment for mount to complete
            time.sleep(2)
            
            if self.is_mounted(str(mount_point)):
                # Force directory refresh by listing contents
                try:
                    subprocess.run(
                        ["ls", str(mount_point)],
                        capture_output=True,
                        timeout=5
                    )
                except:
                    pass
                
                if self.output_callback:
                    self.output_callback(f"Successfully mounted at {mount_point}")
                return True, f"Successfully mounted at {mount_point}"
            else:
                if self.output_callback:
                    self.output_callback("Mount command executed but mount point not available")
                return False, "Mount command executed but mount point not available"
                
        except subprocess.CalledProcessError as e:
            if self.output_callback:
                self.output_callback(f"Mount failed: {e.stderr}")
            return False, f"Mount failed: {e.stderr}"
    
    def mount_with_retry(self, mount_point: str = "~/Vault", max_retries: int = 3, retry_delay: int = 5) -> Tuple[bool, str]:
        """Mount with automatic retry on network failure.
        
        Args:
            mount_point: Local directory path
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        
        Returns:
            Tuple of (success, message)
        """
        for attempt in range(max_retries):
            success, message = self.mount(mount_point)
            if success:
                return True, message
            
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        return False, f"Failed to mount after {max_retries} attempts: {message}"
    
    def unmount(self, mount_point: str = "~/Vault") -> Tuple[bool, str]:
        """Unmount the vault.
        
        Args:
            mount_point: Local directory path
        
        Returns:
            Tuple of (success, message)
        """
        mount_point = Path(mount_point).expanduser()
        
        if not self.is_mounted(str(mount_point)):
            return True, f"Not mounted at {mount_point}"
        
        try:
            # Try fusermount first
            result = subprocess.run(
                ["fusermount3", "-u", str(mount_point)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return True, f"Successfully unmounted from {mount_point}"
            
            # Fallback to umount
            result = subprocess.run(
                ["umount", str(mount_point)],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return True, f"Successfully unmounted from {mount_point}"
            
            return False, f"Unmount failed: {result.stderr}"
            
        except FileNotFoundError:
            return False, "Neither fusermount3 nor umount found"
    
    def cleanup_cache(self, mount_point: str = "~/Vault") -> None:
        """Clean up FUSE cache after unmounting.
        
        Args:
            mount_point: Local directory path
        """
        mount_point = Path(mount_point).expanduser()
        
        # Remove cache directory if it exists
        cache_dir = Path.home() / ".cache" / "rclone"
        if cache_dir.exists():
            try:
                import shutil
                shutil.rmtree(cache_dir)
            except OSError:
                pass  # Cache cleanup is non-critical
    
    def get_mount_status(self, mount_point: str = "~/Vault") -> dict:
        """Get current mount status.
        
        Args:
            mount_point: Local directory path
        
        Returns:
            Dictionary with status information
        """
        mount_point = Path(mount_point).expanduser()
        
        return {
            "mounted": self.is_mounted(str(mount_point)),
            "mount_point": str(mount_point),
            "exists": mount_point.exists()
        }
