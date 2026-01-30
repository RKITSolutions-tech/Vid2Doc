import runpy
import pathlib
runpy.run_path(str(pathlib.Path(__file__).resolve().parent.parent / 'test' / 'test_katna_scaler_edgecases.py'), run_name=__name__)
