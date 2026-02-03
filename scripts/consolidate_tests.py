#!/usr/bin/env python3
"""Consolidate test directories into a single `tests/` location.

Usage:
  python scripts/consolidate_tests.py [--apply] [--target TARGET]

By default the script performs a dry-run and prints proposed moves. Use
`--apply` to perform filesystem moves. It is conservative about duplicates:
- If a file in `test/` collides with an existing file in `tests/`, the
  source copy is moved into `tests/legacy_from_test/` for manual review.

This script does not modify test imports or CI configs; it only moves files.
Run tests locally after applying and update configs as needed.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
from pathlib import Path


def gather_files(src: Path):
    for p in src.rglob("*"):
        if p.is_file():
            rel = p.relative_to(src)
            yield p, rel


def ensure_dir(p: Path):
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Consolidate test directories into one `tests/`.")
    parser.add_argument("--apply", action="store_true", help="Perform the moves. Otherwise do a dry-run.")
    parser.add_argument("--target", default="tests", help="Target tests directory (default: tests)")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    candidates = [Path("test"), Path("tests"), Path("test_integration"), Path("test_output")]
    found = [p for p in candidates if p.exists()]

    print("Found test directories:")
    for p in found:
        print(f" - {p} ({sum(1 for _ in p.rglob('*') if _.is_file())} files)")

    target = repo_root / args.target
    ensure_dir(target)
    legacy = target / "legacy_from_test"
    ensure_dir(legacy)
    integration_data = target / "integration_data"
    ensure_dir(integration_data)

    planned = []

    # Move files from `test` into `tests` (or legacy if duplicates)
    src_test = repo_root / "test"
    if src_test.exists():
        for src_path, rel in gather_files(src_test):
            dest_path = target / rel
            # If destination exists, move to legacy
            if dest_path.exists():
                dest = legacy / rel
            else:
                dest = dest_path

            planned.append((src_path, dest))

    # Move contents of test_integration into integration_data
    src_integ = repo_root / "test_integration"
    if src_integ.exists():
        for src_path, rel in gather_files(src_integ):
            dest = integration_data / rel
            planned.append((src_path, dest))

    # If there is an existing `tests` dir, we don't move it; we only report
    # collisions where files would be overwritten.

    if not planned:
        print("No files to move based on current layout.")
        return 0

    print("\nProposed moves (dry-run):")
    for src, dst in planned:
        print(f" - {src} -> {dst}")

    if not args.apply:
        print("\nDry-run complete. Re-run with --apply to perform moves.")
        return 0

    # Apply moves
    print("\nApplying moves...")
    for src, dst in planned:
        ensure_dir(dst.parent)
        # If identical file exists at dst, skip moving and note
        if dst.exists():
            # If files are identical, skip moving
            try:
                if filecmp.cmp(src, dst, shallow=False):
                    print(f"Skipping identical file: {src} (destination already identical)")
                    src.unlink()
                    continue
            except Exception:
                pass

        shutil.move(str(src), str(dst))
        print(f"Moved: {src} -> {dst}")

    # Cleanup empty source directories if any
    def cleanup_empty_dirs(base: Path):
        for d in sorted(base.rglob("*"), key=lambda x: -len(str(x))):
            if d.is_dir():
                try:
                    next(d.iterdir())
                except StopIteration:
                    d.rmdir()

    cleanup_empty_dirs(repo_root / "test")
    cleanup_empty_dirs(repo_root / "test_integration")

    print("Migration complete. Please run pytest and update configs/CI as needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
