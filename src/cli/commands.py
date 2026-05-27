"""CLI commands for The Memory Vault."""

import argparse
import sys
from pathlib import Path

from ..utils.config import Config
from ..utils.i18n import I18n
from ..utils.shield import Shield
from ..core.rclone_wrapper import RcloneWrapper
from ..core.restic_wrapper import ResticWrapper
from ..core.mount_manager import MountManager
from ..core.hostname import get_hostname
from ..core.binary_detector import BinaryDetector
from ..core.worm_manager import WORMManager


def cmd_setup(args) -> int:
    """Run interactive setup wizard."""
    config = Config()
    i18n = I18n(config.get("ui.language", "auto"))

    print(i18n.t("setup_welcome"))
    print()

    # Ask which functionalities to configure
    print("Select functionalities to configure:")
    print("1. Sync only (Rclone for daily use)")
    print("2. Snapshots only (Restic for backups)")
    print("3. Both Sync and Snapshots")
    choice = input("Enter choice [1/2/3]: ").strip()

    sync_enabled = choice in ["1", "3"]
    snapshots_enabled = choice in ["2", "3"]

    if not sync_enabled and not snapshots_enabled:
        print("Invalid choice. Please run setup again.")
        return 1

    # Common Wasabi credentials
    print("\nWasabi Credentials:")
    access_key = input("Access Key ID: ").strip()
    secret_key = input("Secret Access Key: ").strip()

    # Sync configuration
    sync_bucket = ""
    sync_region = "us-east-1"
    if sync_enabled:
        print("\nSync Configuration:")
        sync_bucket = input("Sync Bucket Name: ").strip()
        if not sync_bucket:
            print("Error: Sync Bucket Name is required")
            return 1
        sync_region = input("Sync Bucket Region [us-east-1]: ").strip() or "us-east-1"

    # Snapshots configuration
    vault_bucket = ""
    vault_region = "us-east-1"
    password = ""
    keep_last = 3
    auto_snap_interval = "daily"
    if snapshots_enabled:
        print("\nSnapshots Configuration:")
        vault_bucket = input("Vault Bucket Name (for snapshots with Restic): ").strip()
        vault_region = input("Vault Bucket Region [us-east-1]: ").strip() or "us-east-1"
        password = input("Encryption Password: ").strip()

        keep_last_input = input("Number of snapshots to keep [3]: ").strip()
        if keep_last_input:
            try:
                keep_last = int(keep_last_input)
            except ValueError:
                keep_last = 3

        auto_snap_input = input("Automatic snapshot interval (daily, weekly, none) [daily]: ").strip().lower()
        auto_snap_interval = auto_snap_input if auto_snap_input in ["daily", "weekly", "none"] else "daily"

    # Save configuration
    config.set("storage.access_key", access_key)
    config.set("storage.secret_key", secret_key)

    if sync_enabled:
        config.set("storage.sync_bucket", sync_bucket)
        config.set("storage.sync_region", sync_region)

    if snapshots_enabled:
        config.set("storage.vault_bucket", vault_bucket)
        config.set("storage.vault_region", vault_region)
        config.set("snapshots.keep_last", keep_last)
        config.set("snapshots.auto_snap_interval", auto_snap_interval)
        config.set("security.encryption_password", password)

    config.save()

    # Initialize restic repository if snapshots enabled
    if snapshots_enabled:
        try:
            restic = ResticWrapper(config._config)
            success, msg = restic.init_repo()
            if not success:
                print(f"Error: {msg}")
                return 1
        except Exception as e:
            print(f"Error: {str(e)}")
            return 1

    print("Setup completed successfully!")
    return 0


