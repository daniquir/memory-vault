#!/bin/bash
# Installation script for The Memory Vault
# Supports Debian/Ubuntu and Fedora/RHEL family (also Arch via pacman)

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

detect_pkg_manager() {
    if [ -x "$(command -v apt-get)" ]; then
        echo "apt"
    elif [ -x "$(command -v dnf)" ]; then
        echo "dnf"
    elif [ -x "$(command -v pacman)" ]; then
        echo "pacman"
    else
        echo ""
    fi
}

PKG_MANAGER="$(detect_pkg_manager)"

install_system_package() {
    local packages=("$@")
    print_info "Installing ${packages[*]}..."
    case "$PKG_MANAGER" in
        apt)
            sudo apt-get update -qq
            sudo apt-get install -y "${packages[@]}"
            ;;
        dnf)
            sudo dnf install -y "${packages[@]}"
            ;;
        pacman)
            sudo pacman -S --noconfirm "${packages[@]}"
            ;;
        *)
            print_error "No supported package manager found. Please install manually: ${packages[*]}"
            exit 1
            ;;
    esac
}

# Try distro package first; return 0 if the command becomes available.
try_install_from_distro() {
    local cmd="$1"
    shift
    local packages=("$@")

    if [ -z "$PKG_MANAGER" ]; then
        return 1
    fi

    if install_system_package "${packages[@]}" 2>/dev/null; then
        if check_command "$cmd"; then
            return 0
        fi
    fi
    return 1
}

download_file() {
    local url="$1"
    local dest="$2"
    if check_command curl; then
        curl -fsSL -o "$dest" "$url"
    elif check_command wget; then
        wget -q -O "$dest" "$url"
    else
        print_error "Neither curl nor wget is available. Please install one of them."
        exit 1
    fi
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root. Use sudo only when needed."
    exit 1
fi

print_info "The Memory Vault Installation Script"
if [ -n "$PKG_MANAGER" ]; then
    print_info "Detected package manager: $PKG_MANAGER"
fi
echo ""

# Check Python 3
print_info "Checking Python 3..."
if check_command python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_info "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Installing..."
    case "$PKG_MANAGER" in
        apt) install_system_package python3 python3-pip python3-venv python3-setuptools python3-tk ;;
        dnf) install_system_package python3 python3-pip python3-setuptools python3-tkinter ;;
        pacman) install_system_package python python-pip python-setuptools tk ;;
        *) print_error "Install Python 3 manually."; exit 1 ;;
    esac
fi

# Tkinter is required by CustomTkinter (GUI). On Fedora it is a separate RPM.
print_info "Checking tkinter..."
if python3 -c "import tkinter" &> /dev/null; then
    print_info "tkinter found"
else
    print_warn "tkinter not found. Installing..."
    case "$PKG_MANAGER" in
        apt) install_system_package python3-tk ;;
        dnf) install_system_package python3-tkinter ;;
        pacman) install_system_package tk ;;
        *)
            print_error "tkinter is required for the GUI. Install python3-tkinter (Fedora) or python3-tk (Debian)."
            exit 1
            ;;
    esac
fi

# Check pip
print_info "Checking pip..."
if python3 -m pip --version &> /dev/null; then
    print_info "pip found"
else
    print_warn "pip not found. Installing..."
    case "$PKG_MANAGER" in
        apt) install_system_package python3-pip python3-setuptools ;;
        dnf) install_system_package python3-pip python3-setuptools ;;
        pacman) install_system_package python-pip python-setuptools ;;
        *)
            print_warn "Falling back to get-pip.py..."
            TMP_GET_PIP="$(mktemp)"
            download_file "https://bootstrap.pypa.io/get-pip.py" "$TMP_GET_PIP"
            python3 "$TMP_GET_PIP" --user
            rm -f "$TMP_GET_PIP"
            ;;
    esac
fi

# Ensure setuptools is available for editable installs
if ! python3 -c "import setuptools" &> /dev/null; then
    print_warn "setuptools not found. Installing..."
    case "$PKG_MANAGER" in
        apt) install_system_package python3-setuptools ;;
        dnf) install_system_package python3-setuptools ;;
        pacman) install_system_package python-setuptools ;;
        *) python3 -m pip install --user --break-system-packages setuptools ;;
    esac
fi

# Install Python dependencies
print_info "Installing Python dependencies..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
REQUIREMENTS_FILE="$REPO_DIR/requirements.txt"

if [ -f "$REQUIREMENTS_FILE" ]; then
    python3 -m pip install --user --break-system-packages -r "$REQUIREMENTS_FILE"
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
    if ! try_install_from_distro rclone rclone; then
        print_info "Installing rclone via official install script..."
        curl https://rclone.org/install.sh | sudo bash
    fi
fi

