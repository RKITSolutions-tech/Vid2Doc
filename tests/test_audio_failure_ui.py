import io
import os
import time

from app import app
from database import add_audio_failure


def test_audio_failure_detail_shows_structured_fields(tmp_path):
    # Use test DB
    db = str(tmp_path / 'test_af.db')
    # Point DB to a temp file and init
    import database as dbmod
    dbmod.DATABASE_PATH = db
    dbmod.init_db()

    # Create a fake audio failure
    vid = 42
    fid = add_audio_failure(vid, None, 10, 20, 1, 'Test error', tool='whisper', stderr='traceback...', details='more')

    client = app.test_client()
    r = client.get(f'/audio-failures/{fid}')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'whisper' in html
    assert 'traceback' in html
    assert 'more' in html
