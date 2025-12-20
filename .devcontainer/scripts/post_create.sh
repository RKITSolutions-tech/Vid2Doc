#!/usr/bin/env bash
set -euo pipefail

# Post-create script: create micromamba environment and install pytorch with cuda
MAMBA_PREFIX="/opt/micromamba"
ENV_NAME="video-doc"
PYTHON_VERSION="3.12"

echo "Creating micromamba environment and installing CUDA-enabled PyTorch..."
export MAMBA_EXE="$MAMBA_PREFIX/bin/micromamba"
if [ ! -x "$MAMBA_EXE" ]; then
  echo "micromamba not found at $MAMBA_EXE. Ensure the devcontainer Dockerfile installed micromamba."
  exit 1
fi

# Create environment.yaml to pin versions
cat > /workspace/.devcontainer/env-spec.yaml <<YAML
channels:
  - pytorch
  - nvidia
  - conda-forge
  - defaults
dependencies:
  - python=${PYTHON_VERSION}
  - pip
  - pip:
    - -r file:requirements.txt
  # Install pytorch with matching cuda toolkit via pytorch channel
  - pytorch
  - pytorch-cuda=12.1
  - torchvision
  - torchaudio
  - cudatoolkit-dev
YAML

# Create env
$MAMBA_EXE env create -p /opt/conda/envs/${ENV_NAME} -f /workspace/.devcontainer/env-spec.yaml || true

# Create activation script for convenience
cat > /etc/profile.d/activate_video_doc.sh <<'SH'
# Activate micromamba environment for interactive shells
if [ -x "/opt/micromamba/bin/micromamba" ]; then
  source /opt/micromamba/etc/profile.d/micromamba.sh
  micromamba activate -p /opt/conda/envs/video-doc || true
fi
SH

echo "Environment creation finished. Activate with: source /opt/micromamba/etc/profile.d/micromamba.sh && micromamba activate -p /opt/conda/envs/video-doc"
