"""RM-Shield: Protection against accidental file deletion."""

import os
from pathlib import Path
from typing import Tuple


class Shield:
    """Manages RM-Shield protection using trash-cli."""
    
    BASHRC_PATH = Path.home() / ".bashrc"
    ZSHRC_PATH = Path.home() / ".zshrc"
    
    SHIELD_CONFIG = """
# The Memory Vault - RM-Shield Protection
# This section prevents accidental deletion with trash-cli
if command -v trash-put &> /dev/null; then
    alias rm='trash-put'
    alias rrm='/bin/rm'
fi
"""
    
    VAULT_WARNING = """
# The Memory Vault - Vault Mount Warning
vault_rm_warning() {
    if [[ "$PWD" == "$HOME/Vault"* ]]; then
        echo "⚠️  WARNING: You are inside the Vault mount point!"
        echo "   Files here are synced to Wasabi S3."
        echo "   Use 'rrm' to force delete, or 'trash-put' to move to trash."
    fi
}
# Only add vault_rm_warning to PROMPT_COMMAND if not already present
if [[ "$PROMPT_COMMAND" != *"vault_rm_warning"* ]]; then
    if [[ -z "$PROMPT_COMMAND" ]]; then
        PROMPT_COMMAND="vault_rm_warning"
    else
        PROMPT_COMMAND="$PROMPT_COMMAND;vault_rm_warning"
    fi
fi
"""
    
    def __init__(self):
        """Initialize shield manager."""
        self._check_trash_cli()
    
    def _check_trash_cli(self) -> None:
        """Check if trash-cli is installed."""
        from .config import Config
        from ..core.binary_detector import BinaryDetector
        
        if not BinaryDetector.check_binary("trash-put"):
            success, msg = BinaryDetector.install_binary("trash-cli")
            if not success:
                print(f"Warning: Could not install trash-cli: {msg}")
    
    def enable(self) -> Tuple[bool, str]:
        """Enable RM-Shield in shell configuration.
        
        Returns:
            Tuple of (success, message)
        """
        modified = False
        already_enabled = False
        files_found = False
        
        # Modify .bashrc
        if self.BASHRC_PATH.exists():
            files_found = True
            content = self.BASHRC_PATH.read_text()
            if "The Memory Vault - RM-Shield" not in content:
                with open(self.BASHRC_PATH, "a") as f:
                    f.write(self.SHIELD_CONFIG)
                    f.write(self.VAULT_WARNING)
                modified = True
            else:
                already_enabled = True
        
        # Modify .zshrc
        if self.ZSHRC_PATH.exists():
            files_found = True
            content = self.ZSHRC_PATH.read_text()
            if "The Memory Vault - RM-Shield" not in content:
                with open(self.ZSHRC_PATH, "a") as f:
                    f.write(self.SHIELD_CONFIG)
                    f.write(self.VAULT_WARNING)
                modified = True
            else:
                already_enabled = True
        
        if modified:
            return True, "RM-Shield enabled in shell configuration"
        if already_enabled:
            return False, "RM-Shield is already enabled in shell configuration"
        return False, "No shell configuration files found (.bashrc or .zshrc)"
    
    def disable(self) -> Tuple[bool, str]:
        """Disable RM-Shield from shell configuration.
        
        Returns:
            Tuple of (success, message)
        """
        modified = False
        
        # Remove from .bashrc
        if self.BASHRC_PATH.exists():
            content = self.BASHRC_PATH.read_text()
            if "The Memory Vault - RM-Shield" in content:
                # Remove the shield section
                lines = content.split("\n")
                new_lines = []
                skip = False
                for line in lines:
                    if "The Memory Vault" in line:
                        skip = True
                    elif skip and line.strip() and not line.startswith("#"):
                        skip = False
                    if not skip:
                        new_lines.append(line)
                
                self.BASHRC_PATH.write_text("\n".join(new_lines))
                modified = True
        
        # Remove from .zshrc
        if self.ZSHRC_PATH.exists():
            content = self.ZSHRC_PATH.read_text()
            if "The Memory Vault - RM-Shield" in content:
                lines = content.split("\n")
                new_lines = []
                skip = False
                for line in lines:
                    if "The Memory Vault" in line:
                        skip = True
                    elif skip and line.strip() and not line.startswith("#"):
                        skip = False
                    if not skip:
                        new_lines.append(line)
                
                self.ZSHRC_PATH.write_text("\n".join(new_lines))
                modified = True
        
        if modified:
            return True, "RM-Shield disabled from shell configuration"
        return False, "RM-Shield was not enabled"
    
    def is_enabled(self) -> bool:
        """Check if RM-Shield is currently enabled.
        
        Returns:
            True if enabled, False otherwise
        """
        if self.BASHRC_PATH.exists():
            if "The Memory Vault - RM-Shield" in self.BASHRC_PATH.read_text():
                return True
        if self.ZSHRC_PATH.exists():
            if "The Memory Vault - RM-Shield" in self.ZSHRC_PATH.read_text():
                return True
        return False
