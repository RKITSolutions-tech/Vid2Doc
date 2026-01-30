#!/usr/bin/env bash
set -euo pipefail

echo "Installing micromamba (standalone) into ~/micromamba"
MAMBA_DIR="$HOME/micromamba"
mkdir -p "$MAMBA_DIR"
curl -L https://micromamba.snakepit.net/api/micromamba/linux-64/latest | tar -xvj -C "$MAMBA_DIR" --strip-components=1
export PATH="$MAMBA_DIR/bin:$PATH"

MICONDA_BIN="$MAMBA_DIR/bin/micromamba"

echo "Creating conda environment 'dev' with Python 3.10"
"$MICONDA_BIN" create -y -n dev python=3.10 -c conda-forge

echo "Installing PyTorch and CUDA-enabled packages from pytorch channel"
# Example for pytorch-cuda 12.1; adjust if a different subpackage is desired.
"$MICONDA_BIN" install -y -n dev -c pytorch -c nvidia pytorch pytorch-cuda=12.1 torchvision torchaudio -c conda-forge

echo "Environment ready. Activate with: micromamba activate dev"

# Install project Python dependencies into the micromamba 'dev' env (excluding torch entries)
# This avoids needing to re-install everything later and provides a ready-to-use environment
# for running the Flask app, generating PDFs, and DB-backed features.
echo "Installing project Python dependencies into micromamba 'dev' environment"
"$MICONDA_BIN" run -n dev pip install --upgrade pip || true
if [ -f "/workspace/requirements.txt" ]; then
  grep -i -v -E '^\s*(torch|torchvision|torchaudio)\b' /workspace/requirements.txt > /workspace/req_filtered.txt || true
  "${MICONDA_BIN}" run -n dev pip install --no-cache-dir -r /workspace/req_filtered.txt || true
  rm -f /workspace/req_filtered.txt || true
fi

# Create a lightweight project .venv and install minimal runtime packages so
# running `bash start_flask.sh` in the devcontainer will work out-of-the-box.
# This mirrors the workflow used by developers who prefer the project venv.
echo "Creating project .venv and installing minimal runtime packages (.venv will be placed in /workspace/.venv)"
if [ ! -d "/workspace/.venv" ]; then
  /usr/bin/python -m venv /workspace/.venv || true
fi
/workspace/.venv/bin/python -m pip install --upgrade pip setuptools wheel || true
# Install a small set of packages required for the web UI and PDF generation
# Also install testing tools so pytest is available in the project's .venv
/workspace/.venv/bin/pip install --no-cache-dir Flask reportlab sqlalchemy opencv-python-headless scikit-image ffmpeg-python pillow pytest pytest-order numpy moviepy imageio imageio-ffmpeg pydub || true

echo "Dev environment setup complete. You can activate the micromamba env with: micromamba activate dev"
echo "To use the project's .venv: source .venv/bin/activate; to install full requirements run: bash start_flask.sh full"
