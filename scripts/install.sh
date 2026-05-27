#!/bin/bash
# Installation script for The Memory Vault
# Supports Debian-based systems (Debian, Ubuntu, Devuan, MX Linux, AntiX)

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

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

install_system_package() {
    print_info "Installing $1..."
    if [ -x "$(command -v apt-get)" ]; then
        sudo apt-get update -qq
        sudo apt-get install -y "$1"
    elif [ -x "$(command -v dnf)" ]; then
        sudo dnf install -y "$1"
    elif [ -x "$(command -v pacman)" ]; then
        sudo pacman -S --noconfirm "$1"
    else
        print_error "No package manager found. Please install $1 manually."
        exit 1
    fi
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root. Use sudo only when needed."
    exit 1
fi

print_info "The Memory Vault Installation Script"
echo ""

# Check Python 3
print_info "Checking Python 3..."
if check_command python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_info "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Installing..."
    install_system_package python3
fi

# Check pip
print_info "Checking pip..."
if check_command pip3; then
    print_info "pip3 found"
else
    print_warn "pip3 not found. Installing..."
    sudo apt-get install -y python3-pip || curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && sudo python3 get-pip.py
fi

# Install Python dependencies
print_info "Installing Python dependencies..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
REQUIREMENTS_FILE="$REPO_DIR/requirements.txt"

if [ -f "$REQUIREMENTS_FILE" ]; then
    pip3 install --user --break-system-packages -r "$REQUIREMENTS_FILE"
    print_info "Python dependencies installed"
else
    print_error "requirements.txt not found at $REQUIREMENTS_FILE"
    exit 1
fi

# Check and install rclone
print_info "Checking rclone..."
if check_command rclone; then
    RCLONE_VERSION=$(rclone version | head -n1)
    print_info "rclone found: $RCLONE_VERSION"
else
    print_warn "rclone not found. Installing..."
    curl https://rclone.org/install.sh | sudo bash
fi

# Check and install restic
print_info "Checking restic..."
if check_command restic; then
    RESTIC_VERSION=$(restic version)
    print_info "restic found: $RESTIC_VERSION"
else
    print_warn "restic not found. Installing..."
    if [ "$(uname -m)" = "x86_64" ]; then
        RESTIC_VERSION="0.16.4"
        wget https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/restic_${RESTIC_VERSION}_linux_amd64.bz2
        bunzip2 restic_${RESTIC_VERSION}_linux_amd64.bz2
        sudo mv restic_${RESTIC_VERSION}_linux_amd64 /usr/local/bin/restic
        sudo chmod +x /usr/local/bin/restic
        rm -f restic_${RESTIC_VERSION}_linux_amd64.bz2
    else
        print_error "Automatic restic installation not supported for this architecture. Please install manually."
        exit 1
    fi
fi

# Check and install fuse3
print_info "Checking fuse3..."
if check_command fusermount3; then
    print_info "fuse3 found"
else
    print_warn "fuse3 not found. Installing..."
    install_system_package fuse3
fi

# Check and install trash-cli
print_info "Checking trash-cli..."
if check_command trash-put; then
    print_info "trash-cli found"
else
    print_warn "trash-cli not found. Installing..."
    install_system_package trash-cli
fi

# Create configuration directory
print_info "Creating configuration directory..."
CONFIG_DIR="$HOME/.config/memory-vault"
mkdir -p "$CONFIG_DIR"
print_info "Configuration directory created: $CONFIG_DIR"

# Install vault as Python package
print_info "Installing The Memory Vault as Python package..."
cd "$REPO_DIR"
pip3 install --user --break-system-packages -e .
print_info "The Memory Vault installed as Python package"

# Create desktop file for application menu
print_info "Creating application menu entry..."
APPLICATIONS_DIR="/usr/share/applications"
if [ -w "$APPLICATIONS_DIR" ]; then
    sudo tee "$APPLICATIONS_DIR/memory-vault.desktop" > /dev/null << EOF
[Desktop Entry]
Type=Application
Name=The Memory Vault
Comment=Multi-device backup and sync tool
Exec=vault --gui
Icon=folder-locked
Terminal=false
Categories=Utility;Archiving;System;
EOF
    print_info "Application menu entry created"
else
    print_warn "Cannot create system-wide application entry. Creating user entry..."
    USER_APPLICATIONS_DIR="$HOME/.local/share/applications"
    mkdir -p "$USER_APPLICATIONS_DIR"
    cat > "$USER_APPLICATIONS_DIR/memory-vault.desktop" << EOF
[Desktop Entry]
Type=Application
Name=The Memory Vault
Comment=Multi-device backup and sync tool
Exec=vault --gui
Icon=folder-locked
Terminal=false
Categories=Utility;Archiving;System;
EOF
    print_info "User application menu entry created"
fi

# Create desktop file for autostart (optional)
read -p "Do you want to add The Memory Vault GUI to autostart? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Creating autostart entry..."
    AUTOSTART_DIR="$HOME/.config/autostart"
    mkdir -p "$AUTOSTART_DIR"
    
    # Get the actual path to vault executable
    VAULT_PATH=$(which vault || echo "$HOME/.local/bin/vault")
    
    cat > "$AUTOSTART_DIR/memory-vault.desktop" << EOF
[Desktop Entry]
Type=Application
Name=The Memory Vault
Comment=Multi-device backup and sync tool
Exec=$VAULT_PATH --gui
Icon=folder-locked
Terminal=false
Categories=Utility;Archiving;
X-GNOME-Autostart-Delay=3
EOF
    
    print_info "Autostart entry created"
fi

# Add Python user bin to PATH if not already there
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    print_warn "Adding ~/.local/bin to PATH in .bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    print_info "Please run: source ~/.bashrc"
fi

print_info "Installation completed successfully!"
echo ""
print_info "Next steps:"
echo "  1. Run 'vault setup' to configure your Wasabi credentials"
echo "  2. Run 'vault --help' to see all available commands"
echo "  3. Run 'vault --gui' to launch the graphical interface"
echo ""
print_info "For more information, see the documentation in docs/"
