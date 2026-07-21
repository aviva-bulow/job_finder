from datetime import datetime, timezone

import requests

from .base import Job, strip_html

BASE_URL = "https://api.lever.co/v0/postings/{token}"


def fetch(company: str, token: str, timeout: int = 15) -> list[Job]:
    resp = requests.get(BASE_URL.format(token=token), params={"mode": "json"}, timeout=timeout)
    resp.raise_for_status()
    postings = resp.json()

    jobs = []
    for posting in postings:
        categories = posting.get("categories") or {}
        description = posting.get("descriptionPlain") or strip_html(posting.get("description", ""))
        created_at = posting.get("createdAt")
        date_posted = ""
        if created_at:
            date_posted = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).isoformat()

        jobs.append(
            Job(
                id="",
                title=posting.get("text", ""),
                company=company,
                location=categories.get("location", ""),
                description=description,
                url=posting.get("hostedUrl", ""),
                date_posted=date_posted,
                source="lever",
            )
        )
    return jobs


def probe(token: str, timeout: int = 10, session: requests.Session | None = None) -> bool:
    requester = session or requests
    try:
        resp = requester.get(BASE_URL.format(token=token), params={"mode": "json"}, timeout=timeout)
    except requests.RequestException:
        return False
    if resp.status_code != 200:
        return False
    try:
        return isinstance(resp.json(), list)
    except ValueError:
        return False
