import io
import os
import time

from app import app


def test_job_logs_endpoint_includes_job_logs_and_host(tmp_path):
    client = app.test_client()
    path = 'videos/small_demo_video.mp4'
    assert os.path.exists(path)

    # Create a small host log file and configure app to use it
    host_log = tmp_path / 'app.log'
    host_log.write_text('\n'.join([f'line {i}' for i in range(1, 21)]))
    app.config['LOG_FILE'] = str(host_log)

    with open(path, 'rb') as f:
        data = {'video': (io.BytesIO(f.read()), os.path.basename(path))}
        resp = client.post('/api/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    file_id = resp.get_json()['file_id']

    resp2 = client.post('/api/process', json={'file_id': file_id, 'settings': {'test_slides': 2}})
    assert resp2.status_code == 200
    job_id = resp2.get_json()['job_id']

    # Wait to complete
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

    # Call the logs endpoint with host logs included
    r = client.get(f'/api/job/{job_id}/logs?n=5&host=1')
    assert r.status_code == 200
    payload = r.get_json()
    assert payload['success'] is True
    assert 'logs' in payload
    assert isinstance(payload['logs'], list)
    assert 'host_log_lines' in payload
    assert isinstance(payload['host_log_lines'], list)
    assert len(payload['host_log_lines']) <= 5
