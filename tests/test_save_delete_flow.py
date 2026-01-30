import runpy
import pathlib
runpy.run_path(str(pathlib.Path(__file__).resolve().parent.parent / 'test' / 'test_save_delete_flow.py'), run_name=__name__)
