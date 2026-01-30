"""Tests for min_slide_audio_seconds behavior (default and katna flows)."""
import os
import sys
from pathlib import Path
import tempfile
import cv2
import numpy as np
import pytest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import init_db, DATABASE_PATH, get_db_connection, get_video_slides
from video_processor import VideoProcessor


def create_color_change_video(path, duration_sec=1, fps=10, width=320, height=240):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    total_frames = int(duration_sec * fps)
    for i in range(total_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        if i < total_frames // 2:
            frame[:, :, 2] = 200
        else:
            frame[:, :, 0] = 200
        writer.write(frame)
    writer.release()


def test_default_deferral(tmp_path):
    # Setup isolated DB
    orig_db = os.environ.get('VIDEO_DOC_DB', '')
    test_db = tmp_path / 'test.db'
    # Ensure database module points to file-based DB used by functions
    import database
    database.DATABASE_PATH = str(test_db)
    init_db()

    video_file = tmp_path / 'demo.mp4'
    create_color_change_video(video_file, duration_sec=1, fps=10)

    out_dir = tmp_path / 'out'
    out_dir.mkdir()

    # Run with a min threshold longer than video duration to force deferral
    settings = {
        'min_slide_audio_seconds': 2.0,
        'preview_interval': 500,
    }

    processor = VideoProcessor(str(video_file), output_dir=str(out_dir))
    vid_id = processor.process_video(settings=settings)
    assert vid_id is not None
    slides = get_video_slides(vid_id)
    # With deferral, we expect only the initial slide (no short segment captures)
    assert len(slides) <= 1

    # Now run with zero threshold to allow normal captures
    database.DATABASE_PATH = str(test_db)
    # create another processor output dir
    out_dir2 = tmp_path / 'out2'
    out_dir2.mkdir()
    processor2 = VideoProcessor(str(video_file), output_dir=str(out_dir2))
    vid_id2 = processor2.process_video(settings={'min_slide_audio_seconds': 0.0})
    assert vid_id2 is not None
    slides2 = get_video_slides(vid_id2)
    assert len(slides2) >= 1


def test_katna_deferral(tmp_path):
    # Mock katna extraction to return two keyframes spaced by 1s
    import database
    database.DATABASE_PATH = str(tmp_path / 'katna.db')
    init_db()

    # Create a fake frame image
    img1 = np.zeros((240, 320, 3), dtype=np.uint8)
    img1[:, :, 2] = 200
    img2 = np.zeros((240, 320, 3), dtype=np.uint8)
    img2[:, :, 0] = 200

    fake_keyframes = [
        (1, 0.0, img1),
        (30, 1.0, img2),
    ]

    video_file = tmp_path / 'dummy.mp4'
    # create a tiny file so VideoProcessor won't fail reading properties
    create_color_change_video(video_file, duration_sec=1, fps=30)

    out_dir = tmp_path / 'out'
    out_dir.mkdir()

    processor = VideoProcessor(str(video_file), output_dir=str(out_dir))

    with patch('katna_processor.extract_keyframes_katna', return_value=fake_keyframes):
        vid_id = processor._process_video_katna(
            katna_max_keyframes=0,
            katna_scale_percent=50,
            progress_callback=None,
            should_cancel=None,
            whisper_model='base',
            audio_retry_attempts=1,
            audio_skip_on_failure=True,
            summary_min=30,
            summary_max=150,
            summary_model='sshleifer/distilbart-cnn-12-6',
            target_resolution_percent=100,
            min_slide_audio_seconds=2.0,
        )
    assert vid_id is not None
    slides = get_video_slides(vid_id)
    # With min 2s but keyframes only 1s apart, expect the second keyframe to be deferred -> <=1 slide
    assert len(slides) <= 1
