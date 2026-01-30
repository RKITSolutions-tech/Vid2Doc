import os
import tempfile
import subprocess
import pytest


@pytest.fixture
def synthetic_video_path(tmp_path):
    """Create a small synthetic MP4 video and return its path.

    Attempts to use OpenCV to write a short MP4. If OpenCV isn't available, tries to use ffmpeg if present on PATH.
    If neither is available, skips the tests that require a video.
    """
    out = tmp_path / "synthetic.mp4"

    # Try OpenCV approach
    try:
        import cv2
        import numpy as np

        fps = 10
        width, height = 320, 240
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(out), fourcc, fps, (width, height))
        for i in range(20):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            color = (int(100 + i * 7) % 255, 50, 150)
            frame[:] = color
            cv2.putText(frame, f"Frame {i}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            writer.write(frame)
        writer.release()
        return str(out)
    except Exception:
        # Fallback to ffmpeg if available
        if subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0:
            # Use ffmpeg to generate a test pattern
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "testsrc=duration=2:size=320x240:rate=10",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                str(out)
            ]
            p = subprocess.run(cmd, capture_output=True)
            if p.returncode == 0 and out.exists():
                return str(out)

    pytest.skip("No suitable tool (opencv or ffmpeg) available to generate synthetic video")
