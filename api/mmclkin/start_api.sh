#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
MMCLKIN_ROOT="${MMCLKIN_ROOT:-${PROJECT_ROOT}/models/MMCLKin}"

if [[ -n "${CONDA_PREFIX:-}" ]]; then
  export LD_LIBRARY_PATH="${CONDA_PREFIX}/lib:${LD_LIBRARY_PATH:-}"
fi

export DGLBACKEND="${DGLBACKEND:-pytorch}"
export MMCLKIN_ROOT
export PYTHONPATH="${MMCLKIN_ROOT}:${PROJECT_ROOT}:${PYTHONPATH:-}"

HOST="${MMCLKIN_API_HOST:-0.0.0.0}"
PORT="${MMCLKIN_API_PORT:-8020}"

uvicorn api.mmclkin.api:app --host "$HOST" --port "$PORT"
