from src import filters
from src.fetchers.base import Job

KEYWORDS_CONFIG = {
    "climate_keywords": ["climate", "renewable", "solar"],
    "management_titles": ["manager", "director", "head of"],
    "complex_ic_signals": ["staff engineer", "research scientist", "quantitative"],
}


def make_job(title, description=""):
    return Job(
        id="",
        title=title,
        company="Acme",
        location="Remote",
        description=description,
        url="https://example.com/1",
        date_posted="2026-01-01",
        source="greenhouse",
    )


def test_climate_management_title_matches():
    job = make_job("Engineering Manager", "Join our solar deployment team.")
    assert filters.matches(job, KEYWORDS_CONFIG) is True


def test_climate_complex_ic_matches():
    job = make_job("Staff Engineer", "Build renewable grid forecasting systems.")
    assert filters.matches(job, KEYWORDS_CONFIG) is True


def test_non_climate_management_does_not_match():
    job = make_job("Engineering Manager", "Build our e-commerce checkout flow.")
    assert filters.matches(job, KEYWORDS_CONFIG) is False


def test_climate_without_management_or_ic_does_not_match():
    job = make_job("Customer Support Rep", "Help solar customers with billing.")
    assert filters.matches(job, KEYWORDS_CONFIG) is False


def test_keyword_match_is_case_insensitive():
    job = make_job("DIRECTOR of Engineering", "We build CLIMATE software.")
    assert filters.matches(job, KEYWORDS_CONFIG) is True


def test_keyword_match_respects_word_boundaries():
    job = make_job("Director", "We help teams acclimate to new tools.")
    assert filters.matches(job, KEYWORDS_CONFIG) is False
