import pytest
from frame_analysis_gpu import extract_frames_gpu


def test_missing_input_raises_runtimeerror(tmp_path):
    outdir = tmp_path / 'out'
    outdir.mkdir()
    with pytest.raises(RuntimeError):
        # pass a file that does not exist
        extract_frames_gpu(str(tmp_path / 'no_such_file.mp4'), str(outdir), sample_limit=8)
