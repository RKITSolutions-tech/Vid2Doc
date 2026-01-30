import os
import sys
import tempfile
import shutil
import pytest

# Ensure workspace root is on sys.path so local modules can be imported
sys.path.insert(0, os.path.abspath(os.getcwd()))

# We'll import the module under test
import video_audio_extraction as vae


def test_wav_path_and_extraction_called(monkeypatch, tmp_path):
    # Create a fake video file
    video_file = tmp_path / "uploads" / "test_video.mp4"
    video_file.parent.mkdir(parents=True, exist_ok=True)
    video_file.write_bytes(b"FAKEMP4")

    # Track calls to extract_audio_segment
    calls = []

    def fake_extract_audio_segment(video_path, start_frame, end_frame, fps, output_audio_path, max_attempts=None):
        # Assert we received the real video path
        assert os.path.exists(video_path)
        calls.append((video_path, start_frame, end_frame, fps, output_audio_path, max_attempts))
        # Create the wav file to simulate success
        with open(output_audio_path, 'wb') as f:
            f.write(b"RIFF....WAVE")

    monkeypatch.setattr(vae, 'extract_audio_segment', fake_extract_audio_segment)

    # Monkeypatch whisper model loader to avoid loading real models
    class FakeModel:
        def transcribe(self, wav_path):
            assert os.path.exists(wav_path)
            return {"text": "recognized speech"}

    monkeypatch.setattr(vae, '_load_whisper_model', lambda m: FakeModel())

    # Call get_slide_text with a full path and a video_id to force per-video wav folder
    video_path = str(video_file)
    text = vae.get_slide_text(video_path, 1, 501, fps=25, model_size='tiny', audio_retry_attempts=1, video_id=12345)

    assert text == "recognized speech"
    assert len(calls) == 1

    called_output = calls[0][4]
    # Expect the wav to be stored under wav/12345/
    assert os.path.normpath(called_output).startswith(os.path.normpath(os.path.join('wav', '12345')))

    # Cleanup created wav folder
    if os.path.exists('wav'):
        shutil.rmtree('wav')