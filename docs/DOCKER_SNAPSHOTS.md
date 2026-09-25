# Docker snapshots (Restic only)

Run **memory-vault in a container** so the host does not need `restic`, `rclone`, or a Python install. This example is **snapshots only** (no Rclone sync).

## What you get

- Image builds memory-vault CLI + Restic
- First start: `restic init` (if needed) + one snapshot
- Then a snapshot every day at `SNAP_HOUR` (container local time / `TZ`)
- `KEEP_LAST` versions with **deduplication** (not N full copies of the dataset)
- Data on S3 is **client-side encrypted** (Restic password)

## Quick start

```bash
cd examples/docker-snapshots
cp docker-compose.yml docker-compose.override.yml   # optional: edit the bind mount
export WASABI_ACCESS_KEY=...
export WASABI_SECRET_KEY=...
export RESTIC_PASSWORD=...          # long random secret; losing it = lost backups
export WASABI_BUCKET=my-bucket      # empty Wasabi/S3 bucket for this repo
# Edit the volume line to mount your data read-only, then:
docker compose up -d --build
docker logs -f memory-vault-snapshots
```

## Environment

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `WASABI_ACCESS_KEY` | yes | — | S3 access key |
| `WASABI_SECRET_KEY` | yes | — | S3 secret key |
| `RESTIC_PASSWORD` | yes | — | Restic repo password |
| `WASABI_BUCKET` | yes | — | Bucket name (snapshots only) |
| `WASABI_REGION` | no | `eu-west-2` | Wasabi region |
| `BACKUP_PATH` | no | `/data/backup-src` | Path **inside** the container |
| `KEEP_LAST` | no | `3` | Restic `forget --keep-last` |
| `SNAP_HOUR` | no | `3` | Hour of day (0–23) for the daily snap |
| `HOSTNAME_TAG` | no | `docker-host` | Restic `--host` / device name |
| `TZ` | no | `UTC` | Timezone for `SNAP_HOUR` |

## Sync vs snap

| | Rclone sync | This example (Restic snap) |
| --- | --- | --- |
| Uploads only new bytes | yes | yes (content-defined chunks) |
| Files readable on S3 with API keys alone | usually yes | **no** (encrypted) |
| Point-in-time history | weak | yes (`KEEP_LAST`) |
| Good for container volume backups | possible | **recommended** |

Do **not** use the sync bucket for this workload. Use a dedicated snapshot bucket.

## Security notes

- Anyone with the Wasabi keys **and** `RESTIC_PASSWORD` can restore data.
- Anyone with only the Wasabi keys sees opaque blobs.
- Store `RESTIC_PASSWORD` in a password manager / secrets store; it is not recoverable from the bucket.
