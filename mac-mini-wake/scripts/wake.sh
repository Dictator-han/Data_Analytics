#!/bin/sh
# One-shot Wake-on-LAN from the project directory (Docker or local Python).
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"

if [ -f "$ROOT/config.env" ]; then
  # shellcheck disable=SC1091
  set -a
  . "$ROOT/config.env"
  set +a
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  if docker compose ps --status running --services 2>/dev/null | grep -qx mac-mini-wake; then
    echo "Service is running; calling HTTP API..."
    if [ -z "${WAKE_TOKEN:-}" ]; then
      echo "WAKE_TOKEN missing in config.env" >&2
      exit 2
    fi
    curl -fsS -X POST \
      -H "Authorization: Bearer ${WAKE_TOKEN}" \
      -H "Content-Type: application/json" \
      "http://127.0.0.1:${HTTP_PORT:-8787}/wake"
    echo
    exit 0
  fi
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$ROOT/wake.py" "$@"
fi

echo "Neither a running docker compose service nor python3 was found." >&2
exit 1
