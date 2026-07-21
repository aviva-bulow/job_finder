import re

import requests
import yaml
from bs4 import BeautifulSoup

DIRECTORY_URLS = [
    "https://www.climatejobslist.com/companies",
]

# Only treat links that point at an actual company profile page as company
# names. Matching every <a> tag on the page (the original approach) also
# picked up nav links ("Talent", "Pricing", "Log in"), per-company category
# tags ("CivicTech", "Water", "Industrial"), and country/industry filters -
# all styled the same as company links, with no way to tell them apart from
# link text alone.
COMPANY_LINK_RE = re.compile(r"^/companies/[a-z0-9-]+$")
NAME_EL_CLASS_RE = re.compile(r"text-weight-bold")


def _extract_names(html: str) -> list[str]:
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


def main():
    added = refresh_seed("config/companies_seed.yaml")
    print(f"Added {len(added)} new seed companies")
    for name in added:
        print(f"  {name}")


if __name__ == "__main__":
    main()
