"""Deprecated root module.

The purge helper moved into the `vid2doc` package. Import from
`vid2doc.database_purge` or run `scripts/check_env.py`/`scripts/consolidate_tests.py` as needed.
"""

raise ImportError("module 'database_purge' moved: import from 'vid2doc.database_purge' instead")
"""Compatibility shim for `database_purge` moved into the `vid2doc` package.

This root-level module re-exports from `vid2doc.database_purge` so existing
CLI usage continues to work during migration.
"""

from vid2doc.database_purge import *  # noqa: F401,F403
"""Standalone helper for purging audio_failures older than N days.
"""
import sys
from datetime import datetime, timedelta

from database import get_db_connection


def purge_audio_failures_older_than_days(days: int) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = datetime.utcnow() - timedelta(days=days)
    cursor.execute('DELETE FROM audio_failures WHERE created_at < ?', (cutoff,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


if __name__ == '__main__':
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    d = purge_audio_failures_older_than_days(days)
    print(f"Purged {d} audio failures older than {days} days")
