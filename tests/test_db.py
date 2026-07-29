import sqlite3

from src import db
from src.fetchers.base import Job


def make_job(url="https://example.com/1", company="Acme", description="Do climate work."):
    return Job(
        id="",
        title="Engineering Manager",
        company=company,
        location="Remote",
        description=description,
        url=url,
        date_posted="2026-01-01",
        source="greenhouse",
    )


def test_is_seen_false_for_new_job(tmp_path):
    with db.connect(str(tmp_path / "jobs.sqlite")) as conn:
        assert db.is_seen(conn, make_job()) is False


def test_record_and_is_seen_by_id(tmp_path):
    db_path = str(tmp_path / "jobs.sqlite")
    job = make_job()

    with db.connect(db_path) as conn:
        db.record(conn, job, "2026-01-01")

    with db.connect(db_path) as conn:
        assert db.is_seen(conn, job) is True


def test_is_seen_by_description_hash_with_different_url(tmp_path):
    db_path = str(tmp_path / "jobs.sqlite")
    description = "Exact same description text."
    job = make_job(url="https://example.com/1", description=description)
    reposted = make_job(url="https://example.com/1-reposted", description=description)

    with db.connect(db_path) as conn:
        db.record(conn, job, "2026-01-01")

    with db.connect(db_path) as conn:
        assert db.is_seen(conn, reposted) is True


def test_different_jobs_not_seen(tmp_path):
    db_path = str(tmp_path / "jobs.sqlite")
    job = make_job()
    other = make_job(url="https://example.com/2", description="A totally different posting.")

    with db.connect(db_path) as conn:
        db.record(conn, job, "2026-01-01")

    with db.connect(db_path) as conn:
        assert db.is_seen(conn, other) is False


def test_record_is_idempotent(tmp_path):
    db_path = str(tmp_path / "jobs.sqlite")
    job = make_job()

    with db.connect(db_path) as conn:
        db.record(conn, job, "2026-01-01")
        db.record(conn, job, "2026-01-01")
        count = conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]

    assert count == 1


def test_record_stores_date_posted(tmp_path):
    db_path = str(tmp_path / "jobs.sqlite")
    job = make_job()

    with db.connect(db_path) as conn:
        db.record(conn, job, "2026-01-05")

    with db.connect(db_path) as conn:
        row = conn.execute(
            "SELECT date_posted FROM seen_jobs WHERE id = ?", (job.id,)
        ).fetchone()

    assert row[0] == "2026-01-01"


def test_migrates_legacy_db_missing_date_posted_column(tmp_path):
    db_path = str(tmp_path / "jobs.sqlite")

    # Simulate a database created before date_posted existed.
    legacy_conn = sqlite3.connect(db_path)
    legacy_conn.executescript(
        """
        CREATE TABLE seen_jobs (
            id TEXT PRIMARY KEY,
            description_hash TEXT NOT NULL,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            first_seen_date TEXT NOT NULL,
            score INTEGER,
            reasoning TEXT
        );
        """
    )
    legacy_conn.commit()
    legacy_conn.close()

    job = make_job()
    with db.connect(db_path) as conn:
        db.record(conn, job, "2026-01-05")

    with db.connect(db_path) as conn:
        row = conn.execute(
            "SELECT date_posted FROM seen_jobs WHERE id = ?", (job.id,)
        ).fetchone()

    assert row[0] == "2026-01-01"


def test_geocode_cache_round_trip(tmp_path):
    db_path = str(tmp_path / "jobs.sqlite")

    with db.connect(db_path) as conn:
        assert db.has_cached_geocode(conn, "Kalamazoo, MI") is False
        db.cache_geocode(conn, "Kalamazoo, MI", (42.29, -85.58))

    with db.connect(db_path) as conn:
        assert db.has_cached_geocode(conn, "Kalamazoo, MI") is True
        assert db.get_cached_geocode(conn, "Kalamazoo, MI") == (42.29, -85.58)


def test_geocode_cache_stores_negative_result(tmp_path):
    db_path = str(tmp_path / "jobs.sqlite")

    with db.connect(db_path) as conn:
        db.cache_geocode(conn, "Not A Real Place", None)

    with db.connect(db_path) as conn:
        assert db.has_cached_geocode(conn, "Not A Real Place") is True
        assert db.get_cached_geocode(conn, "Not A Real Place") is None
