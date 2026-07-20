import re

import requests
import yaml

from .fetchers import ashby, greenhouse, lever
from .fetchers.base import strip_html

GENERIC_SUFFIXES = [
    "inc",
    "llc",
    "co",
    "company",
    "technologies",
    "technology",
    "energy",
    "systems",
    "solutions",
    "labs",
    "industries",
    "science",
    "sciences",
]

PROBERS = [
    ("greenhouse", greenhouse.probe),
    ("lever", lever.probe),
    ("ashby", ashby.probe),
]

# Public, human-facing board pages used to verify a token candidate actually
# belongs to the named company, not just that the token happens to resolve.
# A short/common token (e.g. "carbon", "blue", "rise") can be a live board
# for a completely unrelated company — this catches that before it's recorded.
BOARD_PAGE_URL = {
    "greenhouse": "https://boards.greenhouse.io/{token}",
    "lever": "https://jobs.lever.co/{token}",
    "ashby": "https://jobs.ashbyhq.com/{token}",
}


def significant_words(name: str) -> list[str]:
    base = re.sub(r"[^a-z0-9\s-]", "", name.lower()).strip()
    words = re.split(r"[\s-]+", base)
    words = [w for w in words if w and w not in GENERIC_SUFFIXES and len(w) > 2]
    return words or [w for w in re.split(r"[\s-]+", base) if w]


def verify_board(ats_type: str, token: str, name: str, timeout: int = 10) -> bool:
    url = BOARD_PAGE_URL[ats_type].format(token=token)
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException:
        return False
    if resp.status_code != 200:
        return False

    # Require the company's significant words to appear together, as a
    # phrase - checking each word independently lets a generic word like
    # "engineering" match on any unrelated job board that happens to have
    # an "Engineering" team.
    page_text = " " + strip_html(resp.text).lower() + " "
    page_text = re.sub(r"\s+", " ", page_text)
    words = significant_words(name)
    if not words:
        return False
    return " " + " ".join(words) + " " in page_text


def slug_candidates(name: str) -> list[str]:
    base = re.sub(r"[^a-z0-9\s-]", "", name.lower()).strip()
    words = re.split(r"[\s-]+", base)

    candidates = []

    def add(slug: str):
        if slug and slug not in candidates:
            candidates.append(slug)

    add("".join(words))
    add("-".join(words))

    trimmed = [w for w in words if w not in GENERIC_SUFFIXES]
    if trimmed and trimmed != words:
        add("".join(trimmed))
        add("-".join(trimmed))

    if len(words) > 1:
        add(words[0])

    return candidates


def discover_company(name: str) -> dict | None:
    for slug in slug_candidates(name):
        for ats_type, probe in PROBERS:
            if probe(slug) and verify_board(ats_type, slug, name):
                return {"name": name, "ats_type": ats_type, "token": slug}
    return None


def run_discovery(seed_path: str, companies_path: str) -> list[dict]:
    with open(seed_path) as f:
        seed = yaml.safe_load(f) or {}
    with open(companies_path) as f:
        existing_data = yaml.safe_load(f) or {}

    existing = existing_data.get("companies") or []
    known_names = {c["name"] for c in existing}

    newly_discovered = []
    for entry in seed.get("companies", []):
        name = entry["name"]
        if name in known_names:
            continue
        found = discover_company(name)
        if found:
            newly_discovered.append(found)

    if newly_discovered:
        existing.extend(newly_discovered)
        with open(companies_path, "w") as f:
            yaml.safe_dump({"companies": existing}, f, sort_keys=False)

    return newly_discovered


def main():
    discovered = run_discovery("config/companies_seed.yaml", "config/companies.yaml")
    print(f"Discovered {len(discovered)} new company boards")
    for company in discovered:
        print(
            f"  {company['name']}: "
            f"{company['ats_type']}/{company['token']}"
        )


if __name__ == "__main__":
    main()
