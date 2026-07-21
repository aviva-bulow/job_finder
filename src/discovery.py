import re
from concurrent.futures import ThreadPoolExecutor

import requests
import yaml
from urllib3.util.retry import Retry

from .fetchers import ashby, greenhouse, lever
from .fetchers.base import strip_html

DISCOVERY_WORKERS = 16

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


def verify_board(
    ats_type: str,
    token: str,
    name: str,
    timeout: int = 10,
    session: requests.Session | None = None,
) -> bool:
    url = BOARD_PAGE_URL[ats_type].format(token=token)
    requester = session or requests
    try:
        resp = requester.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
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


def discover_company(name: str, session: requests.Session | None = None) -> dict | None:
    for slug in slug_candidates(name):
        for ats_type, probe in PROBERS:
            if probe(slug, session=session) and verify_board(
                ats_type, slug, name, session=session
            ):
                return {"name": name, "ats_type": ats_type, "token": slug}
    return None


def _make_session() -> requests.Session:
    session = requests.Session()
    # Concurrent probing hits the same 3 hosts (Greenhouse/Lever/Ashby) from
    # every worker at once - transient connection errors, timeouts, and rate
    # limiting (429/5xx) are expected under that burst load. Without retries
    # those register as "token not found" and silently drop real companies,
    # which is exactly the false-negative regression parallelizing this
    # risked introducing - retry before giving up.
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=DISCOVERY_WORKERS,
        pool_maxsize=DISCOVERY_WORKERS,
        max_retries=retry,
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def run_discovery(seed_path: str, companies_path: str) -> list[dict]:
    with open(seed_path) as f:
        seed = yaml.safe_load(f) or {}
    with open(companies_path) as f:
        existing_data = yaml.safe_load(f) or {}

    existing = existing_data.get("companies") or []
    known_names = {c["name"] for c in existing}

    pending_names = [
        entry["name"] for entry in seed.get("companies", []) if entry["name"] not in known_names
    ]

    # These are independent, I/O-bound HTTP calls (each company probes up to
    # a handful of slug candidates across 3 ATS APIs) - running them
    # concurrently doesn't change which companies get accepted, it just stops
    # waiting on one company's network round-trips before starting the next.
    with _make_session() as session, ThreadPoolExecutor(max_workers=DISCOVERY_WORKERS) as pool:
        results = pool.map(lambda name: discover_company(name, session=session), pending_names)
        newly_discovered = [found for found in results if found is not None]

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
