import re

from .fetchers.base import Job


def _load_keywords(config: dict) -> tuple[list[str], list[str], list[str], list[str]]:
    return (
        [k.lower() for k in config.get("climate_keywords", [])],
        [k.lower() for k in config.get("management_titles", [])],
        [k.lower() for k in config.get("excluded_functions", [])],
        [k.lower() for k in config.get("complex_ic_signals", [])],
    )


def _contains_any(text: str, keywords: list[str]) -> bool:
    text = text.lower()
    return any(re.search(rf"\b{re.escape(kw)}\b", text) for kw in keywords)


def matches(job: Job, keywords_config: dict) -> bool:
    climate_kw, management_kw, excluded_kw, ic_kw = _load_keywords(keywords_config)

    haystack = f"{job.title} {job.description}"
    is_climate = _contains_any(haystack, climate_kw)
    if not is_climate:
        return False

    # Non-technical business functions (sales, marketing, finance, etc.) can
    # still carry a management title like "manager" or "director" - exclude
    # those explicitly rather than treating any management word as a match.
    is_management = _contains_any(job.title, management_kw) and not _contains_any(
        job.title, excluded_kw
    )
    is_complex_ic = _contains_any(haystack, ic_kw)

    return is_management or is_complex_ic
