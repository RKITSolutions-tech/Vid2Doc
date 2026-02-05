"""End-to-end capture test using the small demo video."""
from __future__ import annotations

import os
import sys
from pathlib import Path
import pytest
from typing import List, Tuple
from unittest.mock import patch

import cv2

CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import vid2doc.database as database
from vid2doc.database import get_db_connection, get_video_slides, init_db
from vid2doc.video_processor import VideoProcessor


def test_small_demo_video_audio_capture(tmp_path):
    """Process a real video, capture slide text, and verify DB persistence."""
    source_video_path = Path("videos") / "Small Demo Video.mp4"
    if not source_video_path.exists():
        pytest.skip(f"Expected demo video file is missing at {source_video_path}")

    # Create a trimmed copy of the demo video to keep the test fast
    trimmed_video_path = tmp_path / "trimmed_small_demo.mp4"
    source_cap = cv2.VideoCapture(str(source_video_path))
    assert source_cap.isOpened(), "Failed to open the source demo video."

    fps = source_cap.get(cv2.CAP_PROP_FPS) or 30
    width = int(source_cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    height = int(source_cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 360)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(trimmed_video_path), fourcc, fps, (width, height))

    frame_limit = int(fps * 2)  # ~2 seconds of video to keep processing quick
    frames_written = 0
    while frames_written < frame_limit:
        ret, frame = source_cap.read()
        if not ret:
            break
        writer.write(frame)
        frames_written += 1

    source_cap.release()
    writer.release()

    assert trimmed_video_path.exists(), "Trimmed demo video was not created."

    # Use an isolated database for the test
    original_db_path = database.DATABASE_PATH
    test_db_path = tmp_path / "capture_test.db"
    database.DATABASE_PATH = str(test_db_path)
    init_db()

    output_dir = tmp_path / "output"
    os.makedirs(output_dir, exist_ok=True)

    captured_segments: List[Tuple[int, int]] = []

    def fake_get_slide_text(filename, start_frame, end_frame, fps, model_size="base"):
        captured_segments.append((start_frame, end_frame))
        # Simulate transcription output that references the frame window
        return f"Transcript frames {start_frame}-{end_frame} at {fps:.1f}fps"

    def fake_summrise_text(text, min_length=30, max_length=150, model_name="mock-model"):
        # Return a list mimicking the transformers summarize response
        return [{"summary_text": text.upper()}]

    progress_events = []

    def progress_callback(event):
        # Append and print a concise summary so the test runner shows progress
        progress_events.append(event)
        evt_type = event.get('type')
        if evt_type in {'progress', 'preview', 'slide', 'status', 'text_sample'}:
            print(f"[progress_callback] type={evt_type} frame={event.get('frame')} msg={event.get('message', '')}")

    settings = {
        "threshold_ssim": 0.85,
        "threshold_hist": 0.85,
        "frame_gap": 5,
        "transition_limit": 2,
        "preview_interval": 120,
    "force_slide_interval": 30,
        "progress_interval": 30,
        "min_slide_audio_seconds": 0.0,
    }

    try:
        print("[test] Starting processing (this may take a short while)...")
        with patch("vid2doc.video_audio_extraction.get_slide_text", side_effect=fake_get_slide_text), \
             patch("vid2doc.video_audio_extraction.summrise_text", side_effect=fake_summrise_text):
            processor = VideoProcessor(str(trimmed_video_path), output_dir=str(output_dir))
            video_id = processor.process_video(settings=settings, progress_callback=progress_callback)

        print(f"[test] Processing finished. video_id={video_id}")
        print(f"[test] Captured segments: {captured_segments}")
        print(f"[test] Progress events count: {len(progress_events)}")

        assert video_id is not None, "Processing did not return a video ID"
        assert captured_segments, "Audio transcription was never invoked"

        slides = get_video_slides(video_id)
        assert len(slides) >= 2, "Expected at least two slides to be captured"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT original_text, suggested_text FROM text_extracts WHERE slide_id IN ({})".format(
                ",".join("?" for _ in slides)
            ),
            [slide["id"] for slide in slides],
        )
        extracts = cursor.fetchall()
        conn.close()

        assert len(extracts) >= 2, "Text extracts were not stored for captured slides"
        non_empty_extracts = [extract for extract in extracts if extract["original_text"]]
        assert non_empty_extracts, "No captured slide contained extracted text"
        assert len(non_empty_extracts) == len(captured_segments), "Mismatch between audio captures and stored text"
        for extract in non_empty_extracts[:2]:
            assert extract["suggested_text"], "Suggested text should not be empty"
            # Suggested text should mirror or summarize the original transcript
            assert extract["suggested_text"].strip(), "Suggested text should contain content"

        processed_flag = database.get_video_by_id(video_id)["processed"]
        assert processed_flag == 1, "Video was not marked as processed"

        # Ensure status events were emitted during text capture
        status_events = [evt for evt in progress_events if evt.get("type") == "status"]
        assert status_events, "Expected status events describing text capture"
    finally:
        database.DATABASE_PATH = original_db_path
        if test_db_path.exists():
            os.remove(test_db_path)