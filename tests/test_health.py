import json
from app import app


def test_api_health():
    client = app.test_client()
    resp = client.get('/api/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'ffprobe' in data
    assert 'packages' in data
    assert 'sqlalchemy' in data['packages']
