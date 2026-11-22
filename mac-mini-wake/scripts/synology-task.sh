#!/bin/sh
# DSM 控制面板 → 任务计划 → 用户定义的脚本
# 把本脚本路径填进去，或复制下面这行 curl 到任务计划中。
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)

if [ -f "$ROOT/config.env" ]; then
  # shellcheck disable=SC1091
  set -a
  . "$ROOT/config.env"
  set +a
fi

PORT=${HTTP_PORT:-8787}
TOKEN=${WAKE_TOKEN:-}

if [ -z "$TOKEN" ]; then
  echo "WAKE_TOKEN missing" >&2
  exit 2
fi

curl -fsS -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:${PORT}/wake"
echo
