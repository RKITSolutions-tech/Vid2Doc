"""Standalone helper for purging audio_failures older than N days (package copy)."""
import sys
from datetime import datetime, timedelta

from vid2doc.database import get_db_connection


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
