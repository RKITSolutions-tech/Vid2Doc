#!/usr/bin/env python
"""Demo script to process demo_video.mp4"""
import os
import sys

# Check if demo video exists
demo_video = 'videos/demo_video.mp4'

if not os.path.exists(demo_video):
    print(f"❌ Demo video not found at: {demo_video}")
    print("\nThis script expects a demo_video.mp4 file in the videos/ directory")
    sys.exit(1)

print("="*70)
print("VIDEO DOCUMENTATION SYSTEM - DEMO")
print("="*70)

"""Deprecated root demo script.

The interactive demo was moved to `scripts/demo.py` and the packaged demo
helper is available at `vid2doc.demo`.
"""
raise ImportError("demo script moved: run scripts/demo.py or use 'vid2doc.demo'")
print("\nThis may take a few minutes depending on video length...")
