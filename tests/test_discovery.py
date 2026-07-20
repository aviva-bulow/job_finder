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


def test_significant_words_drops_generic_suffixes_and_short_words():
    assert discovery.significant_words("Carbon Engineering") == ["carbon", "engineering"]
    assert discovery.significant_words("Base Power Company") == ["base", "power"]


def test_verify_board_accepts_matching_page(requests_mock):
    requests_mock.get(
        "https://boards.greenhouse.io/carbonengineering",
        text="<title>Carbon Engineering Careers</title>",
    )
    assert discovery.verify_board("greenhouse", "carbonengineering", "Carbon Engineering") is True


def test_verify_board_rejects_unrelated_company(requests_mock):
    # token resolves, but the page belongs to a different "Carbon" company
    requests_mock.get(
        "https://boards.greenhouse.io/carbon",
        text="<title>Carbon Health Careers</title>",
    )
    assert discovery.verify_board("greenhouse", "carbon", "Carbon Engineering") is False


def test_verify_board_rejects_on_fetch_failure(requests_mock):
    requests_mock.get("https://boards.greenhouse.io/acme", status_code=404)
    assert discovery.verify_board("greenhouse", "acme", "Acme") is False


def test_discover_company_finds_greenhouse(requests_mock):
    requests_mock.get(
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        json={"jobs": []},
    )
    requests_mock.get(
        "https://boards.greenhouse.io/acme",
        text="<title>Acme Careers</title>",
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
        "https://jobs.lever.co/acme",
        text="<title>Acme Careers</title>",
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


def test_discover_company_rejects_token_owned_by_unrelated_company(requests_mock):
    # The API resolves for every candidate slug, but the page content never
    # matches "Carbon Engineering" - it's some other company's board.
    for url in [
        "https://boards-api.greenhouse.io/v1/boards/carbonengineering/jobs",
        "https://boards-api.greenhouse.io/v1/boards/carbon-engineering/jobs",
        "https://boards-api.greenhouse.io/v1/boards/carbon/jobs",
    ]:
        requests_mock.get(url, json={"jobs": []})
    for url in [
        "https://boards.greenhouse.io/carbonengineering",
        "https://boards.greenhouse.io/carbon-engineering",
        "https://boards.greenhouse.io/carbon",
    ]:
        requests_mock.get(url, text="<title>Some Unrelated Company</title>")
    requests_mock.get(
        "https://api.lever.co/v0/postings/carbonengineering", status_code=404
    )
    requests_mock.get(
        "https://api.lever.co/v0/postings/carbon-engineering", status_code=404
    )
    requests_mock.get("https://api.lever.co/v0/postings/carbon", status_code=404)
    requests_mock.get(
        "https://api.ashbyhq.com/posting-api/job-board/carbonengineering",
        status_code=404,
    )
    requests_mock.get(
        "https://api.ashbyhq.com/posting-api/job-board/carbon-engineering",
        status_code=404,
    )
    requests_mock.get(
        "https://api.ashbyhq.com/posting-api/job-board/carbon", status_code=404
    )

    assert discovery.discover_company("Carbon Engineering") is None


def test_run_discovery_writes_new_companies(tmp_path, requests_mock):
    seed_path = tmp_path / "companies_seed.yaml"
    companies_path = tmp_path / "companies.yaml"

    seed_path.write_text("companies:\n  - name: Acme\n")
    companies_path.write_text("companies: []\n")

    requests_mock.get(
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs",
        json={"jobs": []},
    )
    requests_mock.get(
        "https://boards.greenhouse.io/acme",
        text="<title>Acme Careers</title>",
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
