from src import discovery


def test_slug_candidates_basic():
    candidates = discovery.slug_candidates("Base Power Company")

    assert "basepowercompany" in candidates
    assert "base-power-company" in candidates
    assert "basepower" in candidates
    assert "base" in candidates


def test_slug_candidates_single_word():
    candidates = discovery.slug_candidates("Watershed")

    assert candidates == ["watershed"]


def test_discover_company_finds_greenhouse(requests_mock):
    requests_mock.get(
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        json={"jobs": []},
    )
    requests_mock.get(
        "https://api.lever.co/v0/postings/acme",
        status_code=404,
    )

    result = discovery.discover_company("Acme")

    assert result == {"name": "Acme", "ats_type": "greenhouse", "token": "acme"}


def test_discover_company_falls_back_to_lever(requests_mock):
    requests_mock.get(
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        status_code=404,
    )
    requests_mock.get(
        "https://api.lever.co/v0/postings/acme",
        json=[],
    )
    requests_mock.get(
        "https://api.ashbyhq.com/posting-api/job-board/acme",
        status_code=404,
    )

    result = discovery.discover_company("Acme")

    assert result == {"name": "Acme", "ats_type": "lever", "token": "acme"}


def test_discover_company_returns_none_when_no_match(requests_mock):
    requests_mock.get(
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        status_code=404,
    )
    requests_mock.get(
        "https://api.lever.co/v0/postings/acme",
        status_code=404,
    )
    requests_mock.get(
        "https://api.ashbyhq.com/posting-api/job-board/acme",
        status_code=404,
    )

    assert discovery.discover_company("Acme") is None


def test_run_discovery_writes_new_companies(tmp_path, requests_mock):
    seed_path = tmp_path / "companies_seed.yaml"
    companies_path = tmp_path / "companies.yaml"

    seed_path.write_text("companies:\n  - name: Acme\n")
    companies_path.write_text("companies: []\n")

    requests_mock.get(
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        json={"jobs": []},
    )

    discovered = discovery.run_discovery(str(seed_path), str(companies_path))

    assert discovered == [{"name": "Acme", "ats_type": "greenhouse", "token": "acme"}]

    import yaml

    saved = yaml.safe_load(companies_path.read_text())
    assert saved["companies"] == discovered


def test_run_discovery_skips_already_known_companies(tmp_path, requests_mock):
    seed_path = tmp_path / "companies_seed.yaml"
    companies_path = tmp_path / "companies.yaml"

    seed_path.write_text("companies:\n  - name: Acme\n")
    companies_path.write_text(
        "companies:\n  - name: Acme\n    ats_type: greenhouse\n    token: acme\n"
    )

    discovered = discovery.run_discovery(str(seed_path), str(companies_path))

    assert discovered == []
    assert requests_mock.call_count == 0
