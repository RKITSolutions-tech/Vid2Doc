#!/usr/bin/env bash
# Bootstrap helper for fresh clones. Creates .venv, installs full Python requirements,
# and checks for system tools (ffmpeg/ffprobe). It does NOT install system packages
# by default — it provides guided instructions.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$ROOT_DIR"

echo "Bootstrapping Vid2Doc in $ROOT_DIR"

# Create virtualenv if needed
if [ ! -d ".venv" ]; then
  echo ".venv not found — creating virtualenv"
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
  elif command -v python >/dev/null 2>&1; then
    python -m venv .venv
  else
    echo "No system python found. Install Python 3.12+ and retry." >&2
    exit 1
  fi
fi

VENV_PY=".venv/bin/python"
echo "Using venv python: $VENV_PY"

echo "Upgrading pip and installing full Python requirements (this may take a while)..."
"$VENV_PY" -m pip install --upgrade pip setuptools wheel >/dev/null
"$VENV_PY" -m pip install -r requirements.txt

# Check system tools
MISSING_SYSTEM=0
if command -v ffprobe >/dev/null 2>&1; then
  echo "✓ ffprobe found: $(command -v ffprobe)"
else
  echo "⚠ ffprobe not found. FFmpeg (ffprobe) is required for some fallback features."
  echo "  Install on Debian/Ubuntu: sudo apt update && sudo apt install ffmpeg"
  MISSING_SYSTEM=1
fi

if command -v git >/dev/null 2>&1; then
  echo "✓ git found"
else
  echo "⚠ git not found; install git to manage the repository"
  MISSING_SYSTEM=1
fi

if [ "$MISSING_SYSTEM" -eq 1 ]; then
  echo "\nOne or more system tools are missing. Please install them per the instructions above and re-run this script."
else
  echo "\nBootstrap complete. You can start the app with: ./start_flask.sh full"
fi

echo "You can run a quick environment check with: .venv/bin/python scripts/check_env.py"
