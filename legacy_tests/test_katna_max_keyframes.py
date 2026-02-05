import os
import pytest


pytestmark = pytest.mark.order(1)


def has_dependencies():
    try:
        import katna  # noqa: F401
        import ffmpeg  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.skipif(not has_dependencies(), reason="Katna or ffmpeg not available")
def test_katna_max_keyframes_10(tmp_path):
    from katna_processor import extract_keyframes_katna
    inp = "videos/small_demo_video.mp4"
    out = str(tmp_path / "out10")
    os.makedirs(out, exist_ok=True)
    kf = extract_keyframes_katna(inp, out, scale_percent=50, max_keyframes=10)
    assert isinstance(kf, list)
    assert len(kf) == 10


@pytest.mark.skipif(not has_dependencies(), reason="Katna or ffmpeg not available")
def test_katna_max_keyframes_0_uses_default(tmp_path):
    from katna_processor import extract_keyframes_katna
    inp = "videos/small_demo_video.mp4"
    out = str(tmp_path / "out0")
    os.makedirs(out, exist_ok=True)
    kf = extract_keyframes_katna(inp, out, scale_percent=50, max_keyframes=0)
    assert isinstance(kf, list)
    # Fallback default is 5 in our compatibility path
    assert len(kf) == 5
