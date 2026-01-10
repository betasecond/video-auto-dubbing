#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

OUT_DIR="${OUT_DIR:-$ROOT_DIR/artifacts}"
mkdir -p "$OUT_DIR"

TS="$(date +%Y%m%d_%H%M%S)"
BUNDLE_NAME="${BUNDLE_NAME:-indextts2_models_${TS}.tar.gz}"

echo "Exporting IndexTTS-2 model bundle..."
echo "Output: $OUT_DIR/$BUNDLE_NAME"

docker compose run --rm -T \
  -v "$OUT_DIR:/out" \
  -e BUNDLE_OUT="/out/$BUNDLE_NAME" \
  tts_service python - <<'PY'
import hashlib
import os
import tarfile
from pathlib import Path

out_path = Path(os.environ["BUNDLE_OUT"])
model_dir = Path(os.environ.get("INDEXTTS_MODEL_DIR", "/app/models/IndexTTS-2"))
cfg_path = Path(os.environ.get("INDEXTTS_CFG_PATH", str(model_dir / "config.yaml")))

if not cfg_path.exists():
    raise SystemExit(
        f"IndexTTS-2 not found at {cfg_path}. "
        "Download the model first (see docs/startup-guide.md)."
    )

out_path.parent.mkdir(parents=True, exist_ok=True)

with tarfile.open(out_path, "w:gz") as tar:
    tar.add(model_dir, arcname="IndexTTS-2")

sha256 = hashlib.sha256()
with out_path.open("rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        sha256.update(chunk)

sha_path = out_path.with_suffix(out_path.suffix + ".sha256")
sha_path.write_text(f"{sha256.hexdigest()}  {out_path.name}\n", encoding="utf-8")

print(f"OK: wrote {out_path} and {sha_path}")
PY
