import os
import time
from datetime import datetime, timedelta

import vid2doc.database as database


def test_purge_audio_failures_older_than(tmp_path):
    # Use a fresh DB
    db_file = str(tmp_path / 'test_purge.db')
    database.DATABASE_PATH = db_file
    if os.path.exists(db_file):
        os.remove(db_file)
    database.init_db()

    conn = database.get_db_connection()
    cur = conn.cursor()
    # Insert one old failure and one recent failure
    from datetime import timezone
    old_time = (datetime.now(timezone.utc) - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')
    cur.execute('INSERT INTO audio_failures (video_id, start_frame, end_frame, attempts, error_message, created_at) VALUES (?, ?, ?, ?, ?, ?)', (1, 0, 10, 1, 'old', old_time))
    cur.execute('INSERT INTO audio_failures (video_id, start_frame, end_frame, attempts, error_message) VALUES (?, ?, ?, ?, ?)', (1, 20, 30, 1, 'recent'))
    conn.commit()
    conn.close()

    deleted = database.purge_audio_failures_older_than(30)
    assert deleted >= 1

    remaining = database.get_audio_failures(limit=10, video_id=1)
    assert len([r for r in remaining if r['error_message'] == 'old']) == 0
    assert len([r for r in remaining if r['error_message'] == 'recent']) == 1
