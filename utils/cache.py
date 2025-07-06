import sqlite3
import time
import threading
import json
import os

DB_PATH = os.getenv("CACHE_DB_PATH", "/tmp/bot_cache.db")

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expiry INTEGER NOT NULL
)
"""

class _SQLiteCache:
    def __init__(self, path=DB_PATH):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(_CREATE_SQL)
        self._conn.commit()
        self._lock = threading.Lock()

    def get(self, key):
        """Return cached value or None if missing/expired"""
        now = int(time.time())
        with self._lock:
            cur = self._conn.execute("SELECT value, expiry FROM cache WHERE key=?", (key,))
            row = cur.fetchone()
            if row:
                value_json, expiry = row
                if expiry == 0 or expiry > now:
                    try:
                        return json.loads(value_json)
                    except Exception:
                        return None
                # expired – delete row
                self._conn.execute("DELETE FROM cache WHERE key=?", (key,))
                self._conn.commit()
            return None

    def set(self, key, value, ttl=300):
        """Store value with TTL (seconds). ttl==0 => no expiration"""
        expiry = 0 if ttl == 0 else int(time.time()) + int(ttl)
        value_json = json.dumps(value)
        with self._lock:
            self._conn.execute(
                "REPLACE INTO cache (key, value, expiry) VALUES (?,?,?)",
                (key, value_json, expiry),
            )
            self._conn.commit()

# Singleton instance
cache = _SQLiteCache()