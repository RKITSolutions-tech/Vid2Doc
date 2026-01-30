Devcontainer & Environment Notes

Summary of environment fixes applied to make development easier:

- Added a minimal `video_processor.py` stub so the Flask app can import and start without heavy video-processing dependencies during development.
- Made heavy imaging and data stack imports optional at module import time (OpenCV, scikit-image, ReportLab, SQLAlchemy). When these packages are missing, functions that require them will raise a clear ImportError explaining how to install the missing dependency.
- Updated `.devcontainer/post_create.sh` to install project dependencies into the micromamba `dev` environment (excluding torch pins) and to create a lightweight `.venv` in the project root with a minimal set of runtime packages (Flask, reportlab, sqlalchemy, opencv-python-headless, scikit-image, ffmpeg-python, pillow).

Why these changes?
- Many CI/dev setups (and this devcontainer) don't include heavy packages like PyTorch or full OpenCV by default. Making these imports optional allows contributors to run and iterate on the web interface quickly while still preserving full functionality for users who install the full stack.

How to use the devcontainer
1. Rebuild the devcontainer (VS Code: Rebuild and Reopen in Container).
2. Post-create will create the `dev` micromamba environment and install project deps into it.
3. Activate micromamba: `micromamba activate dev`.
4. To run the web app via the project's venv: `source .venv/bin/activate` then `bash start_flask.sh full`.

If you prefer to install everything into a single Python environment, run:

  micromamba run -n dev pip install -r requirements.txt

or use your system/python venv and `pip install -r requirements.txt` as usual.

If you need assistance customizing the devcontainer for a specific CUDA/tooling combination, open an issue describing your host setup (CUDA version, desired PyTorch build) and we can update the post-create script accordingly.
