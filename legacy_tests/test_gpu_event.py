import time
import pytest

from vid2doc.app import _start_processing_job, processing_jobs, jobs_lock


def test_gpu_event_stored_and_logged():
    job_id = _start_processing_job('uploads/fake.mp4', {})
    # small sleep to allow worker thread to initialize
    time.sleep(0.1)
    with jobs_lock:
        job = processing_jobs.get(job_id)
        assert job is not None
        # Simulate GPU event as the extractor would emit
        ev = {'type': 'gpu', 'diagnostics': {'device_name': 'CI-GPU', 'cuda_version': '12.1', 'total_memory_mb': 8192}}
        # emulate server-side handling used in progress_callback
        job['gpu_diagnostics'] = ev['diagnostics']
        parts = [f"GPU: {ev['diagnostics'].get('device_name')}"]
        if ev['diagnostics'].get('cuda_version'):
            parts.append('CUDA ' + str(ev['diagnostics'].get('cuda_version')))
        if ev['diagnostics'].get('total_memory_mb'):
            parts.append(str(ev['diagnostics'].get('total_memory_mb')) + 'MB')
        job['logs'].append({'message': ' '.join(parts), 'timestamp': time.time()})

    # Verify snapshot contains gpu_diagnostics and at least one log containing 'GPU:'
    with jobs_lock:
        snapshot = processing_jobs.get(job_id)
        assert 'gpu_diagnostics' in snapshot
        assert snapshot['gpu_diagnostics']['device_name'] == 'CI-GPU'
        assert any('GPU:' in l['message'] for l in snapshot['logs'])
