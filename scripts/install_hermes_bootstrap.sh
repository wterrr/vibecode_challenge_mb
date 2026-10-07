#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIN="f97608f178d1ffeca59860195ab7da295f7c8e5f"
RUNTIME="$ROOT/.hermes_runtime"
INSTALL_DIR="$RUNTIME/hermes-agent"
HERMES_HOME="$RUNTIME/home"
INSTALLER="$RUNTIME/install-hermes-bootstrap.sh"

mkdir -p "$RUNTIME"

curl -fsSL \
  --retry 8 \
  --retry-all-errors \
  --retry-delay 5 \
  --retry-max-time 240 \
  "https://raw.githubusercontent.com/NousResearch/hermes-agent/$PIN/scripts/install.sh" \
  -o "$INSTALLER"

bash "$INSTALLER" --commit "$PIN" --force-commit --skip-setup --skip-browser --skip-computer-use --dir "$INSTALL_DIR" --hermes-home "$HERMES_HOME"

ACTUAL="$(git -C "$INSTALL_DIR" rev-parse HEAD)"
if [[ "$ACTUAL" != "$PIN" ]]; then
  echo "HERMES_BOOTSTRAP_INSTALL=FAIL expected=$PIN actual=$ACTUAL" >&2
  exit 1
fi

mkdir -p "$HERMES_HOME"
cp "$ROOT/hermes/bootstrap/config.yaml" "$HERMES_HOME/config.yaml"

echo "HERMES_BOOTSTRAP_INSTALL=PASS"
echo "Hermes commit: $ACTUAL"
echo "Hermes home:   $HERMES_HOME"
echo "Next: put OPENROUTER_API_KEY in $ROOT/.env, then run:"
echo "  python scripts/run_hermes_bootstrap_smoke.py"
