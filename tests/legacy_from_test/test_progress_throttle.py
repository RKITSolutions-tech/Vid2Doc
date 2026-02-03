import time
import threading
from app import _start_processing_job, app as flask_app, processing_jobs


def fake_process_video(settings=None, progress_callback=None, should_cancel=None):
    # emit a 'started' event
    if progress_callback:
        progress_callback({'type': 'started', 'total_frames': 100, 'fps': 25})
    # emit many rapid status events
    for i in range(0, 101, 5):
        if progress_callback:
            progress_callback({'type': 'status', 'message': 'Processing update', 'progress': float(i), 'frames': i, 'total_frames': 100})
        time.sleep(0.05)
    # emit complete
    if progress_callback:
        progress_callback({'type': 'complete', 'video_id': 1})


def test_progress_throttle_and_gpu_log_absent(monkeypatch):
    # Monkeypatch the VideoProcessor.process_video path to use fake_process_video
    import video_processor

    class DummyProcessor:
        def __init__(self, path, out):
            pass

        def process_video(self, settings, progress_callback, should_cancel):
            fake_process_video(settings=settings, progress_callback=progress_callback, should_cancel=should_cancel)

    monkeypatch.setattr('app.VideoProcessor', DummyProcessor)

    job_id = _start_processing_job('uploads/test_small.mp4', {'extraction_method': 'frame_analysis_gpu'})
    # Poll until complete
    with flask_app.test_client() as client:
        final = None
        for _ in range(50):
            resp = client.get(f'/api/progress/{job_id}')
            assert resp.status_code == 200
            data = resp.get_json()
            job = data['job']
            if job['status'] == 'completed':
                final = job
                break
            time.sleep(0.1)

        assert final is not None
        # percent should be 100.0 at the end
        assert final['percent_complete'] == 100.0
        # ensure no GPU diagnostics short log string exists in logs
        msgs = [m['message'] for m in final.get('logs', [])]
        assert not any(m.startswith('GPU:') for m in msgs), 'GPU short summary found in logs'
        # diagnostics dict should still be present (may be empty)
        assert 'gpu_diagnostics' in final
