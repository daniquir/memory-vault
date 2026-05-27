# CLI Reference

Complete reference for all `vault` CLI commands.

## Global Options

- `--gui`, `-g`: Launch graphical interface instead of CLI
- `--help`: Show help message

## Commands

### setup

Run the interactive setup wizard to configure The Memory Vault.

```bash
vault setup
```

**Prompts:**
- Wasabi bucket name
- Access Key ID
- Secret Access Key
- Region (default: us-east-1)
- Encryption password for snapshots
- Object Lock (WORM mode) enable/disable
- Lock retention days (default: 90)

**What it does:**
- Creates configuration file at `~/.config/memory-vault/config.json`
- Initializes Restic repository
- Configures Wasabi Object Lock if enabled
- Sets up versioning on the bucket

---

### open

Mount the vault to a local directory.

```bash
vault open [--mount-point PATH]
```

**Options:**
- `--mount-point PATH`: Custom mount point (default: `~/Vault`)

**What it does:**
- Uses `rclone mount` to mount Wasabi bucket
- Enables automatic retry on network failure
- Creates mount point if it doesn't exist

**Example:**
```bash
vault open
vault open --mount-point ~/my-vault
```

---

### close

Unmount the vault and clean up.

```bash
vault close [--mount-point PATH]
```

**Options:**
- `--mount-point PATH`: Custom mount point (default: `~/Vault`)

**What it does:**
- Unmounts the FUSE mount
- Cleans up rclone cache
- Prevents data corruption

**Example:**
```bash
vault close
```

---

### snap

Create a snapshot of files.

```bash
vault snap --all | --path PATH
```

**Options:**
- `--all`: Snapshot all configured sync folders
- `--path PATH`: Snapshot a specific path

**What it does:**
- Creates encrypted snapshot with Restic
- Tags snapshot with hostname
- Updates last snapshot timestamp

**Examples:**
```bash
vault snap --all
vault snap --path /home/user/documents
```

---

### list

List snapshots.

```bash
vault list [--host NAME]
```

**Options:**
- `--host NAME`: Filter by hostname

**What it does:**
- Lists all snapshots or filter by device
- Shows snapshot ID, time, and paths
- Displays all registered devices if no host specified

**Examples:**
```bash
vault list                    # List all devices
vault list --host my-pc       # List snapshots for specific device
```

---

### restore

Restore a snapshot to a target directory.

```bash
vault restore SNAPSHOT_ID TARGET
```

**Arguments:**
- `SNAPSHOT_ID`: The snapshot ID to restore
- `TARGET`: Target directory path

**What it does:**
- Restores files from snapshot
- Preserves original structure
- Checks WORM status before deletion operations

**Example:**
```bash
vault restore abc123def456 /home/user/restore
```

---

### config

Interactive configuration of sync folders.

```bash
vault config
```

**What it does:**
- Shows current sync folders
- Allows adding/removing folders
- Saves configuration per device

**Interactive prompts:**
- Add folder to sync (or 'done' to finish)

**Example:**
```bash
vault config
# Current sync folders: /home/user/docs
# Add folder to sync (or 'done' to finish): /home/user/photos
# Add folder to sync (or 'done' to finish): done
# Configuration saved
```

---

### edit

Edit existing configuration values without recreating the full setup from scratch.

```bash
vault edit
```

**What it does:**
- Shows current configuration values
- Lets you update any field interactively
- Keeps existing values when you press Enter

**Example:**
```bash
vault edit
```

---

### shield

Manage RM-Shield protection.

```bash
vault shield --on | --off
```

**Options:**
- `--on`: Enable RM-Shield
- `--off`: Disable RM-Shield

**What it does:**
- Adds/removes shell aliases in `.bashrc` and `.zshrc`
- Replaces `rm` with `trash-put`
- Adds warning for vault mount point deletions
- Provides `rrm` for forced deletion

**Examples:**
```bash
vault shield --on
vault shield --off
vault shield    # Show current status
```

---

### status

Show vault status.

```bash
vault status [--mount-point PATH]
```

**Options:**
- `--mount-point PATH`: Custom mount point (default: `~/Vault`)

**What it does:**
- Shows mount status
- Displays last snapshot time
- Shows used space in repository

**Example:**
```bash
vault status
# Output:
# Mounted: /home/user/Vault
# Last snapshot: 2026-04-25T10:00:00
# Used space: 2.45 GB
```

---

## Exit Codes

- `0`: Success
- `1`: Error or failure

## Environment Variables

- `LANG`: System language for i18n (auto-detected)
- `HOME`: User home directory for configuration

## Configuration File

Location: `~/.config/memory-vault/config.json`

See README.md for configuration structure.
