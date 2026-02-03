# Test Suite Documentation

This directory contains different types of tests for the Video Documentation system.

## Test Types

### Pytest Tests (Run with `pytest`)

These are standard pytest test files that can be run with `pytest -q -k "not manual"`:

- **test_audio_capture.py** - Tests audio capture functionality
- **test_audio_wav_paths.py** - Tests WAV file path handling
- **test_document_edit_integration.py** - Integration tests for document editing API
- **test_save_delete_flow.py** - Tests database save/delete operations
- **test_suite.py** - Comprehensive test suite
- **test_smoke_flask.py** - Flask app smoke test (has if __name__ guard)

### Standalone Smoke Test Scripts (Run directly with Python)

These are end-to-end smoke tests that should be run directly, NOT via pytest:

- **test_basic.py** - Basic functionality verification
  ```bash
  pytest tests/test_basic.py
  ```

- **test_integration.py** - Quick integration test with synthetic video
  ```bash
  python tests/test_integration.py
  ```

- **test_smoke_demo.py** - Smoke test that creates a small test video
  ```bash
  python tests/test_smoke_demo.py
  ```

- **test_smoke_workflow.py** - Complete end-to-end workflow test
  ```bash
  python tests/test_smoke_workflow.py
  ```
  Note: Requires `videos/small_demo_video.mp4` to exist

## Running Tests

### Run all pytest tests (excluding manual tests)
```bash
pytest -q -k "not manual"
```

### Run a specific pytest test file
```bash
pytest -xvs tests/test_audio_capture.py
```

### Run standalone smoke tests
```bash
python tests/test_basic.py
python tests/test_smoke_demo.py
python tests/test_smoke_workflow.py
python tests/test_integration.py
```

## Note on Pytest Collection

The standalone smoke test scripts are excluded from pytest collection (see `pytest.ini`) because they:
1. Execute code at module level (not in functions)
2. Call `sys.exit()` on errors, which interferes with pytest collection
3. Are designed to be run as standalone scripts with detailed output

These scripts are still important for verifying the complete workflow works correctly!
