import os
import shutil
from pathlib import Path

import pytest

from vid2doc.app import _clear_directory_contents


def test_clear_directory_contents_removes_files_and_dirs(tmp_path):
    d = tmp_path / "uploads"
    d.mkdir()

    # files that should be removed
    (d / "remove.txt").write_text("rm")
    sub = d / "subdir"
    sub.mkdir()
    (sub / "nested.txt").write_text("hello")

    # files that should be kept
    (d / ".gitkeep").write_text("")
    (d / "README.md").write_text("keep")

    _clear_directory_contents(str(d), keep_names={'.gitkeep', 'README.md'})

    remaining = {p.name for p in d.iterdir()}
    assert remaining == {'.gitkeep', 'README.md'}


def test_clear_directory_no_error_if_missing(tmp_path):
    missing = tmp_path / "does_not_exist"
    # Should not raise
    _clear_directory_contents(str(missing))
    assert not missing.exists()
