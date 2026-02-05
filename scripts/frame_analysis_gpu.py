#!/usr/bin/env python
"""Script wrapper for GPU frame analysis extractor (moved to scripts/)."""
from vid2doc.frame_analysis_gpu import extract_frames_gpu
import sys

def main():
    if len(sys.argv) < 3:
        print("Usage: scripts/frame_analysis_gpu.py <input_path> <output_dir>")
        return
    extract_frames_gpu(sys.argv[1], sys.argv[2])

if __name__ == '__main__':
    main()