# Check and install restic
print_info "Checking restic..."
if check_command restic; then
    RESTIC_VERSION=$(restic version)
    print_info "restic found: $RESTIC_VERSION"
else
    print_warn "restic not found. Installing..."
    if ! try_install_from_distro restic restic; then
        ARCH="$(uname -m)"
        case "$ARCH" in
            x86_64|amd64) RESTIC_ARCH="amd64" ;;
            aarch64|arm64) RESTIC_ARCH="arm64" ;;
            *)
                print_error "Automatic restic installation not supported for architecture: $ARCH"
                exit 1
                ;;
        esac
        RESTIC_VERSION="0.16.4"
        RESTIC_TMP="$(mktemp -d)"
        RESTIC_ARCHIVE="restic_${RESTIC_VERSION}_linux_${RESTIC_ARCH}.bz2"
        print_info "Downloading restic ${RESTIC_VERSION}..."
        download_file \
            "https://github.com/restic/restic/releases/download/v${RESTIC_VERSION}/${RESTIC_ARCHIVE}" \
            "${RESTIC_TMP}/${RESTIC_ARCHIVE}"
        bunzip2 -f "${RESTIC_TMP}/${RESTIC_ARCHIVE}"
        sudo mv "${RESTIC_TMP}/restic_${RESTIC_VERSION}_linux_${RESTIC_ARCH}" /usr/local/bin/restic
        sudo chmod +x /usr/local/bin/restic
        rm -rf "$RESTIC_TMP"
        print_info "restic installed to /usr/local/bin/restic"
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
python3 -m pip install --user --break-system-packages -e .
print_info "The Memory Vault installed as Python package"

# Verify the entry point can import the package
print_info "Verifying installation..."
if ! python3 -c "from vault import main_entry; from src.cli import commands" &> /dev/null; then
    print_error "Installation verification failed: cannot import vault modules."
    print_error "Try: python3 -m pip install --user --break-system-packages --force-reinstall -e \"$REPO_DIR\""
    exit 1
fi
if ! check_command vault; then
    print_warn "vault command not on PATH yet (expected under ~/.local/bin)."
elif ! vault --help &> /dev/null; then
    print_error "vault command is on PATH but failed to run."
    exit 1
fi
print_info "Import and CLI check passed"

# Create desktop file for application menu
print_info "Creating application menu entry..."
APPLICATIONS_DIR="/usr/share/applications"
DESKTOP_CONTENT='[Desktop Entry]
Type=Application
Name=The Memory Vault
Comment=Multi-device backup and sync tool
Exec=vault --gui
Icon=folder-locked
Terminal=false
Categories=Utility;Archiving;System;'

if [ -w "$APPLICATIONS_DIR" ]; then
    echo "$DESKTOP_CONTENT" | sudo tee "$APPLICATIONS_DIR/memory-vault.desktop" > /dev/null
    print_info "Application menu entry created"
else
    print_warn "Cannot create system-wide application entry. Creating user entry..."
    USER_APPLICATIONS_DIR="$HOME/.local/share/applications"
    mkdir -p "$USER_APPLICATIONS_DIR"
    echo "$DESKTOP_CONTENT" > "$USER_APPLICATIONS_DIR/memory-vault.desktop"
    print_info "User application menu entry created"
fi

# Create desktop file for autostart (optional)
read -p "Do you want to add The Memory Vault GUI to autostart? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Creating autostart entry..."
    AUTOSTART_DIR="$HOME/.config/autostart"
    mkdir -p "$AUTOSTART_DIR"

    # Prefer resolved path so autostart works before PATH is fully set
    VAULT_PATH=$(command -v vault || echo "$HOME/.local/bin/vault")

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
ensure_local_bin_path() {
    local rc_file="$1"
    if [ ! -f "$rc_file" ]; then
        return
    fi
    if grep -q '\$HOME/\.local/bin' "$rc_file" 2>/dev/null || grep -q '~/.local/bin' "$rc_file" 2>/dev/null; then
        return
    fi
    print_warn "Adding ~/.local/bin to PATH in $(basename "$rc_file")"
    {
        echo ''
        echo '# Added by The Memory Vault installer'
        echo 'export PATH="$HOME/.local/bin:$PATH"'
    } >> "$rc_file"
}

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    ensure_local_bin_path "$HOME/.bashrc"
    # Fedora Workstation often uses .bashrc; also cover zsh users
    ensure_local_bin_path "$HOME/.zshrc"
    print_info "Please run: source ~/.bashrc  (or open a new terminal)"
fi

print_info "Installation completed successfully!"
echo ""
print_info "Next steps:"
echo "  1. Run 'vault setup' to configure your Wasabi credentials"
echo "  2. Run 'vault --help' to see all available commands"
echo "  3. Run 'vault --gui' to launch the graphical interface"
echo ""
print_info "For more information, see the documentation in docs/"
