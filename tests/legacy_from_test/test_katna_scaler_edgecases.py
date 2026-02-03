import os
import subprocess
from unittest import mock
import katna_processor


def fake_completed(returncode=0, stdout="", stderr=""):
    p = subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)
    return p


def test_missing_ffmpeg(monkeypatch):
    # Simulate ffmpeg not found by making subprocess.run raise
    def fake_run(*a, **k):
        raise FileNotFoundError('ffmpeg not found')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    try:
        # _ffmpeg_supports_scale_npp should return False rather than crash
        assert not katna_processor._ffmpeg_supports_scale_npp()
        assert not katna_processor._ffmpeg_supports_nvenc()
    finally:
        pass


def test_both_scalers_fail(monkeypatch, tmp_path):
    # Simulate ffprobe OK, GPU path available but both GPU and CPU fail
    def fake_run(cmd, capture_output=True, text=True, timeout=None):
        s = ' '.join(cmd)
        if 'ffprobe' in s:
            return fake_completed(returncode=0, stdout='640\n480\n')
        if '-filters' in s:
            return fake_completed(returncode=0, stdout='scale_npp')
        if '-encoders' in s:
            return fake_completed(returncode=0, stdout='h264_nvenc')
        # Any ffmpeg invocation fails
        return fake_completed(returncode=1, stderr='fail')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    try:
        try:
            katna_processor._create_scaled_video('clipped/sample.mp4', 50, prefer_gpu=True, auto_benchmark=False)
            assert False, 'Expected RuntimeError when both scalers fail'
        except RuntimeError:
            pass
    finally:
        pass


def test_env_presets(monkeypatch):
    monkeypatch.setenv('KATNA_NVENC_PRESET', 'p7')
    monkeypatch.setenv('KATNA_CPU_PRESET', 'medium')
    # Reload module attributes
    import importlib
    importlib.reload(katna_processor)
    assert katna_processor.NVENC_PRESET == 'p7'
    assert katna_processor.CPU_PRESET == 'medium'
