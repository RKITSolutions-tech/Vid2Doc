# Lightweight devcontainer Dockerfile for VideoDocumentation
# Base: NVIDIA CUDA dev image to allow GPU-accelerated processing when available
FROM --platform=amd64 nvidia/cuda:12.1.1-devel-ubuntu22.04

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ARG VARIANT=3.11
ARG TORCH_VERSION=2.3.1+cu121
ARG CUDA_INDEX_URL=https://download.pytorch.org/whl/cu121

ENV PYTHONUNBUFFERED=1
WORKDIR /workspace

# Install minimal system dependencies and create the vscode user
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates curl git build-essential wget unzip python3 python3-venv python3-pip \
        sudo xdg-utils portaudio19-dev python3-pyaudio xz-utils gnupg; \
    rm -rf /var/lib/apt/lists/*; \
    groupadd --gid "${USER_GID}" "${USERNAME}" || true; \
    useradd -s /bin/bash --uid "${USER_UID}" --gid "${USER_GID}" -m "${USERNAME}" || true; \
    echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME}; \
    chmod 0440 /etc/sudoers.d/${USERNAME}; \
    usermod -aG sudo "${USERNAME}" || true; \
    mkdir -p /workspace; chown -R "${USER_UID}":"${USER_GID}" /workspace;

# Copy optional requirements.txt into image to support offline install during build
COPY requirements.txt /tmp/requirements.txt

# Install Python tooling and common runtime deps
RUN set -eux; \
    ln -sf /usr/bin/python3 /usr/bin/python || true; \
    pip3 install --upgrade pip; \
    # Attempt to install CUDA-aware PyTorch wheels (if available). If it fails, continue.
    pip3 install --index-url "${CUDA_INDEX_URL}" "torch==${TORCH_VERSION}" torchvision torchaudio --extra-index-url "${CUDA_INDEX_URL}" || true; \
    pip3 install --no-cache-dir numpy opencv-python-headless scikit-image scikit-learn ffmpeg-python pillow kornia || true; \
    if [ -f "/tmp/requirements.txt" ]; then \
        echo 'Installing requirements.txt (excluding torch entries)'; \
        grep -i -v -E '^\s*(torch|torchvision|torchaudio)\b' /tmp/requirements.txt > /tmp/req_filtered.txt || true; \
        pip3 install --no-cache-dir -r /tmp/req_filtered.txt || true; \
        rm -f /tmp/req_filtered.txt; \
    else \
        echo 'No requirements.txt found in build context'; \
    fi

# Install FFmpeg (try static build then fallback to apt)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates xz-utils wget curl gnupg; \
    rm -rf /var/lib/apt/lists/*; \
    echo 'Attempting to download BtbN FFmpeg static build'; \
    wget -q -O /tmp/ffmpeg-git-64bit-static.tar.xz https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-git-64bit-static.tar.xz || true; \
    if [ -f /tmp/ffmpeg-git-64bit-static.tar.xz ] && xz -t /tmp/ffmpeg-git-64bit-static.tar.xz 2>/dev/null; then \
        tar -xJf /tmp/ffmpeg-git-64bit-static.tar.xz -C /tmp; \
        cp /tmp/ffmpeg-*/ffmpeg /usr/local/bin/ffmpeg || true; \
        cp /tmp/ffmpeg-*/ffprobe /usr/local/bin/ffprobe || true; \
        chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe || true; \
        rm -rf /tmp/ffmpeg-* /tmp/ffmpeg-git-64bit-static.tar.xz; \
    else \
        apt-get update; apt-get install -y --no-install-recommends ffmpeg; rm -rf /var/lib/apt/lists/*; \
    fi

# Sanity checks are non-fatal
RUN ( /usr/local/bin/ffmpeg -hide_banner -filters | grep -i scale_npp ) || echo 'WARNING: scale_npp not found'; \
    ( /usr/local/bin/ffmpeg -hide_banner -encoders | grep -i nvenc ) || echo 'WARNING: nvenc not found'

# Ensure vscode user exists (idempotent) and switch to it for the devcontainer
RUN id -u "${USERNAME}" >/dev/null 2>&1 || ( groupadd --gid "${USER_GID}" "${USERNAME}" || true; useradd -s /bin/bash --uid "${USER_UID}" --gid "${USER_GID}" -m "${USERNAME}" || true )

USER ${USERNAME}
ENV HOME=/home/${USERNAME}
WORKDIR /workspace

CMD ["/bin/bash"]