def cmd_edit(args) -> int:
    """Edit existing configuration."""
    config = Config()
    i18n = I18n(config.get("ui.language", "auto"))

    if not config.is_configured():
        print("Error: No configuration found. Please run 'vault setup' first.")
        return 1

    storage = config._config.get("storage", {})
    snapshots = config._config.get("snapshots", {})
    security = config._config.get("security", {})

    print("Current Configuration:")
    print("=" * 50)

    # Sync configuration
    if config.is_sync_configured():
        print(f"\nSync Configuration:")
        print(f"  Sync Bucket: {storage.get('sync_bucket', '')}")
        print(f"  Sync Region: {storage.get('sync_region', 'us-east-1')}")
        print(f"  Access Key: {storage.get('access_key', '')}")
        print(f"  Secret Key: {'*' * len(storage.get('secret_key', ''))}")

    # Snapshots configuration
    if config.is_snapshots_configured():
        print(f"\nSnapshots Configuration:")
        print(f"  Vault Bucket: {storage.get('vault_bucket', '')}")
        print(f"  Vault Region: {storage.get('vault_region', 'us-east-1')}")
        print(f"  Encryption Password: {'*' * len(security.get('encryption_password', ''))}")
        print(f"  Keep Last: {snapshots.get('keep_last', 3)}")
        print(f"  Auto Snap Interval: {snapshots.get('auto_snap_interval', 'daily')}")

    print("\n" + "=" * 50)
    print("Press Enter to keep current value, or enter new value.\n")

    # Edit Sync configuration
    if config.is_sync_configured():
        print("Edit Sync Configuration:")
        sync_bucket = input(f"Sync Bucket [{storage.get('sync_bucket', '')}]: ").strip()
        if sync_bucket:
            config.set("storage.sync_bucket", sync_bucket)

        sync_region = input(f"Sync Region [{storage.get('sync_region', 'us-east-1')}]: ").strip()
        if sync_region:
            config.set("storage.sync_region", sync_region)

        access_key = input(f"Access Key [{storage.get('access_key', '')}]: ").strip()
        if access_key:
            config.set("storage.access_key", access_key)

        secret_key = input(f"Secret Key [****]: ").strip()
        if secret_key:
            config.set("storage.secret_key", secret_key)

    # Edit Snapshots configuration
    if config.is_snapshots_configured():
        print("\nEdit Snapshots Configuration:")
        vault_bucket = input(f"Vault Bucket [{storage.get('vault_bucket', '')}]: ").strip()
        if vault_bucket:
            config.set("storage.vault_bucket", vault_bucket)

        vault_region = input(f"Vault Region [{storage.get('vault_region', 'us-east-1')}]: ").strip()
        if vault_region:
            config.set("storage.vault_region", vault_region)

        password = input(f"Encryption Password [****]: ").strip()
        if password:
            config.set("security.encryption_password", password)

        keep_last_input = input(f"Keep Last [{snapshots.get('keep_last', 3)}]: ").strip()
        if keep_last_input:
            try:
                keep_last = int(keep_last_input)
                config.set("snapshots.keep_last", keep_last)
            except ValueError:
                print("Invalid value for Keep Last. Keeping current value.")

        auto_snap_input = input(f"Auto Snap Interval (daily/weekly/none) [{snapshots.get('auto_snap_interval', 'daily')}]: ").strip().lower()
        if auto_snap_input in ["daily", "weekly", "none"]:
            config.set("snapshots.auto_snap_interval", auto_snap_input)

    config.save()
    print("\nConfiguration updated successfully!")
    return 0


def cmd_open(args) -> int:
    """Mount the vault."""
    config = Config()
    i18n = I18n(config.get("ui.language", "auto"))

    if not config.is_sync_configured():
        print("Error: Sync functionality is not configured. Please run 'vault setup' and select Sync.")
        return 1
    
    print(i18n.t("open_mounting"))
    
    try:
        mount_manager = MountManager(config._config)
        success, msg = mount_manager.mount_with_retry(args.mount_point or "~/Vault")
        
        if success:
            print(i18n.t("open_success", msg))
            return 0
        else:
            print(i18n.t("open_error", msg))
            return 1
    except Exception as e:
        print(i18n.t("open_error", str(e)))
        return 1


def cmd_close(args) -> int:
    """Unmount the vault."""
    config = Config()
    i18n = I18n(config.get("ui.language", "auto"))
    
    print(i18n.t("close_unmounting"))
    
    try:
        mount_manager = MountManager(config._config)
        success, msg = mount_manager.unmount(args.mount_point or "~/Vault")
        
        if success:
            mount_manager.cleanup_cache(args.mount_point or "~/Vault")
            print(i18n.t("close_success"))
            return 0
        else:
            print(i18n.t("close_error", msg))
            return 1
    except Exception as e:
        print(i18n.t("close_error", str(e)))
        return 1


