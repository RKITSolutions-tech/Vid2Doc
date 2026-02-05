"""vid2doc package entrypoint.

This module exposes a `create_app()` function so the project can be run
as a package (``python -m vid2doc``). The Flask app is defined in
`vid2doc.app`.
"""
from __future__ import annotations

import importlib


def create_app() -> "Flask":
    """Create or return the Flask application instance.

    Resolution order:
    1. If `vid2doc.app` exists and defines `create_app`, call it.
    2. If `vid2doc.app` defines `app`, return that.
    """
    # Package-local app module
    try:
        mod = importlib.import_module('vid2doc.app')
    except ModuleNotFoundError:
        mod = None

    if mod is not None:
        if hasattr(mod, 'create_app'):
            return getattr(mod, 'create_app')()
        if hasattr(mod, 'app'):
            return getattr(mod, 'app')

    raise RuntimeError('Could not locate Flask application (create_app or app) in vid2doc.app')


__all__ = ['create_app']
