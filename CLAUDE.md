# Job Finder — context for Claude

Aviva's personal job-search pipeline: finds openings at mission-driven employers
(climate, human health, education, economic opportunity, civic/public interest —
originally climate-only) for management roles or technically/scientifically
complex IC roles, scores each against her resume with Claude, and delivers
matches to a Google Sheet + email.
README.md has the user-facing docs (setup, secrets, forking guide).

## Pipeline (`python -m src.run` → `src/run.py:main`)

1. Fetch postings for every board in `config/companies.yaml` (`src/fetchers/`)
2. Drop jobs already in the SQLite DB (`db.is_seen` — by job id *or* description hash)
3. Keyword filter (`src/filters.py`, driven by `config/keywords.yaml`): needs a
   `mission_keywords` hit *and* a management title or complex-IC signal
4. Commute filter (`src/location.py` — geocodes job locations, haversine vs
   `home_lat`/`home_lon`; geocodes are cached in the DB). Non-candidates are
   recorded in the DB unscored so they're never re-evaluated.
5. Score candidates in batches (`src/scorer.py:score_jobs_batch`) — batched calls
   with prompt caching of the system text (anonymized resume + salary range).
   The prompt also scores down employers without a pro-social mission.
6. Record scores; matches ≥ `score_threshold` go to `src/digest_sheets.py`
   and `src/digest_email.py` (each skipped if its env vars are missing)

## Where things are

| Path | What |
| --- | --- |
| `src/fetchers/base.py` | `Job` dataclass, `job_id`, `description_hash`, `strip_html` |
| `src/fetchers/{greenhouse,lever,ashby,rss}.py` | One per source; each ATS has `fetch()` and `probe()` |
| `src/db.py` | Schema (`seen_jobs`, `geocode_cache`) + `_migrate` for added columns |
| `src/resume.py`, `src/anonymize.py` | Fetch resume (LaTeX from `resume_url`) and strip contact info |
| `src/discovery.py` | Probes `companies_seed.yaml` names for live ATS boards → `companies.yaml`. One-word names can verify against the wrong company's board; fix by deleting from `companies.yaml` *and* adding `skip: true` to the seed entry, or it's re-discovered weekly |
| `src/seed_refresh.py` | Scrapes Climate Jobs List + Tech Jobs for Good (paginated) to grow `companies_seed.yaml`; one fetcher per site in `DIRECTORY_FETCHERS` |
| `config/settings.yaml` | Threshold, Claude model, resume URL, salary range, home coords, commute radius |
| `config/keywords.yaml` | mission keywords (grouped by cause), management titles, complex-IC signals, excluded functions |
| `config/companies.yaml` | Verified boards: `{name, ats_type, token}` |
| `data/jobs.sqlite` | Dedup/score DB — **committed to git**; the daily workflow commits it back |
| `.github/workflows/` | `job_search.yml` (daily 13:00 UTC), `weekly_discovery.yml` (Mon 12:00 UTC), `tests.yml` (every push) |

## Development

- Activate venv: `source .venv/bin/activate`; tests: `pytest` (all external calls
  mocked with `requests-mock` / fakes — no secrets needed)
- Most `src/` modules have a matching `tests/test_*.py` (not `run.py`/`resume.py`);
  add/update tests with changes
- flake8 max line length is 100
- Secrets live in `.env` locally (gitignored) and as GitHub repo secrets for Actions
- Schema changes: add the column to `SCHEMA` *and* to `_migrate` in `src/db.py`,
  since the committed DB already exists
- "Update job dedup database" and "Weekly company discovery update" commits are
  from the bot workflows (they touch only `data/jobs.sqlite`, `config/companies.yaml`
  and `config/companies_seed.yaml`); pull before touching those files to avoid conflicts
- Mission keywords must avoid benefits/EEO/requirements boilerplate words
  ("health", "medical", "education", "disability"...) or every posting passes
