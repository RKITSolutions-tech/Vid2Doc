"""Module entrypoint for `python -m vid2doc`.

Runs the Flask development server using the package's `create_app()`.
This is a thin convenience wrapper intended for development only.
"""
from __future__ import annotations

import os
from . import create_app


def run() -> None:
    app = create_app()
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    app.run(host=host, port=port)


if __name__ == '__main__':
    run()
