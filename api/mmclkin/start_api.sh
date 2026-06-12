#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${MMCLKIN_ROOT:-C:/Project/DrugAgent/models/MMCLKin}:$(pwd):${PYTHONPATH:-}"

HOST="${MMCLKIN_API_HOST:-0.0.0.0}"
PORT="${MMCLKIN_API_PORT:-8020}"

uvicorn api.mmclkin.api:app --host "$HOST" --port "$PORT"
