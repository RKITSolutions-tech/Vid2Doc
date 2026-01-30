"""Simple runtime check that the Flask app reports health via /api/health.

Usage:
  .venv/bin/python scripts/check_api_health.py
"""
import sys

from app import app

with app.test_client() as client:
    resp = client.get('/api/health')
    if resp.status_code != 200:
        print(f"ERROR: /api/health returned status {resp.status_code}")
        sys.exit(2)
    data = resp.get_json() or {}
    print("/api/health ->", data)
    # Basic validation
    if not data.get('ffprobe') and not data.get('packages', {}).get('sqlalchemy'):
        print("ERROR: critical dependencies missing according to /api/health")
        sys.exit(3)

print("Health endpoint OK")
sys.exit(0)
