import requests

from .base import Job, strip_html

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def fetch(company: str, token: str, timeout: int = 15) -> list[Job]:
    resp = requests.get(BASE_URL.format(token=token), params={"content": "true"}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for posting in data.get("jobs", []):
        location = (posting.get("location") or {}).get("name", "")
        jobs.append(
            Job(
                id="",
                title=posting.get("title", ""),
                company=company,
                location=location,
                description=strip_html(posting.get("content", "")),
                url=posting.get("absolute_url", ""),
                date_posted=posting.get("updated_at", ""),
                source="greenhouse",
                # Greenhouse has no structured remote/hybrid/onsite field -
                # "remote" reliably shows up in the location text when it
                # applies; anything else is treated as unknown (handled as
                # onsite by the commute filter).
                workplace_type="remote" if "remote" in location.lower() else "",
            )
        )
    return jobs


def probe(token: str, timeout: int = 10, session: requests.Session | None = None) -> bool:
    requester = session or requests
    try:
        resp = requester.get(BASE_URL.format(token=token), timeout=timeout)
    except requests.RequestException:
        return False
    if resp.status_code != 200:
        return False
    try:
        return isinstance(resp.json().get("jobs"), list)
    except ValueError:
        return False
