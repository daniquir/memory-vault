#!/bin/sh
# memory-vault en modo solo-snap (Restic). Sin sync Rclone.
# Secretos por entorno. Monta BACKUP_PATH (por defecto /data/backup-src).
set -eu

CONFIG_DIR="${HOME}/.config/memory-vault"
ORIGINALS="${BACKUP_PATH:-/data/backup-src}"
KEEP_LAST="${KEEP_LAST:-3}"
SNAP_HOUR="${SNAP_HOUR:-3}"
HOSTNAME_TAG="${HOSTNAME_TAG:-docker-host}"

: "${WASABI_ACCESS_KEY:?set WASABI_ACCESS_KEY}"
: "${WASABI_SECRET_KEY:?set WASABI_SECRET_KEY}"
: "${RESTIC_PASSWORD:?set RESTIC_PASSWORD}"
: "${WASABI_BUCKET:?set WASABI_BUCKET}"
: "${WASABI_REGION:=eu-west-2}"

mkdir -p "$CONFIG_DIR" /data/restic-cache
export RESTIC_CACHE_DIR=/data/restic-cache

python3 - <<PY
import json, os
from pathlib import Path

host = os.environ.get("HOSTNAME_TAG", "docker-host")
path = os.environ.get("BACKUP_PATH", "/data/backup-src")
cfg = {
    "storage": {
        "provider": "wasabi",
        "bucket": "",
        "access_key": os.environ["WASABI_ACCESS_KEY"],
        "secret_key": os.environ["WASABI_SECRET_KEY"],
        "region": os.environ.get("WASABI_REGION", "eu-west-2"),
        "object_lock": False,
        "lock_days": 0,
        "versioning": "disabled",
        "sync_bucket": "",
        "sync_region": os.environ.get("WASABI_REGION", "eu-west-2"),
        "sync_versioning": 0,
        "vault_bucket": os.environ["WASABI_BUCKET"],
        "vault_region": os.environ.get("WASABI_REGION", "eu-west-2"),
    },
    "devices": {
        host: {"sync_folders": [path], "last_snap": None},
    },
    "security": {
        "rm_shield": False,
        "encryption_password": os.environ["RESTIC_PASSWORD"],
    },
    "ui": {"language": "en", "start_minimized": True},
    "snapshots": {
        "keep_last": int(os.environ.get("KEEP_LAST", "3")),
        "auto_snap_interval": "daily",
    },
    "sync": {"auto_sync": False},
}
out = Path(os.environ["HOME"]) / ".config/memory-vault/config.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(cfg, indent=2) + "\n")
os.chmod(out, 0o600)
print("wrote", out)
PY

if [ ! -d "$ORIGINALS" ]; then
  echo "missing backup path: $ORIGINALS" >&2
  exit 2
fi

echo "== restic init (idempotent) =="
export RESTIC_REPOSITORY="s3:s3.${WASABI_REGION}.wasabisys.com/${WASABI_BUCKET}"
export AWS_ACCESS_KEY_ID="$WASABI_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$WASABI_SECRET_KEY"
export RESTIC_PASSWORD
if ! restic snapshots >/dev/null 2>&1; then
  restic init
  echo "repository initialized"
else
  echo "repository already exists"
fi

run_snap() {
  echo "== snap $(date -Iseconds) =="
  vault snap --all
  echo "== done $(date -Iseconds) =="
}

run_snap || echo "initial snap failed; will retry on schedule" >&2

while true; do
  now_h=$(date +%H)
  now_m=$(date +%M)
  if [ "$now_h" = "$(printf '%02d' "$SNAP_HOUR")" ] && [ "$now_m" = "00" ]; then
    run_snap || true
    sleep 60
  fi
  sleep 30
done
