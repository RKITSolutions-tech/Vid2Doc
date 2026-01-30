import runpy
import pathlib
runpy.run_path(str(pathlib.Path(__file__).resolve().parent.parent / 'test' / 'test_audio_capture.py'), run_name=__name__)
