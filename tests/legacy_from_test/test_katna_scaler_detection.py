import builtins
import subprocess
from unittest import mock
import os
import tempfile

import katna_processor


def fake_completed(returncode=0, stdout="", stderr=""):
    p = subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)
    return p


def test_ffmpeg_feature_detection_cpu_only(monkeypatch):
    # Simulate ffmpeg -filters and -encoders without GPU features
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: fake_completed(returncode=0, stdout='scale, crop, transpose'))
    assert not katna_processor._ffmpeg_supports_scale_npp()
    assert not katna_processor._ffmpeg_supports_nvenc()


def test_run_ffmpeg_command_writes_log_on_error(tmp_path, monkeypatch):
    # Simulate a failing ffmpeg run
    def fake_run(cmd, capture_output=True, text=True):
        return fake_completed(returncode=1, stdout='', stderr='some ffmpeg error')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    cp = katna_processor._run_ffmpeg_command(['ffmpeg', '-i', 'in.mp4'], stderr_log_prefix='test_err_')
    assert getattr(cp, 'log_path', '') != ''
    assert os.path.exists(cp.log_path)
    # cleanup
    try:
        os.remove(cp.log_path)
    except Exception:
        pass


def test_benchmark_prefers_cpu_when_gpu_fails(monkeypatch, tmp_path):
    # Simulate GPU available but GPU run fails and CPU run succeeds
    def fake_run(cmd, capture_output=True, text=True, timeout=None):
        s = ' '.join(cmd)
        if 'ffprobe' in s:
            # return a plausible width/height
            return fake_completed(returncode=0, stdout='1280\n720\n')
        if '-filters' in s:
            return fake_completed(returncode=0, stdout='scale_npp something')
        if '-encoders' in s:
            return fake_completed(returncode=0, stdout='h264_nvenc')
        if 'h264_nvenc' in s:
            # Simulate GPU run failure
            return fake_completed(returncode=1, stderr='gpu fail')
        # CPU run
        return fake_completed(returncode=0, stdout='ok')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    choice = katna_processor._benchmark_scalers('clipped/sample.mp4', 50, secs=1)
    assert choice == 'cpu'
