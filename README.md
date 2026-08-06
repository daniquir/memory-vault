# The Memory Vault (El Baúl de los Recuerdos) 📦

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Linux](https://img.shields.io/badge/os-linux-orange.svg)](https://www.linux.org/)

A lightweight, multi-device backup and sync tool for Linux (systemd-free friendly).
It combines the convenience of cloud sync (Rclone) with the bulletproof security of snapshots (Restic) using Wasabi S3.

## Features

- 🚀 **Hybrid Sync:** Access your files like a local drive while keeping historical snapshots.
- 🛡️ **RM-Shield:** Protect yourself from accidental `rm -r` with shell aliases and trash integration.
- 💻 **Multi-device:** Hostname-aware snapshots to manage different PCs in the same bucket.
- 🌍 **Bilingual:** Full CLI and UI support for English and Spanish.
- 🔧 **Systemd-free:** Runs on any Init system (OpenRC, runit, SysVinit).
- 🔒 **WORM Immutability:** Optional Object Lock for bulletproof data protection.
- 🖥️ **GUI & CLI:** Both graphical and command-line interfaces available.

## Architecture

The Memory Vault uses a **two-bucket "Lean" architecture** for optimal cost efficiency and data protection:

### Bucket A: Sync Bucket (Daily Use)
- **Purpose:** Real-time file synchronization via Rclone
- **Mount:** Mounted as a local drive at `~/Vault`
- **Protection:** Bucket Versioning enabled
- **Use case:** Recover accidentally deleted files
- **Object Lock:** Not needed (would interfere with daily use)

### Bucket B: Vault Bucket (Snapshots)
- **Purpose:** Encrypted, deduplicated snapshots via Restic
- **Access:** Via CLI commands (`vault snap`, `vault list`, `vault restore`)
- **Protection:** Restic's internal retention policy (`--keep-last N --prune`)
- **Use case:** Bulletproof protection against ransomware and accidental deletion
- **Object Lock:** Disabled (simpler, more predictable)
- **Versioning:** Disabled (Restic manages its own versioning)

### Why Two Buckets?

Using separate buckets prevents:
- **Space duplication:** Restic's internal versioning would create unnecessary duplicates if bucket versioning was enabled
- **Cost inefficiency:** Paying for both bucket versioning and Restic's deduplication
- **Management complexity:** Easy to distinguish between daily sync files and historical snapshots

### Lean Architecture Benefits

The "Lean" approach simplifies the system:
- **No Object Lock:** Removes complexity and potential issues with WORM mode
- **Restic Retention:** Uses `restic forget --keep-last N --prune` for automatic cleanup
- **Configurable Retention:** Set how many snapshots to keep (default: 3)
- **Efficient Storage:** Restic's deduplication means unchanged files don't take extra space
- **Predictable Costs:** Only pay for what you actually use

### Key Components

- **Core Logic** (`src/core/`): Wrappers for Rclone, Restic, mount management, WORM, and Versioning
- **CLI** (`src/cli/`): Command-line interface with argparse
- **GUI** (`src/gui/`): CustomTkinter-based graphical interface with system tray
- **Utils** (`src/utils/`): Configuration management, i18n, and RM-Shield

## Installation

### Prerequisites

- Python 3.7+
- Linux (Debian/Ubuntu, Fedora/RHEL, or Arch-based)
- Wasabi S3 account

### Automated Installation

```bash
# Clone the repository
git clone https://github.com/Daniquir/memory-vault.git
cd memory-vault

# Run the installation script
./scripts/install.sh
```

The installation script will:
- Detect apt, dnf, or pacman and install system dependencies
- Check and install Python 3, pip, setuptools, and tkinter (required for the GUI)
- Install Python dependencies (customtkinter, pystray, Pillow, boto3)
- Install rclone and restic (from distro packages when available)
- Install fuse3 and trash-cli
- Create configuration directory at `~/.config/memory-vault/`
- Install the `vault` command (typically to `~/.local/bin/vault`)
- Verify that `vault` imports and runs
- Optionally add GUI to autostart

### Manual Installation

```bash
# Install Python dependencies
python3 -m pip install --user --break-system-packages -r requirements.txt
python3 -m pip install --user --break-system-packages -e .

# Install system dependencies (Debian/Ubuntu)
sudo apt-get install rclone restic fuse3 trash-cli python3-tk

# Install system dependencies (Fedora/RHEL)
sudo dnf install rclone restic fuse3 trash-cli python3-tkinter
```

## Quick Start

### 1. Initial Setup

**Important:** Before running setup, you must create your S3 buckets in Wasabi:
- Create a **Sync Bucket** for daily use (optional, if you want Sync functionality)
- Create a **Vault Bucket** for snapshots (optional, if you want Snapshots functionality)

The application will not create or modify buckets. It will only use the buckets you provide.

Run the setup wizard to configure your Wasabi S3 buckets:

```bash
vault setup
```

You'll be asked which functionalities to configure:
- **Sync only** (Rclone for daily use)
- **Snapshots only** (Restic for backups)
- **Both Sync and Snapshots**

The setup will then prompt for the relevant configuration based on your selection:

**For Sync:**
- Sync Bucket Name (must be pre-created in Wasabi)
- Access Key ID and Secret Access Key
- Sync Bucket Region (default: us-east-1)

**For Snapshots:**
- Vault Bucket Name (must be pre-created in Wasabi)
- Access Key ID and Secret Access Key
- Vault Bucket Region (default: us-east-1)
- Encryption password for snapshots
- Snapshot Retention Policy (number of snapshots to keep, default: 3)
- Auto Snap Interval (daily, weekly, or none, default: daily)

**Note:** You can configure only one functionality if you don't need both. The application will work with just Sync or just Snapshots configured.

### Edit Configuration

To modify an existing configuration:

**CLI:**
```bash
vault edit
```

This will show your current configuration and allow you to modify any field. Press Enter to keep the current value.

**GUI:**
Click the "✏️ Edit Configuration" button in the main window. The setup wizard will open with all fields pre-filled with your current configuration.

### 2. Mount the Vault

```bash
vault open
```

This mounts your **Sync Bucket** at `~/Vault` for daily use.

### 3. Create a Snapshot

```bash
vault snap /path/to/folder
```

Snapshots are stored in the **Vault Bucket** with AES-256 encryption. After each snapshot, the system automatically runs `restic forget --keep-last N --prune` to remove old snapshots and free up space. By default, it keeps the last 3 snapshots per device.

### 4. Unmount the Vault

```bash
vault close
```

## CLI Commands

### `vault setup`
Run the interactive setup wizard to configure Wasabi credentials and encryption.

### `vault open [--mount-point PATH]`
Mount the vault to a local directory (default: `~/Vault`).

### `vault close [--mount-point PATH]`
Unmount the vault and clean up cache.

### `vault snap --all | --path PATH`
Create a snapshot. Use `--all` for all configured folders or `--path` for a specific directory.

### `vault list [--host NAME]`
List snapshots. Use `--host` to filter by device hostname.

### `vault restore SNAPSHOT_ID TARGET`
Restore a snapshot to a target directory.

### `vault config`
Interactive configuration of sync folders for the current device.

### `vault shield --on | --off`
Enable or disable RM-Shield protection (replaces `rm` with `trash-put`).

### `vault status [--mount-point PATH]`
Show vault status (mount status, last snapshot, used space).

## GUI Usage

Launch the graphical interface:

```bash
vault --gui
```

Or use the system tray icon (green=ok, blue=syncing, red=error).

### GUI Features

- **Dashboard**: Visual status of connection and mount
- **Security Center**: Toggle RM-Shield protection
- **Sync Filter**: Manage which folders to sync
- **Panic Button**: Emergency close all operations

## Configuration

Configuration is stored in `~/.config/memory-vault/config.json`:

```json
{
  "storage": {
    "provider": "wasabi",
    "bucket": "your-bucket-name",
    "access_key": "YOUR_ACCESS_KEY",
    "secret_key": "YOUR_SECRET_KEY",
    "region": "us-east-1",
    "object_lock": true,
    "lock_days": 90,
    "versioning": "enabled"
  },
  "devices": {
    "hostname": {
      "sync_folders": ["/home/user/documents", "/home/user/photos"],
      "last_snap": "2026-04-25T10:00:00"
    }
  },
  "security": {
    "rm_shield": false,
    "encryption_password": "your_encryption_password"
  },
  "ui": {
    "language": "auto",
    "start_minimized": true
  }
}
```

## Security Features

### RM-Shield

When enabled, RM-Shield:
- Replaces `rm` with `trash-put` in your shell
- Shows warnings when deleting files inside the vault mount point
- Provides `rrm` command for forced deletion

Enable it:
```bash
vault shield --on
```

### WORM Immutability

Object Lock (WORM mode) ensures:
- Files cannot be deleted for the retention period (default: 90 days)
- Protection against ransomware and accidental deletion
- Configured via Wasabi API during setup

Note: Wasabi charges for minimum 90-day retention regardless of Object Lock, so enabling it provides protection without additional cost.

### Encryption

All snapshots are encrypted with AES-256 using Restic. The encryption password is set during setup and stored locally in the configuration file.

## Multi-Device Support

Each device is identified by its hostname. Snapshots are tagged with the hostname, allowing you to:
- View snapshots from all registered devices: `vault list`
- Restore snapshots from any device: `vault restore <id> <target>`
- Configure different sync folders per device

## Troubleshooting

### Mount Fails

Check if FUSE is installed:
```bash
fusermount3 --version
```

Check if rclone is configured:
```bash
rclone version
```

### Snapshot Fails

Verify Wasabi credentials are correct in `~/.config/memory-vault/config.json`.

Check network connectivity to Wasabi S3.

### GUI Won't Start

Ensure customtkinter is installed:
```bash
python3 -m pip list | grep customtkinter
```

On Fedora/RHEL, tkinter is a separate package:
```bash
sudo dnf install python3-tkinter
```

On Debian/Ubuntu:
```bash
sudo apt install python3-tk
```

Check for X11/Wayland display issues.

## Uninstallation

To remove The Memory Vault:

```bash
cd memory-vault/scripts
./uninstall.sh
```

The uninstall script will:
- Remove the `vault` binary from `/usr/local/bin/`
- Remove application menu entries
- Remove autostart entry
- Optionally remove configuration directory (with confirmation)
- Optionally remove Python dependencies (with confirmation)

**Note:** System packages (rclone, restic, fuse3, trash-cli, python3, pip) are NOT removed as they may be used by other applications.

## System Compatibility

Tested on:
- Debian 11/12
- Ubuntu 20.04/22.04/24.04
- Fedora 40+
- Devuan
- MX Linux
- AntiX
- Void Linux

Should work on any Linux distribution with:
- Python 3.7+
- FUSE support
- Package manager (apt, dnf, or pacman)
- Tkinter for the GUI (`python3-tk` / `python3-tkinter`)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file for details on our code of conduct and the process for submitting pull requests.

## Support

For issues and questions:
- GitHub Issues: https://github.com/Daniquir/memory-vault/issues
- Documentation: See `docs/` directory