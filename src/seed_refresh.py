import re

import requests
import yaml
from bs4 import BeautifulSoup

CLIMATE_JOBS_LIST_URL = "https://www.climatejobslist.com/companies"

# Tech Jobs for Good lists mission-driven employers across health, education,
# civic tech, climate, etc. Its company directory is paginated (~50 per
# page); pages past the end return 404. The page cap is just a backstop
# against a pagination change looping forever.
TECH_JOBS_FOR_GOOD_URL = "https://www.techjobsforgood.com/companies/"
TECH_JOBS_FOR_GOOD_MAX_PAGES = 200

# Only treat links that point at an actual company profile page as company
# names. Matching every <a> tag on the page (the original approach) also
# picked up nav links ("Talent", "Pricing", "Log in"), per-company category
# tags ("CivicTech", "Water", "Industrial"), and country/industry filters -
# all styled the same as company links, with no way to tell them apart from
# link text alone.
COMPANY_LINK_RE = re.compile(r"^/companies/[a-z0-9-]+$")
NAME_EL_CLASS_RE = re.compile(r"text-weight-bold")


def _extract_climatejobslist_names(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    seen_hrefs = set()
    names = []
    for link in soup.find_all("a", href=COMPANY_LINK_RE):
        href = link["href"]
        if href in seen_hrefs:
            continue
        # The company name sits in its own element inside the link; the link
        # itself often also wraps a job-count element, so link.get_text()
        # concatenates both ("120Water" + "0 jobs available").
        name_el = link.find(class_=NAME_EL_CLASS_RE)
        if name_el is None:
            continue
        text = name_el.get_text(strip=True)
        if not text:
            continue
        seen_hrefs.add(href)
        names.append(text)
    return names


def _extract_techjobsforgood_names(html: str) -> list[str]:
    # Each company is a "div.item" card whose name is an "a.header"; the nav
    # menu also uses a "header" class, but on a <div> outside any card.
    soup = BeautifulSoup(html, "html.parser")
    names = []
    for el in soup.select("div.item a.header"):
        text = el.get_text(strip=True)
        if text and text not in names:
            names.append(text)
    return names


def _get(session: requests.Session, url: str, timeout: int, **kwargs) -> requests.Response:
    return session.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}, **kwargs)


def _fetch_climatejobslist(session: requests.Session, timeout: int) -> list[str]:
    try:
        resp = _get(session, CLIMATE_JOBS_LIST_URL, timeout)
        resp.raise_for_status()
    except requests.RequestException:
        return []
    return _extract_climatejobslist_names(resp.text)


def _fetch_techjobsforgood(session: requests.Session, timeout: int) -> list[str]:
    names = []
    for page in range(1, TECH_JOBS_FOR_GOOD_MAX_PAGES + 1):
        try:
            resp = _get(session, TECH_JOBS_FOR_GOOD_URL, timeout, params={"page": page})
        except requests.RequestException:
            break
        if resp.status_code == 404:
            break
        if not resp.ok:
            # A transient failure mid-crawl shouldn't throw away the pages
            # already read - keep what we have and try again next week.
            break
        page_names = _extract_techjobsforgood_names(resp.text)
        if not page_names:
            break
        names.extend(page_names)
    return names


DIRECTORY_FETCHERS = [
    _fetch_climatejobslist,
    _fetch_techjobsforgood,
]


def fetch_candidate_names(timeout: int = 20) -> list[str]:
    names = []
    with requests.Session() as session:
        for fetch in DIRECTORY_FETCHERS:
            names.extend(fetch(session, timeout))
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


def main():
    added = refresh_seed("config/companies_seed.yaml")
    print(f"Added {len(added)} new seed companies")
    for name in added:
        print(f"  {name}")


if __name__ == "__main__":
    main()
