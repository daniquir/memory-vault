"""Rclone wrapper for S3 sync operations."""

import subprocess
import shutil
import os
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple
from .binary_detector import BinaryDetector


class RcloneWrapper:
    """Wrapper for rclone commands."""
    
    def __init__(self, config: dict):
        """Initialize rclone wrapper with configuration.
        
        Args:
            config: Configuration dictionary with Wasabi credentials
        """
        self.config = config
        self._ensure_binary()
    
    def _ensure_binary(self) -> None:
        """Ensure rclone binary is available."""
        if not BinaryDetector.check_binary("rclone"):
            success, msg = BinaryDetector.install_binary("rclone")
            if not success:
                raise RuntimeError(f"Failed to install rclone: {msg}")
    
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
    
    def _get_rclone_cmd(self, operation: str, **kwargs) -> List[str]:
        """Build rclone command with configuration."""
        storage = self.config.get("storage", {})

        cmd = ["rclone", operation]

        if operation == "mount":
            # Mount-specific configuration
            bucket = storage.get("sync_bucket", "")
            region = storage.get("sync_region", "us-east-1")
            endpoint = f"{region}.wasabisys.com"

            cmd.extend([
                f":s3:{endpoint}/{bucket}",
                kwargs.get("mount_point", "~/Vault"),
                "--vfs-mode",
                "full",
                "--no-modtime",
                "--no-checksum",
                "--attr-timeout",
                "1s",
                "--dir-cache-time",
                "1s"
            ])
        elif operation == "sync":
            # Sync-specific configuration
            bucket = storage.get("sync_bucket", "")
            region = storage.get("sync_region", "us-east-1")
            endpoint = f"{region}.wasabisys.com"

            cmd.extend([
                kwargs.get("source", ""),
                f":s3:{endpoint}/{bucket}",
                "--progress"
            ])

        return cmd
    
    def get_sync_bucket(self) -> str:
        """Get the sync bucket name."""
        return self.config.get("storage", {}).get("sync_bucket", "")
    
    def sync_to_cloud(self, local_path: str, remote_path: str) -> Tuple[bool, str]:
        """Sync local directory to Wasabi S3.
        
        Args:
            local_path: Local directory path
            remote_path: Remote path in bucket (e.g., "folder")
        
        Returns:
            Tuple of (success, message)
        """
        storage = self.config.get("storage", {})
        bucket = storage.get("sync_bucket", "")
        
        # Create persistent config file
        config_path = self._create_rclone_config()
        
        try:
            cmd = [
                "rclone",
                "--config",
                config_path,
                "sync",
                local_path,
                f"wasabi:{bucket}/{remote_path}",
                "--progress"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"Sync failed: {e.stderr}"
    
    def sync_from_cloud(self, remote_path: str, local_path: str) -> Tuple[bool, str]:
        """Sync directory from Wasabi S3 to local.
        
        Args:
            remote_path: Remote path in bucket (e.g., "bucket:path")
            local_path: Local directory path
        
        Returns:
            Tuple of (success, message)
        """
        cmd = self._get_rclone_cmd() + [
            "sync",
            f":s3:{remote_path}",
            local_path,
            "--progress"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"Sync failed: {e.stderr}"
    
    def list_remote(self, remote_path: str) -> Tuple[bool, List[str]]:
        """List files in remote path.
        
        Args:
            remote_path: Remote path in bucket (e.g., "bucket:path")
        
        Returns:
            Tuple of (success, file_list)
        """
        cmd = self._get_rclone_cmd() + [
            "ls",
            f":s3:{remote_path}"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            files = [line.split()[-1] for line in result.stdout.strip().split("\n") if line]
            return True, files
        except subprocess.CalledProcessError as e:
            return False, []
    
    def check_bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists in Wasabi.
        
        Args:
            bucket_name: Name of the bucket
        
        Returns:
            True if bucket exists, False otherwise
        """
        cmd = self._get_rclone_cmd() + [
            "lsd",
            f":s3:"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return bucket_name in result.stdout
        except subprocess.CalledProcessError:
            return False
    
    def create_bucket(self, bucket_name: str) -> Tuple[bool, str]:
        """Create a new bucket in Wasabi.
        
        Args:
            bucket_name: Name of the bucket
        
        Returns:
            Tuple of (success, message)
        """
        cmd = self._get_rclone_cmd() + [
            "mkdir",
            f":s3:{bucket_name}"
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True, f"Bucket {bucket_name} created successfully"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to create bucket: {e.stderr}"
