Devcontainer instructions

This project uses CUDA and GPU-accelerated libraries. Because PyTorch/torchvision
binary compatibility is sensitive to the CUDA version, the recommended approach
is to install PyTorch via conda/mamba from the `pytorch` channel which provides
prebuilt `pytorch` + `pytorch-cuda` packages for common CUDA versions.

Steps to rebuild the devcontainer (from VS Code):

1. Open the Command Palette -> Remote-Containers: Rebuild and Reopen in Container
2. The devcontainer will use `.devcontainer/Dockerfile` as its base image (nvidia/cuda:12.1.1-devel-ubuntu22.04)
3. After the container is created, run the post-create script to install micromamba and the environment:

   ./ .devcontainer/post_create.sh

4. Activate the environment:

   micromamba activate dev

5. Verify GPU & transformers pipeline:

   python -c "import torch; print('cuda', torch.cuda.is_available(), torch.__version__)"
   python -c "from transformers import pipeline; print('pipeline ok', bool(pipeline('summarization', model='sshleifer/distilbart-cnn-12-6')))"

Notes:
- If `pytorch-cuda=12.1` is not available on the conda channel for a newer torch,
  you may need to tweak the CUDA version (e.g., 12.0/11.x) or use a different
  combination supported by the `pytorch` channel. The post-create script is a
  template; adjust the `micromamba install` line to pick the desired pytorch/pytorch-cuda version.
