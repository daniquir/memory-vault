# Changelog

All notable changes to The Memory Vault will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-08-06

### Fixed
- Package install on Fedora and other systems with modern pip (PEP 660): include `vault` as a `py_module` so the `vault` console entry point resolves after editable install
- Lazy-load CLI/GUI imports so `vault` CLI works even when tkinter is missing
- Clearer GUI error when tkinter is not installed (Fedora: `python3-tkinter`, Debian: `python3-tk`)
- CI flake8 failures (`Path` import, lambda exception capture, unused `global`)
- `test_is_configured` aligned with sync/vault bucket configuration API
- Drop unsupported Python 3.7/3.8 from GitHub Actions matrix (ubuntu-latest)

### Changed
- Installation script now supports Fedora/RHEL (`dnf`) and Arch (`pacman`) in addition to Debian/Ubuntu
- Installer installs tkinter/setuptools when needed, prefers distro packages for rclone/restic, downloads restic via curl/wget to a temp dir, and verifies `vault` after install
- Uninstaller removes the pip `memory-vault` package and `~/.local/bin/vault`

## [1.0.0] - 2026-04-27

### Added
- Core backup and sync functionality
- CLI interface with comprehensive commands
- GUI with CustomTkinter
- Installation and uninstallation scripts
- Configuration wizard for Wasabi S3 setup
- Mount management with FUSE3
- Snapshot creation, listing, and restoration
- Sync folder management
- Activity logging
- System tray icon with status indicators
- Hybrid sync architecture with Rclone and Restic
- Multi-device support with hostname-aware snapshots
- RM-Shield protection against accidental deletion
- Bilingual support (English/Spanish)
- Systemd-free compatibility (works with OpenRC, runit, SysVinit)
- Two-bucket "Lean" architecture for optimal cost efficiency
- Auto-sync functionality
- Snapshot management with configurable retention policy

### Security
- AES-256 encryption for all snapshots
- Optional Object Lock (WORM mode) for vault bucket
- Secure credential storage in local configuration
