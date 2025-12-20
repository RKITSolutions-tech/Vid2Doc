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
