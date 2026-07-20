import re

import requests
import yaml
from bs4 import BeautifulSoup

DIRECTORY_URLS = [
    "https://www.climatejobslist.com/companies",
]

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9&.,'!\- ]{1,40}$")
SKIP_WORDS = {"home", "jobs", "about", "companies", "contact", "login", "sign up", "sign in", "post a job"}


def _extract_names(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    names = []
    for link in soup.find_all("a"):
        text = link.get_text(strip=True)
        if not text or not NAME_RE.match(text):
            continue
        if text.lower() in SKIP_WORDS:
            continue
        names.append(text)
    return names


def fetch_candidate_names(timeout: int = 20) -> list[str]:
    names = []
    for url in DIRECTORY_URLS:
        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
        except requests.RequestException:
            continue
        names.extend(_extract_names(resp.text))
    return names


def refresh_seed(seed_path: str) -> list[str]:
    with open(seed_path) as f:
        seed = yaml.safe_load(f) or {}

    existing = seed.get("companies") or []
    known_names = {c["name"] for c in existing}

    added = []
    for name in fetch_candidate_names():
        if name not in known_names:
            existing.append({"name": name})
            known_names.add(name)
            added.append(name)

    if added:
        with open(seed_path, "w") as f:
            yaml.safe_dump({"companies": existing}, f, sort_keys=False)

    return added
