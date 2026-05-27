# Changelog

All notable changes to The Memory Vault will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial public release
- Hybrid sync architecture with Rclone and Restic
- Multi-device support with hostname-aware snapshots
- RM-Shield protection against accidental deletion
- Bilingual support (English/Spanish)
- GUI with system tray integration
- Systemd-free compatibility (works with OpenRC, runit, SysVinit)
- Two-bucket "Lean" architecture for optimal cost efficiency
- Auto-sync functionality
- Snapshot management with configurable retention policy

### Security
- AES-256 encryption for all snapshots
- Optional Object Lock (WORM mode) for vault bucket
- Secure credential storage in local configuration

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