def cmd_snap(args) -> int:
    """Create a snapshot."""
    config = Config()
    i18n = I18n(config.get("ui.language", "auto"))

    if not config.is_snapshots_configured():
        print("Error: Snapshots functionality is not configured. Please run 'vault setup' and select Snapshots.")
        return 1
    
    # Determine path to snapshot
    if args.all:
        # Snapshot all configured sync folders
        device_config = config.get_device_config()
        sync_folders = device_config.get("sync_folders", [])
        if not sync_folders:
            print(i18n.t("snap_no_path"))
            return 1
        paths = sync_folders
    elif args.path:
        paths = [args.path]
    else:
        print(i18n.t("snap_no_path"))
        return 1
    
    print(i18n.t("snap_creating"))
    
    try:
        restic = ResticWrapper(config._config)
        hostname = get_hostname()
        
        for path in paths:
            if not Path(path).exists():
                print(i18n.t("error_path_not_found", path))
                continue
            
            success, msg = restic.backup(path, hostname)
            if success:
                print(i18n.t("snap_success", path))
            else:
                print(i18n.t("snap_error", msg))
                return 1
        
        # Update last snap timestamp
        from datetime import datetime
        device_config = config.get_device_config()
        device_config["last_snap"] = datetime.now().isoformat()
        config.update_device_config(hostname, device_config)
        
        return 0
    except Exception as e:
        print(i18n.t("snap_error", str(e)))
        return 1


def cmd_list(args) -> int:
    """List snapshots."""
    config = Config()
    i18n = I18n(config.get("ui.language", "auto"))
    
    if not config.is_configured():
        print(i18n.t("error_not_configured"))
        return 1
    
    try:
        restic = ResticWrapper(config._config)
        
        if args.host:
            success, snapshots = restic.list_snapshots(args.host)
            if success and snapshots:
                print(i18n.t("list_snapshots", args.host))
                for snap in snapshots:
                    print(f"  - {snap['id']}: {snap['time']} ({snap['paths']})")
            else:
                print(i18n.t("list_no_snapshots"))
        else:
            # List all devices
            devices = config.get_all_devices()
            print(i18n.t("list_all_devices"))
            for hostname, device_config in devices.items():
                last_snap = device_config.get("last_snap", "Never")
                print(f"  - {hostname}: Last snap {last_snap}")
        
        return 0
    except Exception as e:
        print(i18n.t("status_error", str(e)))
        return 1


def cmd_restore(args) -> int:
    """Restore a snapshot."""
    config = Config()
    i18n = I18n(config.get("ui.language", "auto"))
    
    if not config.is_configured():
        print(i18n.t("error_not_configured"))
        return 1
    
    if not args.snapshot_id or not args.target:
        print("Usage: vault restore <snapshot_id> <target_path>")
        return 1
    
    print(i18n.t("restore_restoring", args.snapshot_id, args.target))
    
    try:
        restic = ResticWrapper(config._config)
        success, msg = restic.restore(args.snapshot_id, args.target)
        
        if success:
            print(i18n.t("restore_success"))
            return 0
        else:
            print(i18n.t("restore_error", msg))
            return 1
    except Exception as e:
        print(i18n.t("restore_error", str(e)))
        return 1


def cmd_config(args) -> int:
    """Configure sync folders."""
    config = Config()
    i18n = I18n(config.get("ui.language", "auto"))
    
    hostname = get_hostname()
    device_config = config.get_device_config(hostname)
    sync_folders = device_config.get("sync_folders", [])
    
    print(i18n.t("config_current", ", ".join(sync_folders) or "None"))
    
    while True:
        folder = input(i18n.t("config_add")).strip()
        if folder.lower() == "done":
            break
        
        if Path(folder).exists():
            if folder not in sync_folders:
                sync_folders.append(folder)
            device_config["sync_folders"] = sync_folders
            config.update_device_config(hostname, device_config)
        else:
            print(i18n.t("error_path_not_found", folder))
    
    print(i18n.t("config_saved"))
    return 0


