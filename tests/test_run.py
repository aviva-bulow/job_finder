import sqlite3

import pytest

from src import run
from src.fetchers.base import Job


def make_job(n):
    return Job(
        id=f"job-{n}",
        title=f"Engineering Manager {n}",
        company="Acme",
        location="Remote",
        description=f"Climate software posting {n}.",
        url=f"https://example.com/{n}",
        date_posted="2026-01-01",
        source="greenhouse",
    )


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    db_path = str(tmp_path / "jobs.sqlite")
    configs = {
        "config/settings.yaml": {
            "score_threshold": 7,
            "claude_model": "test-model",
            "resume_url": "https://example.com/resume.tex",
            "db_path": db_path,
        },
        "config/keywords.yaml": {
            "mission_keywords": ["climate"],
            "management_titles": ["manager"],
        },
        "config/companies.yaml": {"companies": []},
    }
    jobs = [make_job(n) for n in range(run.SCORE_BATCH_SIZE + 1)]
    sheet_calls = []

    monkeypatch.setattr(run, "load_yaml", lambda path: configs[path])
    monkeypatch.setattr(run, "fetch_all_jobs", lambda companies: jobs)
    monkeypatch.setattr(run.resume, "fetch_resume_text", lambda url: "resume")
    monkeypatch.setattr(run.anthropic, "Anthropic", lambda: None)
    monkeypatch.setattr(
        run.digest_sheets,
        "append_matches",
        lambda creds, sheet_id, date, matches: sheet_calls.append(
            [m["job"].id for m in matches]
        ),
    )
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    for var in ("GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "DIGEST_RECIPIENT_EMAIL"):
        monkeypatch.delenv(var, raising=False)

    return db_path, sheet_calls


def scored_ids(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return {row[0] for row in conn.execute("SELECT id FROM seen_jobs WHERE score IS NOT NULL")}
    finally:
        conn.close()


def test_interrupted_run_keeps_completed_batches_and_their_matches(pipeline, monkeypatch):
    db_path, sheet_calls = pipeline
    calls = []

    def fake_score(client, model, resume_text, batch, **kwargs):
        calls.append(batch)
        if len(calls) > 1:
            raise KeyboardInterrupt  # simulates the process being killed mid-run
        return {i: {"score": 8, "reasoning": "fit"} for i in range(len(batch))}

    monkeypatch.setattr(run, "score_jobs_batch", fake_score)

    with pytest.raises(KeyboardInterrupt):
        run.main()

    first_batch = {f"job-{n}" for n in range(run.SCORE_BATCH_SIZE)}
    assert scored_ids(db_path) == first_batch
    assert [set(ids) for ids in sheet_calls] == [first_batch]


def test_rerun_after_interruption_scores_only_remaining_jobs(pipeline, monkeypatch):
    db_path, sheet_calls = pipeline
    calls = []

    def interrupted(client, model, resume_text, batch, **kwargs):
        calls.append(batch)
        if len(calls) > 1:
            raise KeyboardInterrupt
        return {i: {"score": 3, "reasoning": "weak"} for i in range(len(batch))}

    monkeypatch.setattr(run, "score_jobs_batch", interrupted)
    with pytest.raises(KeyboardInterrupt):
        run.main()

    rerun_batches = []

    def rerun(client, model, resume_text, batch, **kwargs):
        rerun_batches.append([job.id for job in batch])
        return {i: {"score": 3, "reasoning": "weak"} for i in range(len(batch))}

    monkeypatch.setattr(run, "score_jobs_batch", rerun)
    run.main()

    assert rerun_batches == [[f"job-{run.SCORE_BATCH_SIZE}"]]
    assert sheet_calls == []
