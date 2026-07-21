import requests

from .base import Job, strip_html

BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"


def fetch(company: str, token: str, timeout: int = 15) -> list[Job]:
    resp = requests.get(BASE_URL.format(token=token), timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    jobs = []
    for posting in data.get("jobs", []):
        description = posting.get("descriptionPlain") or strip_html(
            posting.get("descriptionHtml", "")
        )
        jobs.append(
            Job(
                id="",
                title=posting.get("title", ""),
                company=company,
                location=posting.get("location", ""),
                description=description,
                url=posting.get("jobUrl") or posting.get("applyUrl", ""),
                date_posted=posting.get("publishedAt", ""),
                source="ashby",
                workplace_type=(posting.get("workplaceType") or "").lower(),
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
