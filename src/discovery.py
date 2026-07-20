import re

import yaml

from .fetchers import ashby, greenhouse, lever

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
            if probe(slug):
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
