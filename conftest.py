import os
from pathlib import Path

# Files to ignore during collection (previously in pytest.ini as collect_ignore)
_IGNORED = {
    str(Path('test') / 'test_basic.py'),
    str(Path('test') / 'test_smoke_demo.py'),
    str(Path('test') / 'test_smoke_workflow.py'),
    str(Path('test') / 'test_integration.py'),
}


def pytest_ignore_collect(path, config):
    try:
        rel = os.path.relpath(str(path))
    except Exception:
        rel = str(path)
    return rel in _IGNORED
