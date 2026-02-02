import io
import os
import time
import pytest

from app import app


def test_upload_and_process():
    client = app.test_client()
    path = 'videos/small_demo_video.mp4'
    assert os.path.exists(path), 'Test video missing'

    with open(path, 'rb') as f:
        data = {'video': (io.BytesIO(f.read()), os.path.basename(path))}
        resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload['success'] is True
    file_id = payload['file_id']

    # Start processing with an override to create 4 test slides (pass under 'settings')
    resp2 = client.post('/api/process', json={'file_id': file_id, 'settings': {'test_slides': 4}})
    assert resp2.status_code == 200
    body = resp2.get_json()
    assert body['success'] is True
    job_id = body['job_id']

    # Poll until completion
    deadline = time.time() + 5
    final = None
    while time.time() < deadline:
        r = client.get(f'/api/progress/{job_id}')
        assert r.status_code == 200
        j = r.get_json()['job']
        if j['status'] in ('completed', 'error', 'cancelled'):
            final = j
            break
        time.sleep(0.1)

    assert final is not None, 'Job did not finish in time'
    assert final['status'] == 'completed'
    assert final['total_frames'] == 4

    # Validate DB slides were created
    from database import get_video_slides
    slides = get_video_slides(final['video_id'])
    assert len(slides) == 4
