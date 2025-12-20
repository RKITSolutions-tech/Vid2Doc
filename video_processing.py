# Copyright (c) 2025 Ryan Kenning
# Licensed under the MIT License - see LICENSE file for details

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import ffmpeg
import os
from typing import Optional


def get_video_properties(video_path: str) -> dict:
    """Collect core metadata for the supplied video path."""
    properties = {}
    cap = cv2.VideoCapture(video_path)
    properties["file_size"] = os.path.getsize(video_path)
    properties["fps"] = cap.get(cv2.CAP_PROP_FPS)
    properties["frame_count"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # Guard against division by zero for malformed videos
    properties["duration"] = properties["frame_count"] / properties["fps"] if properties["fps"] else 0
    properties["width"] = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    properties["height"] = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    if properties["duration"]:
        properties["bit_rate"] = (properties["file_size"] * 8) / properties["duration"]
    else:
        properties["bit_rate"] = 0
    properties["aspect_ratio"] = (
        (properties["width"] / properties["height"]) if properties["height"] else 0
    )
    properties["total_frames"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return properties


def resize_video(
    input_file: str,
    output_file: str,
    original_fps: float,
    new_fps: float,
    scale_factor: float = 0.75,
    overwrite: bool = True,
):
    """Resize the video using ffmpeg-python wrapper with configurable scale."""

    if not overwrite and os.path.exists(output_file):
        return

    (
        ffmpeg
        .input(input_file)
        .output(output_file, vf=f'scale=iw*{scale_factor}:ih*{scale_factor},fps={new_fps}')
        .run(overwrite_output=overwrite)
    )


def frame_difference(frame1, frame2) -> float:
    """Compare two frames using structural similarity index (SSIM)."""
    grayA = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(grayA, grayB, full=True)
    return score


def compare_histograms(frame1, frame2, bins: int = 256) -> float:
    """Compare two frames using histogram correlation with configurable bins."""
    hist_range = [0, 256]
    hist1 = cv2.calcHist([frame1], [0], None, [bins], hist_range)
    hist2 = cv2.calcHist([frame2], [0], None, [bins], hist_range)
    cv2.normalize(hist1, hist1)
    cv2.normalize(hist2, hist2)
    return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)


def resize_frame(frame, scale_percent: Optional[float]) -> np.ndarray:
    """Downscale a frame by the requested percentage for faster processing."""
    if not scale_percent or scale_percent <= 0 or scale_percent == 100:
        return frame
    scale = scale_percent / 100.0
    return cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def extract_video_and_audio(full_video_path, frame_gap):
    """Placeholder function for video and audio extraction."""
    pass