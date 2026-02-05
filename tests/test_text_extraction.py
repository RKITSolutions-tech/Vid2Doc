import io
import os
import time

from vid2doc.app import app


def test_text_samples_are_persisted():
    client = app.test_client()
    path = 'videos/small_demo_video.mp4'
    assert os.path.exists(path), 'Test video missing'

    with open(path, 'rb') as f:
        data = {'video': (io.BytesIO(f.read()), os.path.basename(path))}
        resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    payload = resp.get_json()
    file_id = payload['file_id']

    # Start processing which will emit text_sample events
    resp2 = client.post('/api/process', json={'file_id': file_id, 'settings': {'test_slides': 3}})
    assert resp2.status_code == 200
    job_id = resp2.get_json()['job_id']

    # Wait for completion
    deadline = time.time() + 5
    final = None
    while time.time() < deadline:
        r = client.get(f'/api/progress/{job_id}')
        j = r.get_json()['job']
        if j['status'] in ('completed', 'error', 'cancelled'):
            final = j
            break
        time.sleep(0.05)

    assert final and final['status'] == 'completed'

    # Ensure job recorded sample counts
    assert final.get('sample_count', 0) >= 1
    assert final.get('samples_persisted', 0) >= 1

    # Ensure extracts panel has entries and that DB contains persisted text for slides
    from vid2doc.database import get_video_slides, get_text_extract_by_slide
    slides = get_video_slides(final['video_id'])
    assert len(slides) >= 1

    persisted = 0
    for s in slides:
        txt = get_text_extract_by_slide(s['id'])
        if txt and (txt['original_text'] or txt['suggested_text'] or txt['final_text']):
            persisted += 1

    assert persisted >= 1, 'No text extracts found for processed slides'