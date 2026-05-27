"""Binary detection and installation for Rclone and Restic."""

import os
import shutil
import subprocess
import sys
from typing import Optional, Tuple


class BinaryDetector:
    """Detects and manages installation of required binaries."""
    
    REQUIRED_BINARIES = {
        "rclone": {
            "check_cmd": ["rclone", "version"],
            "install_cmd": "curl https://rclone.org/install.sh | sudo bash",
            "pip_package": None
        },
        "restic": {
            "check_cmd": ["restic", "version"],
            "install_cmd": None,
            "pip_package": None
        },
        "fuse3": {
            "check_cmd": ["fusermount3", "--version"],
            "install_cmd": "sudo apt-get install -y fuse3",
            "pip_package": None
        },
        "trash-cli": {
            "check_cmd": ["trash-put", "--version"],
            "install_cmd": "sudo apt-get install -y trash-cli",
            "pip_package": None
        }
    }
    
    @classmethod
    def check_binary(cls, binary_name: str) -> bool:
        """Check if a binary is available in PATH."""
        return shutil.which(binary_name) is not None
    
    @classmethod
    def check_version(cls, binary_name: str) -> Tuple[bool, Optional[str]]:
        """Check binary version and return (is_available, version_string)."""
        if binary_name not in cls.REQUIRED_BINARIES:
            return False, None
        
        config = cls.REQUIRED_BINARIES[binary_name]
        check_cmd = config["check_cmd"]
        
        try:
            result = subprocess.run(
                check_cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, None
    
    @classmethod
    def get_missing_binaries(cls) -> list[str]:
        """Get list of missing required binaries."""
        missing = []
        for binary_name in cls.REQUIRED_BINARIES:
            if not cls.check_binary(binary_name):
                missing.append(binary_name)
        return missing
    
    @classmethod
    def install_binary(cls, binary_name: str) -> Tuple[bool, str]:
        """Attempt to install a binary. Returns (success, message)."""
        if binary_name not in cls.REQUIRED_BINARIES:
            return False, f"Unknown binary: {binary_name}"
        
        config = cls.REQUIRED_BINARIES[binary_name]
        
        # Check if already installed
        if cls.check_binary(binary_name):
            return True, f"{binary_name} is already installed"
        
        # Try pip package first if available
        if config["pip_package"]:
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", config["pip_package"]],
                    check=True,
                    capture_output=True
                )
                return True, f"Successfully installed {binary_name} via pip"
            except subprocess.CalledProcessError as e:
                return False, f"Failed to install {binary_name} via pip: {e.stderr.decode()}"
        
        # Try system install command
        if config["install_cmd"]:
            try:
                subprocess.run(config["install_cmd"], shell=True, check=True)
                return True, f"Successfully installed {binary_name}"
            except subprocess.CalledProcessError as e:
                return False, f"Failed to install {binary_name}: {e}"
        
        return False, f"No installation method available for {binary_name}"
    
    @classmethod
    def check_python_dependencies(cls) -> Tuple[bool, list[str]]:
        """Check if Python dependencies are installed."""
        missing = []
        required_packages = ["customtkinter", "pystray", "Pillow", "boto3"]
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing.append(package)
        
        return len(missing) == 0, missing
    
    @classmethod
    def install_python_dependencies(cls) -> Tuple[bool, str]:
        """Install Python dependencies from requirements.txt."""
        script_dir = Path(__file__).parent.parent.parent
        requirements_file = script_dir / "requirements.txt"
        
        if not requirements_file.exists():
            return False, "requirements.txt not found"
        
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                check=True,
                capture_output=True
            )
            return True, "Successfully installed Python dependencies"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to install Python dependencies: {e.stderr.decode()}"
