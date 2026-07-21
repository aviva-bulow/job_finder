from src.fetchers import ashby, greenhouse, lever, rss
from src.fetchers.base import strip_html


def test_strip_html_removes_real_tags():
    assert strip_html("<p>Build <b>climate</b> software.</p>") == "Build climate software."


def test_strip_html_unescapes_double_encoded_markup():
    # Some ATS postings (seen from real Greenhouse content pasted from Word)
    # store content that's been HTML-escaped twice, e.g. literal
    # "&lt;p&gt;...&lt;/p&gt;" text instead of real "<p>" tags.
    raw = "&lt;p&gt;Build &lt;b&gt;climate&lt;/b&gt; software.&lt;/p&gt;"
    assert strip_html(raw) == "Build climate software."


def test_strip_html_decodes_html_entities():
    assert strip_html("Rondo&amp;nbsp;is hiring &quot;now&quot;") == "Rondo is hiring \"now\""


def test_greenhouse_fetch_handles_double_encoded_content(requests_mock):
    requests_mock.get(
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        json={
            "jobs": [
                {
                    "title": "Site Manager",
                    "location": {"name": "Remote"},
                    "content": "&lt;p&gt;Build &lt;b&gt;climate&lt;/b&gt; software.&lt;/p&gt;",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/2",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ]
        },
    )

    jobs = greenhouse.fetch("Acme", "acme")

    assert jobs[0].description == "Build climate software."


def test_greenhouse_fetch(requests_mock):
    requests_mock.get(
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        json={
            "jobs": [
                {
                    "title": "Engineering Manager",
                    "location": {"name": "Remote"},
                    "content": "<p>Build <b>climate</b> software.</p>",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ]
        },
    )

    jobs = greenhouse.fetch("Acme", "acme")

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Engineering Manager"
    assert job.company == "Acme"
    assert job.location == "Remote"
    assert "climate" in job.description
    assert "<" not in job.description
    assert job.source == "greenhouse"
    assert job.workplace_type == "remote"


def test_greenhouse_fetch_infers_onsite_when_location_has_no_remote_mention(requests_mock):
    requests_mock.get(
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        json={
            "jobs": [
                {
                    "title": "Site Manager",
                    "location": {"name": "San Francisco, CA"},
                    "content": "<p>Manage the site.</p>",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/3",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ]
        },
    )

    jobs = greenhouse.fetch("Acme", "acme")

    assert jobs[0].workplace_type == ""


def test_greenhouse_probe(requests_mock):
    requests_mock.get(
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        json={"jobs": []},
    )
    assert greenhouse.probe("acme") is True


def test_greenhouse_probe_404(requests_mock):
    requests_mock.get(
        "https://boards-api.greenhouse.io/v1/boards/nope/jobs",
        status_code=404,
    )
    assert greenhouse.probe("nope") is False


def test_lever_fetch(requests_mock):
    requests_mock.get(
        "https://api.lever.co/v0/postings/acme",
        json=[
            {
                "text": "Director of Climate Science",
                "categories": {"location": "New York"},
                "descriptionPlain": "Lead our renewable energy modeling team.",
                "hostedUrl": "https://jobs.lever.co/acme/1",
                "createdAt": 1735689600000,
                "workplaceType": "hybrid",
            }
        ],
    )

    jobs = lever.fetch("Acme", "acme")

    assert len(jobs) == 1
    assert jobs[0].title == "Director of Climate Science"
    assert jobs[0].location == "New York"
    assert jobs[0].source == "lever"
    assert jobs[0].workplace_type == "hybrid"


def test_lever_probe(requests_mock):
    requests_mock.get("https://api.lever.co/v0/postings/acme", json=[])
    assert lever.probe("acme") is True


def test_ashby_fetch(requests_mock):
    requests_mock.get(
        "https://api.ashbyhq.com/posting-api/job-board/acme",
        json={
            "jobs": [
                {
                    "title": "Staff Engineer, Grid Software",
                    "location": "Remote - US",
                    "descriptionPlain": "Work on renewable grid optimization.",
                    "jobUrl": "https://jobs.ashbyhq.com/acme/1",
                    "publishedAt": "2026-01-01T00:00:00Z",
                    "workplaceType": "Remote",
                }
            ]
        },
    )

    jobs = ashby.fetch("Acme", "acme")

    assert len(jobs) == 1
    assert jobs[0].title == "Staff Engineer, Grid Software"
    assert jobs[0].source == "ashby"
    # Ashby's workplaceType values are capitalized ("Remote"/"Hybrid"/
    # "OnSite") - normalized lowercase to match Lever's convention.
    assert jobs[0].workplace_type == "remote"


def test_rss_fetch_rss_items(requests_mock):
    feed = """<?xml version="1.0"?>
    <rss version="2.0"><channel>
        <item>
            <title>Head of Climate Engineering</title>
            <link>https://example.com/jobs/1</link>
            <description>Lead our solar platform team.</description>
            <pubDate>Mon, 01 Jan 2026 00:00:00 GMT</pubDate>
        </item>
    </channel></rss>"""
    requests_mock.get("https://example.com/feed.xml", text=feed)

    jobs = rss.fetch("Acme", "https://example.com/feed.xml")

    assert len(jobs) == 1
    assert jobs[0].title == "Head of Climate Engineering"
    assert jobs[0].url == "https://example.com/jobs/1"
    assert jobs[0].source == "rss"


def test_rss_fetch_atom_entries(requests_mock):
    feed = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <title>Principal Scientist, Carbon Removal</title>
            <link href="https://example.com/jobs/2"/>
            <summary>Research direct air capture.</summary>
            <updated>2026-01-01T00:00:00Z</updated>
        </entry>
    </feed>"""
    requests_mock.get("https://example.com/atom.xml", text=feed)

    jobs = rss.fetch("Acme", "https://example.com/atom.xml")

    assert len(jobs) == 1
    assert jobs[0].title == "Principal Scientist, Carbon Removal"
    assert jobs[0].url == "https://example.com/jobs/2"
