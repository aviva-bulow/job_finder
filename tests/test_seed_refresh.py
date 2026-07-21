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
    names = seed_refresh._extract_names(SAMPLE_PAGE)
    assert names == ["120Water", "Watershed"]


def test_extract_names_excludes_nav_and_category_links():
    names = seed_refresh._extract_names(SAMPLE_PAGE)
    assert "Talent" not in names
    assert "Software" not in names
    assert "Clear" not in names
    assert "CivicTech" not in names
    assert "Water" not in names


def test_extract_names_does_not_concatenate_job_count():
    names = seed_refresh._extract_names(SAMPLE_PAGE)
    assert "120Water0jobs available" not in names
    assert not any("jobs available" in name.lower() for name in names)


def test_extract_names_dedupes_repeated_company_links():
    names = seed_refresh._extract_names(SAMPLE_PAGE)
    assert names.count("120Water") == 1


def test_fetch_candidate_names_uses_extraction(requests_mock):
    requests_mock.get("https://www.climatejobslist.com/companies", text=SAMPLE_PAGE)
    names = seed_refresh.fetch_candidate_names()
    assert names == ["120Water", "Watershed"]


def test_refresh_seed_writes_new_companies(tmp_path, requests_mock):
    seed_path = tmp_path / "companies_seed.yaml"
    seed_path.write_text("companies:\n  - name: Watershed\n")

    requests_mock.get("https://www.climatejobslist.com/companies", text=SAMPLE_PAGE)

    added = seed_refresh.refresh_seed(str(seed_path))

    assert added == ["120Water"]

    import yaml

    saved = yaml.safe_load(seed_path.read_text())
    names = [c["name"] for c in saved["companies"]]
    assert names == ["Watershed", "120Water"]
