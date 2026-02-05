import subprocess
import sys


def test_api_health_script():
    """Run the sanity script which exercises the app health endpoint."""
    ret = subprocess.run([sys.executable, 'scripts/check_api_health.py'], capture_output=True, text=True)
    print(ret.stdout)
    print(ret.stderr, file=sys.stderr)
    assert ret.returncode == 0
