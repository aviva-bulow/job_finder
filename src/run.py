import datetime
import os

import anthropic
import yaml

from . import db, digest_email, digest_sheets, filters, resume
from .anonymize import anonymize_resume
from .fetchers import ashby, greenhouse, lever, rss
from .scorer import score_jobs_batch

FETCHERS = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "rss": rss.fetch,
}

# Jobs per scoring call. The system prompt + resume are cached across calls
# within a run (see scorer.py), so batching mainly amortizes the per-request
# overhead and lets more scoring happen per cache read.
SCORE_BATCH_SIZE = 10


def load_yaml(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def fetch_all_jobs(companies: list[dict]) -> list:
    jobs = []
    for company in companies:
        ats_type = company["ats_type"]
        fetch_fn = FETCHERS.get(ats_type)
        if fetch_fn is None:
            continue
        try:
            jobs.extend(fetch_fn(company["name"], company["token"]))
        except Exception as exc:  # noqa: BLE001 - one bad company shouldn't kill the run
            print(f"  fetch failed for {company['name']} ({ats_type}): {exc}")
    return jobs


def main():
    settings = load_yaml("config/settings.yaml")
    keywords_config = load_yaml("config/keywords.yaml")
    companies = load_yaml("config/companies.yaml").get("companies", [])

    print(f"Fetching postings from {len(companies)} companies...")
    all_jobs = fetch_all_jobs(companies)
    print(f"Fetched {len(all_jobs)} postings")

    resume_text = anonymize_resume(resume.fetch_resume_text(settings["resume_url"]))
    client = anthropic.Anthropic()
    today = datetime.date.today().isoformat()

    matches = []
    with db.connect(settings["db_path"]) as conn:
        new_jobs = [job for job in all_jobs if not db.is_seen(conn, job)]
        print(f"{len(new_jobs)} not previously seen")

        candidates = [job for job in new_jobs if filters.matches(job, keywords_config)]
        print(f"{len(candidates)} pass the keyword filter")

        candidate_ids = {job.id for job in candidates}
        for job in new_jobs:
            if job.id not in candidate_ids:
                db.record(conn, job, today)

        for batch_start in range(0, len(candidates), SCORE_BATCH_SIZE):
            batch = candidates[batch_start:batch_start + SCORE_BATCH_SIZE]
            try:
                results = score_jobs_batch(
                    client,
                    settings["claude_model"],
                    resume_text,
                    batch,
                    salary_min=settings.get("salary_min"),
                    salary_max=settings.get("salary_max"),
                )
            except Exception as exc:  # noqa: BLE001 - don't let one bad batch kill the run
                print(
                    f"  scoring failed for batch of {len(batch)} starting at {batch_start}: {exc}"
                )
                continue

            for i, job in enumerate(batch):
                result = results.get(i)
                if result is None:
                    print(f"  no score returned for {job.title} @ {job.company}")
                    continue
                db.record(
                    conn, job, today, score=result["score"], reasoning=result["reasoning"]
                )
                if result["score"] >= settings["score_threshold"]:
                    matches.append(
                        {"job": job, "score": result["score"], "reasoning": result["reasoning"]}
                    )

    matches.sort(key=lambda m: m["score"], reverse=True)
    print(f"{len(matches)} matches at/above threshold {settings['score_threshold']}")

    google_sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    google_service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if matches and google_sheet_id and google_service_account_json:
        digest_sheets.append_matches(google_service_account_json, google_sheet_id, today, matches)

    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("DIGEST_RECIPIENT_EMAIL")
    if matches and gmail_address and gmail_app_password and recipient:
        digest_email.send_digest(gmail_address, gmail_app_password, recipient, matches)


if __name__ == "__main__":
    main()
