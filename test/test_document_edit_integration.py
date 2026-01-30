import json
import re
from app import app
import database


def create_test_video(conn=None):
    # Use database helpers to create a video + slide + text extract
    # Ensure DB schema exists (idempotent)
    database.init_db()
    vid = database.add_video('test_video.mp4', '/tmp/test_video.mp4', duration=10.0, fps=30.0)
    sid = database.add_slide(vid, frame_number=1, timestamp=0.0, image_path='output/preview_test.jpg')
    tid = database.add_text_extract(sid, 'original sample', 'suggested sample')
    # Mark processed so it appears in lists
    database.mark_video_processed(vid)
    return vid, sid, tid


def delete_test_video(video_id):
    # Remove created rows directly for cleanup
    conn = database.get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM text_extracts WHERE slide_id IN (SELECT id FROM slides WHERE video_id = ?)', (video_id,))
    cur.execute('DELETE FROM slides WHERE video_id = ?', (video_id,))
    cur.execute('DELETE FROM sections WHERE video_id = ?', (video_id,))
    cur.execute('DELETE FROM videos WHERE id = ?', (video_id,))
    conn.commit()
    conn.close()


def test_document_api_and_ui_flow():
    # Arrange: create test video/slide
    vid, sid, tid = create_test_video()

    try:
        client = app.test_client()

        # 1) GET /api/videos should include our video
        rv = client.get('/api/videos')
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['success'] is True
        ids = [v['id'] for v in data['videos']]
        assert vid in ids

        # 2) GET document metadata
        rv = client.get(f'/api/video/{vid}/document')
        assert rv.status_code == 200
        meta = rv.get_json()
        assert meta['success'] is True

        # 3) GET slides list
        rv = client.get(f'/api/video/{vid}/slides')
        assert rv.status_code == 200
        slides_payload = rv.get_json()
        assert slides_payload['success'] is True
        slide_ids = [s['id'] for s in slides_payload['slides']]
        assert sid in slide_ids

        # 4) POST update_document
        body = {'title': 'Integration Test Title', 'summary': 'Integration summary'}
        rv = client.post(f'/api/update_document/{vid}', data=json.dumps(body), content_type='application/json')
        assert rv.status_code == 200
        upd = rv.get_json()
        assert upd['success'] is True

        # 5) Verify document persisted via GET document
        rv = client.get(f'/api/video/{vid}/document')
        assert rv.status_code == 200
        meta2 = rv.get_json()
        assert meta2['document_title'] == 'Integration Test Title'
        assert meta2['document_summary'] == 'Integration summary'

        # 6) UI smoke: GET edit page and check it contains the video filename and a save button
        rv = client.get(f'/video/{vid}')
        assert rv.status_code == 200
        text = rv.get_data(as_text=True)
        assert 'Document Editing' in text
        assert re.search(r'Select video:', text)
        assert 'Save Document' in text

    finally:
        # Cleanup created rows
        delete_test_video(vid)
