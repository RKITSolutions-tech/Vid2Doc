# Test directory deprecation

The `test/` directory is being deprecated and replaced by a consolidated `tests/` directory at the repository root.

Please update any local scripts, CI jobs, or documentation to reference `tests/` instead of `test/`.

Planned next steps:
- Replace shim files in `tests/` with full test files and remove the `test/` directory.
- Ensure CI references `tests/` and that all tests pass from the new location.

If you rely on the old `test/` paths, please update them now to avoid breakage.