def cmd_shield(args) -> int:
    """Enable or disable RM-Shield."""
    config = Config()
    i18n = I18n(config.get("ui.language", "auto"))
    
    shield = Shield()
    
    if args.on:
        print(i18n.t("shield_enabling"))
        success, msg = shield.enable()
        if success:
            config.set("security.rm_shield", True)
            config.save()
            print(i18n.t("shield_enabled"))
            return 0
        else:
            print(i18n.t("shield_error", msg))
            return 1
    elif args.off:
        print(i18n.t("shield_disabling"))
        success, msg = shield.disable()
        if success:
            config.set("security.rm_shield", False)
            config.save()
            print(i18n.t("shield_disabled"))
            return 0
        else:
            print(i18n.t("shield_error", msg))
            return 1
    else:
        # Show current status
        enabled = shield.is_enabled()
        print(f"RM-Shield: {'enabled' if enabled else 'disabled'}")
        return 0


def cmd_status(args) -> int:
    """Show vault status."""
    config = Config()
    i18n = I18n(config.get("ui.language", "auto"))
    
    if not config.is_configured():
        print(i18n.t("error_not_configured"))
        return 1
    
    try:
        # Check mount status
        mount_manager = MountManager(config._config)
        mount_status = mount_manager.get_mount_status(args.mount_point or "~/Vault")
        
        if mount_status["mounted"]:
            print(i18n.t("status_mounted", mount_status["mount_point"]))
        else:
            print(i18n.t("status_not_mounted"))
        
        # Check last snapshot
        hostname = get_hostname()
        device_config = config.get_device_config(hostname)
        last_snap = device_config.get("last_snap")
        
        if last_snap:
            print(i18n.t("status_last_snap", last_snap))
        else:
            print(i18n.t("status_no_snap"))
        
        # Check repository stats
        restic = ResticWrapper(config._config)
        success, stats = restic.stats()
        if success:
            total_size = stats.get("total_size", 0)
            total_size_gb = total_size / (1024 ** 3)
            print(i18n.t("status_space", f"{total_size_gb:.2f} GB"))
        
        return 0
    except Exception as e:
        print(i18n.t("status_error", str(e)))
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="The Memory Vault - Multi-device backup and sync tool",
        prog="vault"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # setup command
    subparsers.add_parser("setup", help="Run interactive setup wizard")
    
    # open command
    open_parser = subparsers.add_parser("open", help="Mount the vault")
    open_parser.add_argument("--mount-point", help="Mount point path (default: ~/Vault)")
    
    # close command
    close_parser = subparsers.add_parser("close", help="Unmount the vault")
    close_parser.add_argument("--mount-point", help="Mount point path (default: ~/Vault)")
    
    # snap command
    snap_parser = subparsers.add_parser("snap", help="Create a snapshot")
    snap_group = snap_parser.add_mutually_exclusive_group(required=True)
    snap_group.add_argument("--all", action="store_true", help="Snapshot all configured folders")
    snap_group.add_argument("--path", help="Snapshot specific path")
    
    # list command
    list_parser = subparsers.add_parser("list", help="List snapshots")
    list_parser.add_argument("--host", help="Filter by hostname")
    
    # restore command
    restore_parser = subparsers.add_parser("restore", help="Restore a snapshot")
    restore_parser.add_argument("snapshot_id", help="Snapshot ID to restore")
    restore_parser.add_argument("target", help="Target directory")
    
    # config command
    subparsers.add_parser("config", help="Configure sync folders")

    # edit command
    subparsers.add_parser("edit", help="Edit existing configuration")
    
    # shield command
    shield_parser = subparsers.add_parser("shield", help="Manage RM-Shield protection")
    shield_group = shield_parser.add_mutually_exclusive_group()
    shield_group.add_argument("--on", action="store_true", help="Enable RM-Shield")
    shield_group.add_argument("--off", action="store_true", help="Disable RM-Shield")
    
    # status command
    status_parser = subparsers.add_parser("status", help="Show vault status")
    status_parser.add_argument("--mount-point", help="Mount point path (default: ~/Vault)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Map commands to functions
    commands = {
        "setup": cmd_setup,
        "open": cmd_open,
        "close": cmd_close,
        "snap": cmd_snap,
        "list": cmd_list,
        "restore": cmd_restore,
        "config": cmd_config,
        "edit": cmd_edit,
        "shield": cmd_shield,
        "status": cmd_status
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
