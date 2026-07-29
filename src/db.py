import sqlite3
from contextlib import contextmanager

from .fetchers.base import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    id TEXT PRIMARY KEY,
    description_hash TEXT NOT NULL,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    first_seen_date TEXT NOT NULL,
    date_posted TEXT,
    score INTEGER,
    reasoning TEXT
);
CREATE INDEX IF NOT EXISTS idx_seen_jobs_description_hash ON seen_jobs (description_hash);

CREATE TABLE IF NOT EXISTS geocode_cache (
    place TEXT PRIMARY KEY,
    lat REAL,
    lon REAL
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    # Databases created before date_posted existed won't have the column -
    # CREATE TABLE IF NOT EXISTS is a no-op on them, so add it explicitly.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(seen_jobs)")}
    if "date_posted" not in columns:
        conn.execute("ALTER TABLE seen_jobs ADD COLUMN date_posted TEXT")


@contextmanager
def connect(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def is_seen(conn, job: Job) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM seen_jobs WHERE id = ? OR description_hash = ? LIMIT 1",
        (job.id, job.description_hash),
    )
    return cur.fetchone() is not None


def record(
    conn,
    job: Job,
    first_seen_date: str,
    score: int | None = None,
    reasoning: str | None = None,
):
    conn.execute(
        """
        INSERT OR IGNORE INTO seen_jobs
            (id, description_hash, company, title, url, first_seen_date, date_posted, score, reasoning)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.id,
            job.description_hash,
            job.company,
            job.title,
            job.url,
            first_seen_date,
            job.date_posted,
            score,
            reasoning,
        ),
    )


def has_cached_geocode(conn, place: str) -> bool:
    cur = conn.execute("SELECT 1 FROM geocode_cache WHERE place = ?", (place,))
    return cur.fetchone() is not None


def get_cached_geocode(conn, place: str) -> tuple[float, float] | None:
    # A cached row with NULL lat/lon means a prior lookup failed to resolve
    # this place - that's cached too, so we don't keep retrying it forever.
    cur = conn.execute("SELECT lat, lon FROM geocode_cache WHERE place = ?", (place,))
    row = cur.fetchone()
    if row is None or row[0] is None:
        return None
    return (row[0], row[1])


def cache_geocode(conn, place: str, coords: tuple[float, float] | None) -> None:
    lat, lon = coords if coords else (None, None)
    conn.execute(
        "INSERT OR REPLACE INTO geocode_cache (place, lat, lon) VALUES (?, ?, ?)",
        (place, lat, lon),
    )
