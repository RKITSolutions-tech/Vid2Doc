import os
import sqlite3
import time

from video_audio_extraction import get_slide_text, _load_whisper_model
import video_audio_extraction as vae
import database


def test_transcription_failure_records_audio_failure(tmp_path, monkeypatch):
    # Use a temporary DB for the test
    db_path = str(tmp_path / 'test_audio_fail.db')
    database.DATABASE_PATH = db_path
    if os.path.exists(db_path):
        os.remove(db_path)
    database.init_db()

    # Make a tiny test video path (existing sample in repo)
    video_path = 'videos/small_demo_video.mp4'
    assert os.path.exists(video_path)

    # Monkeypatch the whisper loader to return an object whose transcribe raises
    class BadModel:
        def transcribe(self, path):
            raise RuntimeError('Simulated transcription failure')

    monkeypatch.setattr(vae, '_load_whisper_model', lambda model_size: BadModel())

    # Call get_slide_text; it should return empty string and record an audio_failure
    text = get_slide_text(video_path, 0, 30, fps=30, model_size='tiny', audio_retry_attempts=1, video_id=999)
    assert text == ''

    failures = database.get_audio_failures(video_id=999)
    assert len(failures) >= 1
    found = False
    for f in failures:
        # The new structured fields should include tool='whisper' and stderr containing the error
        if (f['tool'] == 'whisper') and ('Simulated transcription failure' in (f['stderr'] or '')):
            found = True
    assert found, 'Expected transcription failure to be recorded in audio_failures with tool=whisper and stderr'