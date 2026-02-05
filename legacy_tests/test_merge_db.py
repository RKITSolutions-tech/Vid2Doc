import os
import pytest
import tempfile

import database


def init_temp_db(tmp_path):
    db_file = tmp_path / "test_video_doc.db"
    # Use a fresh database path for the database module
    database.DATABASE_PATH = str(db_file)
    # Reinitialize DB schema
    database.init_db()
    return database


def test_merge_append(tmp_path):
    db = init_temp_db(tmp_path)

    # Create video and slides
    vid = db.add_video('test.mp4', '/videos/test.mp4', duration=60.0, fps=30.0)
    s1 = db.add_slide(vid, 10, 0.333, 'output/img_s1.jpg')
    s2 = db.add_slide(vid, 20, 0.666, 'output/img_s2.jpg')

    # Set final text for both slides
    db.set_final_text_for_slide(s1, 'SOURCE TEXT')
    db.set_final_text_for_slide(s2, 'TARGET TEXT')

    # Merge s1 into s2 (append)
    res = db.merge_from_slide_into_target(s1, s2, append=True)
    assert res is not None
    assert res['target_slide_id'] == s2
    assert res['deleted_source_id'] == s1
    assert 'SOURCE TEXT' in res['merged_text']
    assert 'TARGET TEXT' in res['merged_text']
    # Expect target's final_text to be TARGET \n SOURCE
    te = db.get_text_extract_by_slide(s2)
    assert te is not None
    assert te['final_text'] == 'TARGET TEXT\nSOURCE TEXT'

    # Source slide should be deleted
    assert db.get_slide_by_id(s1) is None
    assert db.get_text_extract_by_slide(s1) is None


def test_merge_prepend(tmp_path):
    db = init_temp_db(tmp_path)

    vid = db.add_video('test2.mp4', '/videos/test2.mp4', duration=30.0, fps=24.0)
    s1 = db.add_slide(vid, 1, 0.1, 'output/img_a.jpg')
    s2 = db.add_slide(vid, 2, 0.2, 'output/img_b.jpg')

    db.set_final_text_for_slide(s1, 'FIRST')
    db.set_final_text_for_slide(s2, 'SECOND')

    res = db.merge_from_slide_into_target(s1, s2, append=False)
    assert res is not None
    assert res['target_slide_id'] == s2
    assert res['deleted_source_id'] == s1
    assert res['merged_text'].startswith('FIRST')

    te = db.get_text_extract_by_slide(s2)
    assert te is not None
    assert te['final_text'] == 'FIRST\nSECOND'

    assert db.get_slide_by_id(s1) is None
    assert db.get_text_extract_by_slide(s1) is None
