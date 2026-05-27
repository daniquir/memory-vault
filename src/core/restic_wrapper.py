"""Restic wrapper for snapshot operations."""

import subprocess
import os
import threading
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from .binary_detector import BinaryDetector


class ResticWrapper:
    """Wrapper for restic commands."""
    
    def __init__(self, config: dict, output_callback=None):
        """Initialize restic wrapper with configuration.
        
        Args:
            config: Configuration dictionary with Wasabi credentials and encryption password
            output_callback: Optional callback function for real-time output (receives line)
        """
        self.config = config
        self.output_callback = output_callback
        self._ensure_binary()
    
    def _ensure_binary(self) -> None:
        """Ensure restic binary is available."""
        if not BinaryDetector.check_binary("restic"):
            success, msg = BinaryDetector.install_binary("restic")
            if not success:
                raise RuntimeError(f"Failed to install restic: {msg}")
    
    def _get_env(self) -> Dict[str, str]:
        """Get environment variables for restic."""
        storage = self.config.get("storage", {})
        security = self.config.get("security", {})

        env = os.environ.copy()
        vault_region = storage.get('vault_region', 'us-east-1')
        env["RESTIC_REPOSITORY"] = f"s3:s3.{vault_region}.wasabisys.com/{storage.get('vault_bucket', '')}"
        env["AWS_ACCESS_KEY_ID"] = storage.get("access_key", "")
        env["AWS_SECRET_ACCESS_KEY"] = storage.get("secret_key", "")
        env["RESTIC_PASSWORD"] = security.get("encryption_password", "")

        return env
    
    def _run_command(self, cmd: List[str]) -> Tuple[bool, str, str]:
        """Run a command with real-time output streaming.
        
        Args:
            cmd: Command to execute
        
        Returns:
            Tuple of (success, stdout, stderr)
        """
        stdout_lines = []
        stderr_lines = []
        
        process = subprocess.Popen(
            cmd,
            env=self._get_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Stream stdout in real-time
        for line in process.stdout:
            stdout_lines.append(line)
            if self.output_callback:
                self.output_callback(line.rstrip())
        
        # Stream stderr in real-time
        for line in process.stderr:
            stderr_lines.append(line)
            if self.output_callback:
                self.output_callback(f"ERROR: {line.rstrip()}")
        
        process.wait()
        
        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)
        
        return True, stdout, stderr
    
    def init_repo(self) -> Tuple[bool, str]:
        """Initialize a new restic repository.
        
        Returns:
            Tuple of (success, message)
        """
        cmd = ["restic", "init"]
        
        try:
            success, stdout, stderr = self._run_command(cmd)
            return True, stdout
        except subprocess.CalledProcessError as e:
            # Repository might already exist
            if "already initialized" in str(e.stderr).lower():
                return True, "Repository already initialized"
            return False, f"Failed to initialize repository: {e.stderr}"
    
    def backup(self, path: str, hostname: str, tags: Optional[List[str]] = None, prune: bool = True) -> Tuple[bool, str]:
        """Create a snapshot of a path and optionally prune old snapshots.

        Args:
            path: Path to backup
            hostname: Hostname tag for the snapshot
            tags: Additional tags for the snapshot
            prune: Whether to run forget --prune after backup

        Returns:
            Tuple of (success, message)
        """
        cmd = ["restic", "backup", path, "--host", hostname]

        if tags:
            for tag in tags:
                cmd.extend(["--tag", tag])

        try:
            success, stdout, stderr = self._run_command(cmd)

            # Prune old snapshots if enabled
            if prune:
                keep_last = self.config.get("snapshots", {}).get("keep_last", 3)
                prune_result = self.prune(keep_last)
                if not prune_result[0]:
                    return True, f"{stdout}\nWarning: {prune_result[1]}"

            return True, stdout
        except subprocess.CalledProcessError as e:
            return False, f"Backup failed: {e.stderr}"

    def prune(self, keep_last: int = 3) -> Tuple[bool, str]:
        """Prune old snapshots using restic forget.

        Args:
            keep_last: Number of snapshots to keep

        Returns:
            Tuple of (success, message)
        """
        cmd = ["restic", "forget", "--keep-last", str(keep_last), "--prune"]

        try:
            success, stdout, stderr = self._run_command(cmd)
            return True, f"Pruned to keep last {keep_last} snapshots"
        except subprocess.CalledProcessError as e:
            return False, f"Prune failed: {e.stderr}"
    
    def list_snapshots(self, hostname: Optional[str] = None) -> Tuple[bool, List[Dict]]:
        """List snapshots.
        
        Args:
            hostname: Filter by hostname (optional)
        
        Returns:
            Tuple of (success, snapshot_list)
        """
        cmd = ["restic", "snapshots", "--json"]
        
        if hostname:
            cmd.extend(["--host", hostname])
        
        try:
            success, stdout, stderr = self._run_command(cmd)
            import json
            snapshots = json.loads(stdout)
            return True, snapshots
        except subprocess.CalledProcessError as e:
            return False, []
    
    def restore(self, snapshot_id: str, target_path: str) -> Tuple[bool, str]:
        """Restore a snapshot to a target path.
        
        Args:
            snapshot_id: Snapshot ID to restore
            target_path: Target directory path
        
        Returns:
            Tuple of (success, message)
        """
        cmd = ["restic", "restore", snapshot_id, "--target", target_path]
        
        try:
            success, stdout, stderr = self._run_command(cmd)
            return True, stdout
        except subprocess.CalledProcessError as e:
            return False, f"Restore failed: {e.stderr}"
    
    def forget(self, snapshot_id: str) -> Tuple[bool, str]:
        """Forget (remove) a snapshot.
        
        Args:
            snapshot_id: Snapshot ID to forget
        
        Returns:
            Tuple of (success, message)
        """
        # Check if WORM is enabled
        storage = self.config.get("storage", {})
        if storage.get("object_lock", False):
            return False, "Cannot delete snapshot: Object Lock is enabled"
        
        cmd = ["restic", "forget", snapshot_id]
        
        try:
            success, stdout, stderr = self._run_command(cmd)
            return True, stdout
        except subprocess.CalledProcessError as e:
            return False, f"Forget failed: {e.stderr}"
    
    def check(self) -> Tuple[bool, str]:
        """Check repository integrity.
        
        Returns:
            Tuple of (success, message)
        """
        cmd = ["restic", "check"]
        
        try:
            success, stdout, stderr = self._run_command(cmd)
            return True, stdout
        except subprocess.CalledProcessError as e:
            return False, f"Check failed: {e.stderr}"
    
    def stats(self) -> Tuple[bool, Dict]:
        """Get repository statistics.
        
        Returns:
            Tuple of (success, stats_dict)
        """
        cmd = ["restic", "stats", "--json"]
        
        try:
            success, stdout, stderr = self._run_command(cmd)
            import json
            stats = json.loads(stdout)
            return True, stats
        except subprocess.CalledProcessError as e:
            return False, {}
