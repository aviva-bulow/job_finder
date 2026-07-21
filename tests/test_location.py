import math

import pytest

from src import db, location
from src.fetchers.base import Job


@pytest.fixture(autouse=True)
def _no_rate_limit_delay(monkeypatch):
    # geocode() throttles real Nominatim calls to 1/sec, which would make
    # this test module take several real seconds since it's all mocked
    # (no actual rate limit to respect) but still sleeps between calls.
    monkeypatch.setattr(location, "MIN_REQUEST_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(location, "_last_request_time", 0.0)


def make_job(workplace_type="", loc="San Francisco, CA"):
    return Job(
        id="",
        title="Engineering Manager",
        company="Acme",
        location=loc,
        description="Do climate work.",
        url="https://example.com/1",
        date_posted="2026-01-01",
        source="greenhouse",
        workplace_type=workplace_type,
    )


def test_haversine_miles_same_point_is_zero():
    assert location.haversine_miles(42.39, -85.50, 42.39, -85.50) == 0


def test_haversine_miles_one_degree_at_equator():
    # At the equator, one degree of longitude is an exact great-circle arc:
    # R * angle_in_radians, independent of the haversine implementation -
    # a solid ground-truth check on the formula and the Earth-radius constant.
    expected = location.EARTH_RADIUS_MILES * math.radians(1)
    assert location.haversine_miles(0, 0, 0, 1) == pytest.approx(expected, abs=0.05)


def test_passes_commute_filter_always_true_for_remote(tmp_path):
    with db.connect(str(tmp_path / "jobs.sqlite")) as conn:
        job = make_job(workplace_type="remote", loc="Antarctica")
        assert location.passes_commute_filter(job, 42.39, -85.50, 50, conn) is True


def test_passes_commute_filter_always_true_for_hybrid(tmp_path):
    with db.connect(str(tmp_path / "jobs.sqlite")) as conn:
        job = make_job(workplace_type="hybrid", loc="Antarctica")
        assert location.passes_commute_filter(job, 42.39, -85.50, 50, conn) is True


def test_passes_commute_filter_onsite_within_range(tmp_path, requests_mock):
    requests_mock.get(
        location.NOMINATIM_URL,
        json=[{"lat": "42.40", "lon": "-85.51"}],
    )
    with db.connect(str(tmp_path / "jobs.sqlite")) as conn:
        job = make_job(workplace_type="onsite", loc="Kalamazoo, MI")
        assert location.passes_commute_filter(job, 42.39, -85.50, 50, conn) is True


def test_passes_commute_filter_onsite_outside_range(tmp_path, requests_mock):
    requests_mock.get(
        location.NOMINATIM_URL,
        json=[{"lat": "40.7128", "lon": "-74.0060"}],  # New York City
    )
    with db.connect(str(tmp_path / "jobs.sqlite")) as conn:
        job = make_job(workplace_type="onsite", loc="New York, NY")
        assert location.passes_commute_filter(job, 42.39, -85.50, 50, conn) is False


def test_passes_commute_filter_fails_open_when_ungeocodable(tmp_path, requests_mock):
    requests_mock.get(location.NOMINATIM_URL, json=[])
    with db.connect(str(tmp_path / "jobs.sqlite")) as conn:
        job = make_job(workplace_type="onsite", loc="Nowhereville")
        assert location.passes_commute_filter(job, 42.39, -85.50, 50, conn) is True


def test_passes_commute_filter_passes_if_any_listed_site_in_range(tmp_path, requests_mock):
    def responder(request, context):
        q = request.qs["q"][0]
        if "kalamazoo" in q.lower():
            return [{"lat": "42.40", "lon": "-85.51"}]
        return [{"lat": "40.7128", "lon": "-74.0060"}]

    requests_mock.get(location.NOMINATIM_URL, json=responder)
    with db.connect(str(tmp_path / "jobs.sqlite")) as conn:
        job = make_job(workplace_type="onsite", loc="New York, NY; Kalamazoo, MI")
        assert location.passes_commute_filter(job, 42.39, -85.50, 50, conn) is True


def test_geocode_uses_cache_on_second_call(tmp_path, requests_mock):
    requests_mock.get(
        location.NOMINATIM_URL,
        json=[{"lat": "42.40", "lon": "-85.51"}],
    )
    with db.connect(str(tmp_path / "jobs.sqlite")) as conn:
        first = location.geocode("Kalamazoo, MI", conn)
        second = location.geocode("Kalamazoo, MI", conn)

    assert first == (42.40, -85.51)
    assert second == (42.40, -85.51)
    assert requests_mock.call_count == 1
