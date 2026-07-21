import math
import re
import time

import requests

from . import db
from .fetchers.base import Job

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "job-finder-personal-automation/1.0"
# Nominatim's usage policy caps automated use at 1 request/second.
MIN_REQUEST_INTERVAL_SECONDS = 1.1
EARTH_RADIUS_MILES = 3958.8

_last_request_time = 0.0


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def _split_locations(location: str) -> list[str]:
    # Some postings list multiple sites, e.g. "McCarran, NV; San Francisco, CA"
    # or "Alameda, CA or Orlando, FL" - check each independently so a job
    # counts as commutable if any one of its listed sites is in range.
    pieces = re.split(r";|\bor\b", location)
    return [p.strip() for p in pieces if p.strip()]


def geocode(
    place: str, conn, session: requests.Session | None = None
) -> tuple[float, float] | None:
    global _last_request_time

    if db.has_cached_geocode(conn, place):
        return db.get_cached_geocode(conn, place)

    requester = session or requests
    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
        time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)

    coords = None
    try:
        resp = requester.get(
            NOMINATIM_URL,
            params={"q": place, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        _last_request_time = time.monotonic()
        resp.raise_for_status()
        results = resp.json()
        if results:
            coords = (float(results[0]["lat"]), float(results[0]["lon"]))
    except (requests.RequestException, ValueError, KeyError, IndexError):
        coords = None

    db.cache_geocode(conn, place, coords)
    return coords


def passes_commute_filter(
    job: Job,
    home_lat: float,
    home_lon: float,
    max_miles: float,
    conn,
    session: requests.Session | None = None,
) -> bool:
    if job.workplace_type in ("remote", "hybrid"):
        return True

    places = _split_locations(job.location)
    if not places:
        return True

    any_resolved = False
    for place in places:
        coords = geocode(place, conn, session=session)
        if coords is None:
            continue
        any_resolved = True
        if haversine_miles(home_lat, home_lon, coords[0], coords[1]) <= max_miles:
            return True

    # Couldn't resolve any listed location - fail open rather than silently
    # dropping a potentially-good match because of a geocoding gap.
    return not any_resolved
