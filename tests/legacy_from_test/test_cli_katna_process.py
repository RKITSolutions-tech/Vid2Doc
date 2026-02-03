import os
import subprocess
import json
import pytest


def is_katna_installed():
    try:
        import katna  # noqa: F401
        return True
    except Exception:
        return False


def test_run_katna_cli(tmp_path):
    video_path = os.path.join('videos', 'small_demo_video.mp4')
    if not os.path.exists(video_path):
        pytest.skip('Sample video not present')
    if not is_katna_installed():
        pytest.skip('Katna not installed')

    out_dir = tmp_path / 'out'
    out_dir.mkdir()
    cmd = ['python3', 'scripts/run_katna_process.py', video_path, '--output', str(out_dir)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode == 0, f"CLI failed: {p.stderr}"
    data = json.loads(p.stdout.strip())
    assert data.get('video_id') is not None
