"""Simple runtime check that the Flask app reports health via /api/health.

Usage:
  .venv/bin/python scripts/check_api_health.py
"""
import sys
import os

# Ensure repository root is on sys.path so 'app' can be imported when this
# script is executed directly.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

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
