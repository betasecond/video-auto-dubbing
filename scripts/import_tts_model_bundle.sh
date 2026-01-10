#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ "${1:-}" = "" ]; then
  echo "Usage: $0 <bundle.tar.gz | https://.../bundle.tar.gz>"
  exit 2
fi

INPUT="$1"
WORK_DIR="${WORK_DIR:-$ROOT_DIR/artifacts}"
mkdir -p "$WORK_DIR"

if [[ "$INPUT" =~ ^https?:// ]]; then
  if command -v curl >/dev/null 2>&1; then
    DOWNLOADED="$WORK_DIR/indextts2_models_download.tar.gz"
    echo "Downloading: $INPUT"
    curl -fL --retry 3 --retry-delay 2 -o "$DOWNLOADED" "$INPUT"
  elif command -v wget >/dev/null 2>&1; then
    DOWNLOADED="$WORK_DIR/indextts2_models_download.tar.gz"
    echo "Downloading: $INPUT"
    wget -O "$DOWNLOADED" "$INPUT"
  else
    echo "Error: need curl or wget to download: $INPUT"
    exit 2
  fi
  BUNDLE_PATH="$DOWNLOADED"
else
  if [ -f "$INPUT" ]; then
    BUNDLE_PATH="$INPUT"
  elif [ -f "$ROOT_DIR/$INPUT" ]; then
    BUNDLE_PATH="$ROOT_DIR/$INPUT"
  else
    echo "Error: bundle not found: $INPUT"
    exit 2
  fi
fi

BUNDLE_DIR="$(cd "$(dirname "$BUNDLE_PATH")" && pwd)"
BUNDLE_FILE="$(basename "$BUNDLE_PATH")"

echo "Importing IndexTTS-2 model bundle into docker volume..."
echo "Bundle: $BUNDLE_DIR/$BUNDLE_FILE"

docker compose run --rm -T \
  -v "$BUNDLE_DIR:/in:ro" \
  -e BUNDLE_IN="/in/$BUNDLE_FILE" \
  tts_service python - <<'PY'
import os
import shutil
import tarfile
from pathlib import Path

bundle = Path(os.environ["BUNDLE_IN"])
target_root = Path("/app/models")
target_dir = target_root / "IndexTTS-2"

def is_within_directory(base: Path, path: Path) -> bool:
    try:
        base_resolved = base.resolve()
        path_resolved = path.resolve()
    except FileNotFoundError:
        # For paths that don't exist yet (during extraction), resolve parent.
        base_resolved = base.resolve()
        path_resolved = (base / path).parent.resolve()
    return str(path_resolved).startswith(str(base_resolved))

if target_dir.exists():
    shutil.rmtree(target_dir)

with tarfile.open(bundle, "r:*") as tar:
    for member in tar.getmembers():
        member_path = target_root / member.name
        if not is_within_directory(target_root, member_path):
            raise SystemExit(f"Unsafe path in tar: {member.name}")
    tar.extractall(path=target_root)

cfg = target_dir / "config.yaml"
if not cfg.exists():
    raise SystemExit(f"Import finished but config missing: {cfg}")

print(f"OK: restored {target_dir}")
PY
