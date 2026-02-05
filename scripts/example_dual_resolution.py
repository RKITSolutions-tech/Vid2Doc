#!/usr/bin/env python
"""Example script demonstrating dual-resolution video processing (moved to scripts/)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../')
from vid2doc.video_processor import VideoProcessor

def process_video_fast_quality(video_path, output_dir='output'):
    print("Dual-Resolution Video Processing Example")
    processor = VideoProcessor(video_path, output_dir)
    return processor.process_video()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/example_dual_resolution.py <video_path>")
        sys.exit(1)
    process_video_fast_quality(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'output')
