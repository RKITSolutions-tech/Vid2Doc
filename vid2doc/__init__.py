"""vid2doc package shim for incremental migration.

This module exposes a `create_app()` function so the project can be run
as a package (``python -m vid2doc``) while we gradually migrate modules
into the package. It prefers a `create_app()` defined in
`vid2doc.app` once that file is moved; otherwise it falls back to the
root-level `app` module for compatibility during the transition.
"""
from __future__ import annotations

import importlib


def create_app() -> "Flask":
    """Create or return the Flask application instance.

    Resolution order:
    1. If `vid2doc.app` exists and defines `create_app`, call it.
    2. If `vid2doc.app` defines `app`, return that.
    3. Fallback: import root-level `app` module and look for `create_app` or `app`.
    """
    # Try package-local app module first (future state)
    try:
        mod = importlib.import_module('vid2doc.app')
    except ModuleNotFoundError:
        mod = None

    if mod is not None:
        if hasattr(mod, 'create_app'):
            return getattr(mod, 'create_app')()
        if hasattr(mod, 'app'):
            return getattr(mod, 'app')

    # Fallback to existing root-level app.py for now
    root_app = importlib.import_module('app')
    if hasattr(root_app, 'create_app'):
        return getattr(root_app, 'create_app')()
    if hasattr(root_app, 'app'):
        return getattr(root_app, 'app')

    raise RuntimeError('Could not locate Flask application (create_app or app)')


__all__ = ['create_app']
