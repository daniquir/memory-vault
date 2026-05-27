#!/bin/bash
# Uninstallation script for The Memory Vault
# Removes only Memory Vault-specific files, not system packages

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root. Use sudo only when needed."
    exit 1
fi

print_info "The Memory Vault Uninstallation Script"
echo ""

# Remove vault binary
print_info "Removing vault binary..."
if [ -f "/usr/local/bin/vault" ]; then
    sudo rm -f /usr/local/bin/vault
    print_info "vault binary removed from /usr/local/bin/vault"
else
    print_warn "vault binary not found at /usr/local/bin/vault"
fi

# Remove application menu entry
print_info "Removing application menu entry..."
if [ -f "/usr/share/applications/memory-vault.desktop" ]; then
    sudo rm -f /usr/share/applications/memory-vault.desktop
    print_info "Application menu entry removed"
fi

if [ -f "$HOME/.local/share/applications/memory-vault.desktop" ]; then
    rm -f "$HOME/.local/share/applications/memory-vault.desktop"
    print_info "User application menu entry removed"
fi

# Remove autostart entry
print_info "Removing autostart entry..."
if [ -f "$HOME/.config/autostart/memory-vault.desktop" ]; then
    rm -f "$HOME/.config/autostart/memory-vault.desktop"
    print_info "Autostart entry removed"
else
    print_warn "Autostart entry not found"
fi

# Remove configuration directory
print_warn "Configuration directory: $HOME/.config/memory-vault"
read -p "Do you want to remove the configuration directory? This will delete your settings and credentials. (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "$HOME/.config/memory-vault" ]; then
        rm -rf "$HOME/.config/memory-vault"
        print_info "Configuration directory removed"
    else
        print_warn "Configuration directory not found"
    fi
else
    print_info "Configuration directory preserved"
fi

# Remove Python dependencies (optional)
print_warn "Python dependencies were installed with --user flag"
read -p "Do you want to remove Python dependencies (customtkinter, pystray, Pillow, boto3)? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Removing Python dependencies..."
    pip3 uninstall --yes customtkinter pystray Pillow boto3 2>/dev/null || print_warn "Some Python dependencies could not be removed"
    print_info "Python dependencies removed"
else
    print_info "Python dependencies preserved"
fi

# Note about system packages
echo ""
print_info "System packages (rclone, restic, fuse3, trash-cli, python3, pip) were NOT removed"
print_info "These packages may be used by other applications and were preserved."
echo ""

print_info "Uninstallation completed successfully!"
echo ""
print_info "To completely remove all traces, you may also want to:"
echo "  - Manually remove the vault repository directory"
echo "  - Remove any Python virtual environments created"
echo "  - Review and clean ~/.local/bin if needed"
