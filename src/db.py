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
    score INTEGER,
    reasoning TEXT
);
CREATE INDEX IF NOT EXISTS idx_seen_jobs_description_hash ON seen_jobs (description_hash);
"""


@contextmanager
def connect(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
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
            (id, description_hash, company, title, url, first_seen_date, score, reasoning)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.id,
            job.description_hash,
            job.company,
            job.title,
            job.url,
            first_seen_date,
            score,
            reasoning,
        ),
    )
