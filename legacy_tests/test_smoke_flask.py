#!/usr/bin/env python
"""Smoke test for Flask application - ensures app can start and basic routes work"""
import os
import sys
from pathlib import Path

# Ensure project root is importable when running as a script
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main():
    print("="*70)
    print("FLASK APP SMOKE TEST")
    print("="*70)

    # Test 1: Import Flask app
    print("\n1. Testing Flask app import...")
    try:
        from vid2doc.app import app
        print("✓ Flask app imported successfully")
    except Exception as e:
        print(f"✗ Failed to import Flask app: {e}")
        raise

    # Test 2: Check app configuration
    print("\n2. Testing app configuration...")
    assert app.config['UPLOAD_FOLDER'] == 'uploads'
    assert app.config['OUTPUT_FOLDER'] == 'output'
    assert app.config['MAX_CONTENT_LENGTH'] == 500 * 1024 * 1024
    print("✓ App configuration is correct")

    # Test 3: Check database initialization
    print("\n3. Testing database initialization...")
    assert os.path.exists('video_documentation.db')
    print("✓ Database initialized")

    # Test 4: Check required directories exist
    print("\n4. Testing required directories...")
    assert os.path.exists('uploads')
    assert os.path.exists('output')
    assert os.path.exists('wav')
    print("✓ Required directories exist")

    # Test 5: Test Flask routes are registered
    print("\n5. Testing Flask routes...")
    test_client = app.test_client()

    # Test home page
    response = test_client.get('/')
    assert response.status_code == 200
    print("✓ Home page (/) works")

    # Test upload page
    response = test_client.get('/upload')
    assert response.status_code == 200
    print("✓ Upload page (/upload) works")

    # Test 6: Count registered routes
    print("\n6. Checking registered routes...")
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes.append(str(rule))

    print(f"✓ Found {len(routes)} routes:")
    for route in sorted(routes):
        print(f"  - {route}")

    assert len(routes) >= 7, f"Expected at least 7 routes, found {len(routes)}"
    print(f"✓ All expected routes are registered")

    # Test 7: Test that app can create a test client
    print("\n7. Testing Flask test client...")
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert response.content_type.startswith('text/html')
    print("✓ Flask test client works correctly")

    print("\n" + "="*70)
    print("✅ FLASK APP SMOKE TEST PASSED!")
    print("="*70)
    print("""
All checks passed:
  ✓ Flask app imports successfully
  ✓ Configuration is correct
  ✓ Database is initialized
  ✓ Required directories exist
  ✓ Routes are accessible
  ✓ All expected routes registered
  ✓ Test client works

The Flask application is ready to run!
To start the server: python -m vid2doc
""")


if __name__ == '__main__':
    main()
