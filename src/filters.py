import re

from .fetchers.base import Job


def _load_keywords(config: dict) -> tuple[list[str], list[str], list[str], list[str]]:
    return (
        # "climate_keywords" is the pre-mission-expansion name for this list.
        [k.lower() for k in config.get("mission_keywords", config.get("climate_keywords", []))],
        [k.lower() for k in config.get("management_titles", [])],
        [k.lower() for k in config.get("excluded_functions", [])],
        [k.lower() for k in config.get("complex_ic_signals", [])],
    )


def _contains_any(text: str, keywords: list[str]) -> bool:
    text = text.lower()
    return any(re.search(rf"\b{re.escape(kw)}\b", text) for kw in keywords)


def matches(job: Job, keywords_config: dict) -> bool:
    mission_kw, management_kw, excluded_kw, ic_kw = _load_keywords(keywords_config)

    haystack = f"{job.title} {job.description}"
    is_mission = _contains_any(haystack, mission_kw)
    if not is_mission:
        return False

    # Non-technical business functions (sales, marketing, finance, etc.) can
    # still carry a management title like "manager" or "director" - exclude
    # those explicitly rather than treating any management word as a match.
    title_excluded = _contains_any(job.title, excluded_kw)
    is_management = _contains_any(job.title, management_kw) and not title_excluded
    # An IC signal in the description alone is often just company boilerplate
    # ("we use machine learning to..."), which let titles like "Payroll
    # Manager" through - so for excluded functions, require it in the title.
    is_complex_ic = _contains_any(job.title, ic_kw) or (
        not title_excluded and _contains_any(job.description, ic_kw)
    )

    return is_management or is_complex_ic
