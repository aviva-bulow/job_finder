from src import seed_refresh

SAMPLE_PAGE = """
<html><body>
<a href="/account/talent" class="button is-small w-inline-block">Talent</a>
<a href="/category/software-engineering" class="popular_categories_item">Software</a>
<a href="#" class="pill listing w-inline-block">Clear</a>

<a href="/companies/120water" class="w-inline-block"><img src="logo.png"/></a>
<a href="/companies/120water" class="margin-bottom w-inline-block">
  <div class="custom_flex_space">
    <div class="text-size-medium text-weight-bold">120Water</div>
    <div class="job_listing_right"><div>0</div><div> jobs available</div></div>
  </div>
</a>
<a href="/companies/120water" class="padding-xsmall w-inline-block">View Company</a>
<div class="tags">
  <a href="/category/civictech">CivicTech</a>
  <a href="/category/water">Water</a>
</div>

<a href="/companies/watershed" class="margin-bottom w-inline-block">
  <div class="custom_flex_space">
    <div class="text-size-medium text-weight-bold">Watershed</div>
    <div class="job_listing_right"><div>12</div><div> jobs available</div></div>
  </div>
</a>
</body></html>
"""


def test_extract_names_only_picks_up_company_profile_links():
    names = seed_refresh._extract_climatejobslist_names(SAMPLE_PAGE)
    assert names == ["120Water", "Watershed"]


def test_extract_names_excludes_nav_and_category_links():
    names = seed_refresh._extract_climatejobslist_names(SAMPLE_PAGE)
    assert "Talent" not in names
    assert "Software" not in names
    assert "Clear" not in names
    assert "CivicTech" not in names
    assert "Water" not in names


def test_extract_names_does_not_concatenate_job_count():
    names = seed_refresh._extract_climatejobslist_names(SAMPLE_PAGE)
    assert "120Water0jobs available" not in names
    assert not any("jobs available" in name.lower() for name in names)


def test_extract_names_dedupes_repeated_company_links():
    names = seed_refresh._extract_climatejobslist_names(SAMPLE_PAGE)
    assert names.count("120Water") == 1


TJFG_PAGE_1 = """
<html><body>
<div class="ui vertical menu">
  <div class="header" style="color: #0047BB;">Account</div>
  <a href="/accounts/login/" class="item">Log In</a>
</div>
<div class="ui items">
  <div class="item" onclick="location.href='/companies/zocdoc';">
    <div class="content middle aligned overview">
      <a class="header">Zocdoc</a>
      <div class="ui basic green label">7 open tech roles</div>
      <a class="ui right floated view-company-profile button"
         href='/companies/zocdoc'>Zocdoc Jobs</a>
    </div>
  </div>
  <div class="item" onclick="location.href='/companies/recidiviz';">
    <div class="content middle aligned overview">
      <a class="header">Recidiviz</a>
      <a class="ui right floated view-company-profile button"
         href='/companies/recidiviz'>Recidiviz Jobs</a>
    </div>
  </div>
</div>
</body></html>
"""

TJFG_PAGE_2 = """
<html><body><div class="ui items">
  <div class="item"><div class="content"><a class="header">IXL Learning</a></div></div>
</div></body></html>
"""

TJFG_URL = "https://www.techjobsforgood.com/companies/"


def mock_directories(requests_mock, tjfg_responses=None):
    requests_mock.get("https://www.climatejobslist.com/companies", text=SAMPLE_PAGE)
    requests_mock.get(
        TJFG_URL,
        tjfg_responses
        or [{"text": TJFG_PAGE_1}, {"text": TJFG_PAGE_2}, {"status_code": 404}],
    )


def test_extract_techjobsforgood_names_skips_nav_headers():
    names = seed_refresh._extract_techjobsforgood_names(TJFG_PAGE_1)
    assert names == ["Zocdoc", "Recidiviz"]


def test_fetch_candidate_names_combines_directories(requests_mock):
    mock_directories(requests_mock)
    names = seed_refresh.fetch_candidate_names()
    assert names == ["120Water", "Watershed", "Zocdoc", "Recidiviz", "IXL Learning"]


def test_techjobsforgood_walks_pages_until_404(requests_mock):
    mock_directories(requests_mock)
    seed_refresh.fetch_candidate_names()
    pages = [r.qs.get("page") for r in requests_mock.request_history if "techjobsforgood" in r.url]
    assert pages == [["1"], ["2"], ["3"]]


def test_techjobsforgood_keeps_earlier_pages_on_server_error(requests_mock):
    mock_directories(requests_mock, [{"text": TJFG_PAGE_1}, {"status_code": 503}])
    names = seed_refresh.fetch_candidate_names()
    assert names[-2:] == ["Zocdoc", "Recidiviz"]


def test_one_directory_failing_does_not_block_the_other(requests_mock):
    requests_mock.get("https://www.climatejobslist.com/companies", status_code=500)
    requests_mock.get(TJFG_URL, [{"text": TJFG_PAGE_2}, {"status_code": 404}])
    assert seed_refresh.fetch_candidate_names() == ["IXL Learning"]


def test_refresh_seed_writes_new_companies(tmp_path, requests_mock):
    seed_path = tmp_path / "companies_seed.yaml"
    seed_path.write_text("companies:\n  - name: Watershed\n")

    mock_directories(requests_mock)

    added = seed_refresh.refresh_seed(str(seed_path))

    assert added == ["120Water", "Zocdoc", "Recidiviz", "IXL Learning"]

    import yaml

    saved = yaml.safe_load(seed_path.read_text())
    names = [c["name"] for c in saved["companies"]]
    assert names == ["Watershed", "120Water", "Zocdoc", "Recidiviz", "IXL Learning"]
