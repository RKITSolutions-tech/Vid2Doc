import io
import os
import time

from vid2doc.app import app
import vid2doc.video_audio_extraction as vae


def test_empty_transcription_is_logged(monkeypatch):
    client = app.test_client()
    path = 'videos/small_demo_video.mp4'
    assert os.path.exists(path)

    # Monkeypatch the whisper loader to return an object whose transcribe returns empty text
    class EmptyModel:
        def transcribe(self, path):
            return {"text": ""}

    monkeypatch.setattr(vae, '_load_whisper_model', lambda model_size: EmptyModel())

    with open(path, 'rb') as f:
        data = {'video': (io.BytesIO(f.read()), os.path.basename(path))}
        resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    file_id = resp.get_json()['file_id']

    # Start processing and request the worker to call the real get_slide_text function
    resp2 = client.post('/api/process', json={'file_id': file_id, 'settings': {'test_slides': 2, 'use_get_slide_text_for_samples': True}})
    assert resp2.status_code == 200
    job_id = resp2.get_json()['job_id']

    # Poll until done
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
    # Ensure empty samples were recorded and that no audio_failure was created
    assert final.get('empty_samples', 0) >= 1

    # Verify there are no entries in audio_failures for this job's video id
    from vid2doc.database import get_audio_failures
    fails = get_audio_failures(video_id=final['video_id'])
    # Should be 0 because empty transcription is not an error
    assert len(fails) == 0
