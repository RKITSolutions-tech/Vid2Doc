from video_audio_extraction import get_slide_text
import database


def test_whisper_missing_records_audio_failure(tmp_path):
    # Use test DB
    db_file = str(tmp_path / 'test_whisper.db')
    database.DATABASE_PATH = db_file
    database.init_db()

    # Monkeypatch _load_whisper_model to raise ImportError
    import video_audio_extraction as vae
    orig = vae._load_whisper_model
    vae._load_whisper_model = lambda x: (_ for _ in ()).throw(ImportError('whisper missing for test'))
    try:
        text = get_slide_text('videos/small_demo_video.mp4', 0, 90, fps=30, model_size='tiny', audio_retry_attempts=1, video_id=1234)
        assert text == ''
        fails = database.get_audio_failures(video_id=1234)
        assert len(fails) >= 1
        assert any(f['tool'] == 'whisper' for f in fails)
    finally:
        vae._load_whisper_model = orig
