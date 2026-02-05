#!/usr/bin/env bash
# Helper placed at project root to create the project's .venv, install minimal deps, and start Flask
# Usage:
#   ./start_flask.sh              # create venv (if needed), install Flask, run app
#   ./start_flask.sh full         # install full requirements from requirements.txt then run
#   ./start_flask.sh [full] host port
# Environment:
#   DRY_RUN=1   -> perform setup but do not start the Flask server (useful for CI/testing)
#   PYTHON=/path/to/python -> use this Python interpreter when creating venv or as fallback

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

echo "Project root: $ROOT_DIR"

if [ ! -d ".venv" ]; then
  echo ".venv not found — creating virtualenv"
  # Use PYTHON env var if provided, otherwise prefer python3 then python
  if [ -n "${PYTHON:-}" ]; then
    PY_CMD="$PYTHON"
  elif command -v python3 >/dev/null 2>&1; then
    PY_CMD=python3
  elif command -v python >/dev/null 2>&1; then
    PY_CMD=python
  else
    echo "No python executable found (set PYTHON or install Python and add to PATH)." >&2
    exit 1
  fi
  "$PY_CMD" -m venv .venv
fi

# Prefer using the venv's python directly (avoids activation differences on Windows vs Unix)
if [ -x ".venv/bin/python" ]; then
  VENV_PY=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
elif [ -x ".venv/Scripts/python" ]; then
  VENV_PY=".venv/Scripts/python"
else
  # Fallback to PYTHON env var or whatever python is on PATH
  if [ -n "${PYTHON:-}" ]; then
    VENV_PY="$PYTHON"
  elif command -v python3 >/dev/null 2>&1; then
    VENV_PY=python3
  elif command -v python >/dev/null 2>&1; then
    VENV_PY=python
  else
    echo "No python found to use for venv operations (set PYTHON or install Python)." >&2
    exit 1
  fi
fi

echo "Using venv python: $VENV_PY"

echo "Upgrading pip tools"
"$VENV_PY" -m pip install --upgrade pip setuptools wheel >/dev/null

if [ "${1:-}" = "full" ]; then
  if [ ! -f requirements.txt ]; then
    echo "requirements.txt not found; cannot install full requirements" >&2
  else
    echo "Installing full requirements from requirements.txt (may take a while)"
    "$VENV_PY" -m pip install -r requirements.txt
  fi
else
  echo "Installing minimal runtime packages (Flask)"
  "$VENV_PY" -m pip install Flask
fi

export FLASK_APP=vid2doc:create_app
export FLASK_ENV=development

HOST=${2:-0.0.0.0}
PORT=${3:-5000}

echo "Starting Flask on $HOST:$PORT"

# If DRY_RUN is set, stop before starting the server (useful for tests)
if [ "${DRY_RUN:-0}" != "0" ]; then
  echo "DRY_RUN enabled - skipping starting Flask"
  exit 0
fi

"$VENV_PY" -m flask run --host="$HOST" --port="$PORT"

