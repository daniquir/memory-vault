#!/usr/bin/env python3
"""Entry point script for The Memory Vault."""

import sys
import os
import fcntl

# When running from the repository (not as an installed package), put the
# project root on sys.path so `import src.*` resolves correctly.
script_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(os.path.join(script_dir, "src")) and script_dir not in sys.path:
    sys.path.insert(0, script_dir)


def _check_single_instance():
    """Check if another instance is already running.
    
    Returns:
        True if this is the only instance, False if another is running
    """
    lock_file = os.path.expanduser("~/.config/memory-vault/.lock")
    lock_dir = os.path.dirname(lock_file)
    
    # Create lock directory if it doesn't exist
    os.makedirs(lock_dir, exist_ok=True)
    
    try:
        # Try to acquire exclusive lock
        lock_fd = open(lock_file, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Write PID to lock file
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return True, lock_fd
    except (IOError, BlockingIOError):
        # Another instance is running
        return False, None


def main_entry():
    """Main entry point that detects CLI or GUI mode."""
    # Check for --gui flag
    if "--gui" in sys.argv or "-g" in sys.argv:
        # Remove the flag from argv
        sys.argv = [arg for arg in sys.argv if arg not in ["--gui", "-g"]]
        
        # Check for single instance (only for GUI mode)
        is_single, lock_fd = _check_single_instance()
        if not is_single:
            print("The Memory Vault GUI is already running.")
            sys.exit(0)
        
        # Store lock fd in global to keep it alive
        global _lock_fd
        _lock_fd = lock_fd

        try:
            from src.gui.main_window import launch_gui
        except ImportError as exc:
            print("Error: Cannot load The Memory Vault GUI.")
            print(f"Details: {exc}")
            print("On Fedora/RHEL install: sudo dnf install python3-tkinter")
            print("On Debian/Ubuntu install: sudo apt install python3-tk")
            sys.exit(1)

        launch_gui()
    else:
        try:
            from src.cli.commands import main
        except ImportError as exc:
            print("Error: Cannot find The Memory Vault modules. Please install the package.")
            print(f"Details: {exc}")
            sys.exit(1)
        # Run CLI
        sys.exit(main())


if __name__ == "__main__":
    main_entry()
