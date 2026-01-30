"""Check runtime environment for required Python packages and system tools.

Exits with non-zero status if required elements are missing.

Usage:
  .venv/bin/python scripts/check_env.py
"""
import sys
import shutil
import importlib

REQUIRED_IMPORTS = {
    "flask": "Flask (web framework)",
    "sqlalchemy": "SQLAlchemy (ORM)",
    "reportlab": "reportlab (PDF generation)",
    "PIL": "Pillow (image handling, import as PIL)",
    "pytest": "pytest (tests)",
}

OPTIONAL_IMPORTS = {
    "cv2": "opencv-python-headless (OpenCV) — recommended for video metadata & frame extraction",
    "ffmpeg": "ffmpeg-python (python wrapper for FFmpeg)",
}

MISSING = []

print("Checking Python imports...")
for mod, desc in REQUIRED_IMPORTS.items():
    try:
        importlib.import_module(mod)
        print(f"✓ {desc} (imported {mod})")
    except Exception:
        print(f"✗ Missing: {desc} (cannot import {mod})")
        MISSING.append((mod, desc))

print("\nChecking optional/imported packages...")
for mod, desc in OPTIONAL_IMPORTS.items():
    try:
        importlib.import_module(mod)
        print(f"✓ {desc} (imported {mod})")
    except Exception:
        print(f"⚠ Optional missing: {desc} (cannot import {mod})")

print("\nChecking system tools...")
for tool in ("ffprobe", "ffmpeg", "git"):
    path = shutil.which(tool)
    if path:
        print(f"✓ {tool} found: {path}")
    else:
        print(f"✗ {tool} not found on PATH")
        if tool == "ffprobe":
            MISSING.append((tool, "FFmpeg/ffprobe is required for video metadata fallback"))

if MISSING:
    print("\nOne or more REQUIRED dependencies are missing. Install them and re-run this check.")
    for m in MISSING:
        print(f" - {m[1]}")
    sys.exit(2)

print("\nEnvironment looks good — all required packages and system tools are present.")
sys.exit(0)
