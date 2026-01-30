# Copyright (c) 2025 Ryan Kenning
# Licensed under the MIT License - see LICENSE file for details

try:
    import cv2
    import numpy as np
    from skimage.metrics import structural_similarity as ssim
    import ffmpeg
except Exception:
    # Make imports optional at import time so the Flask app can start without
    # heavy imaging dependencies installed. Functions that require these
    # libraries will raise a clear ImportError when invoked.
    cv2 = None
    np = None
    ssim = None
    ffmpeg = None

import os
from typing import Optional


def get_video_properties(video_path: str) -> dict:
    """Collect core metadata for the supplied video path.

    Raises ImportError if OpenCV (`cv2`) is not available.
    """
    if cv2 is None:
        # Fallback: try to use ffprobe (part of FFmpeg) to gather video metadata so
        # the application can run without OpenCV when ffprobe is available on the system.
        try:
            import json as _json
            import subprocess as _subprocess

            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,nb_frames,avg_frame_rate",
                "-show_entries", "format=duration,bit_rate",
                "-print_format", "json",
                video_path,
            ]
            proc = _subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = _json.loads(proc.stdout)
            stream = info.get("streams", [{}])[0]
            fmt = info.get("format", {})
            file_size = os.path.getsize(video_path)

            rfr = stream.get("r_frame_rate") or stream.get("avg_frame_rate") or "0/1"
            try:
                num, den = rfr.split("/")
                fps = float(num) / float(den) if float(den) != 0 else 0.0
            except Exception:
                fps = 0.0

            frame_count = None
            nb_frames = stream.get("nb_frames")
            if nb_frames:
                try:
                    frame_count = int(nb_frames)
                except Exception:
                    frame_count = None

            if frame_count is None and fmt.get("duration") and fps:
                try:
                    frame_count = int(float(fmt["duration"]) * fps)
                except Exception:
                    frame_count = 0

            if frame_count is None:
                frame_count = 0

            duration = float(fmt.get("duration") or (frame_count / fps if fps else 0)) if (fmt.get("duration") or fps) else 0
            width = float(stream.get("width") or 0)
            height = float(stream.get("height") or 0)
            bit_rate = float(fmt.get("bit_rate")) if fmt.get("bit_rate") else ((file_size * 8) / duration if duration else 0)

            return {
                "file_size": file_size,
                "fps": fps,
                "frame_count": frame_count,
                "duration": duration,
                "width": width,
                "height": height,
                "bit_rate": bit_rate,
                "aspect_ratio": (width / height) if height else 0,
                "total_frames": frame_count,
            }
        except Exception:
            raise ImportError("cv2 (OpenCV) is required for get_video_properties; install with 'pip install opencv-python-headless' or ensure 'ffprobe' (FFmpeg) is installed for a fallback option.")

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
    if cv2 is None or ssim is None:
        raise ImportError("cv2 and scikit-image are required for frame difference calculations")
    grayA = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    score, _ = ssim(grayA, grayB, full=True)
    return score


def compare_histograms(frame1, frame2, bins: int = 256) -> float:
    """Compare two frames using histogram correlation with configurable bins."""
    if cv2 is None:
        raise ImportError("cv2 (OpenCV) is required for histogram comparison")
    hist_range = [0, 256]
    hist1 = cv2.calcHist([frame1], [0], None, [bins], hist_range)
    hist2 = cv2.calcHist([frame2], [0], None, [bins], hist_range)
    cv2.normalize(hist1, hist1)
    cv2.normalize(hist2, hist2)
    return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)


def resize_frame(frame, scale_percent: Optional[float]) -> "np.ndarray":
    """Downscale a frame by the requested percentage for faster processing."""
    if cv2 is None or np is None:
        raise ImportError("cv2 and numpy are required for frame resizing")
    if not scale_percent or scale_percent <= 0 or scale_percent == 100:
        return frame
    scale = scale_percent / 100.0
    return cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def extract_video_and_audio(full_video_path, frame_gap):
    """Placeholder function for video and audio extraction."""
    pass