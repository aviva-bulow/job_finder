# Job Finder

Automated pipeline that finds climate/renewable sector job openings — management
or mathematically/scientifically complex IC roles — and rates how well each one
fits a resume, using Claude.

## How it works

1. **Fetch** — pulls open postings from every company board recorded in
   `config/companies.yaml` (Greenhouse, Lever, or Ashby public APIs, plus any
   RSS feeds).
2. **Dedup** — skips postings already seen, either by exact listing or by an
   identical job description (catches reposts under a new URL).
3. **Filter** — keeps postings that mention climate/renewable topics *and*
   either a management-level title or a complex technical/scientific IC
   signal (see `config/keywords.yaml`).
4. **Score** — sends each filtered posting, alongside an anonymized version of
   the resume, to Claude for a 1–10 fit score with reasoning.
5. **Digest** — matches at or above the score threshold are appended to a
   Google Sheet and, if any qualify, summarized in an email.

The company list isn't hand-picked once and forgotten: `config/companies_seed.yaml`
holds company names sourced from public climate-tech directories, and
`src/discovery.py` probes each one for a live Greenhouse/Lever/Ashby board,
writing verified hits into `config/companies.yaml`. `src/seed_refresh.py`
grows the seed list itself by reading those same directories. Both run
automatically, weekly, via `.github/workflows/weekly_discovery.yml`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env  # fill in the values below
```

### Local secrets (`.env`)

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | Claude API key used for scoring |
| `GMAIL_ADDRESS` | Gmail account the digest is sent from |
| `GMAIL_APP_PASSWORD` | [App password](https://myaccount.google.com/apppasswords) for that account |
| `DIGEST_RECIPIENT_EMAIL` | Where the digest email is sent |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON key for a Google service account with edit access to the target Sheet |
| `GOOGLE_SHEET_ID` | The Sheet's ID (from its URL) |

Add the same values as **repository secrets** (Settings → Secrets and
variables → Actions) so the scheduled workflows can use them.

## Running locally

```bash
set -a; source .env; set +a
python -m src.run          # one full pipeline run
python -m src.discovery    # probe companies_seed.yaml for new boards
python -m src.seed_refresh # pull new company names from directories
```

## Tests

```bash
pytest
```

All external calls (Greenhouse/Lever/Ashby APIs, Anthropic, Gmail, Google
Sheets) are mocked in tests — no secrets are needed to run the suite, and it
runs automatically on every push via `.github/workflows/tests.yml`.

## Scheduled automation

- `.github/workflows/job_search.yml` — runs the full pipeline daily and
  commits the updated dedup database (`data/jobs.sqlite`) back to the repo.
- `.github/workflows/weekly_discovery.yml` — refreshes the seed list and
  re-runs discovery weekly, committing any new companies found.

Both also support manual triggering via `workflow_dispatch` in the Actions tab.

## Tuning

- `config/settings.yaml` — score threshold, Claude model, resume source URL.
- `config/keywords.yaml` — climate/renewable terms, management titles, and
  complex-IC signals used in the pre-filter.
- `config/companies_seed.yaml` — add company names here anytime; discovery
  picks them up automatically.

## Forking this for your own job search

Everything role-specific lives in a handful of config files — nothing you
need to change requires touching the Python. If you're also climate-tech
focused but coming from a different skill set (e.g. not
engineering/science-management), here's the checklist:

1. **Fork the repo**, then `cp .env.example .env` and fill in your own
   values (your own Anthropic key, Gmail account, Google Sheet — see
   [Local secrets](#local-secrets-env) above). Add the same values as repo
   secrets under your fork's Settings → Secrets and variables → Actions so
   the scheduled workflows run under your account, not the original owner's.

2. **Point `resume_url` at your own resume** in `config/settings.yaml`. It
   must be a raw, publicly-fetchable URL (e.g. a raw GitHub link to a `.tex`
   file in your own resume repo) — `src/resume.py` just does a plain HTTP
   GET. If your resume isn't LaTeX, `src/anonymize.py` only strips
   `\contact{...}` macros, email addresses, and GitHub/LinkedIn URLs before
   sending it to Claude for scoring; for a non-LaTeX resume you can simplify
   or skip that step, since the regexes are LaTeX-specific.

3. **Rewrite `config/keywords.yaml` for your own role targets.** This is the
   biggest thing to change, since it encodes *whose* jobs count as a fit:
   - `climate_keywords` — the climate/renewable terms are generic and
     probably don't need much editing.
   - `management_titles` — title words that mark a job as management-level.
     Adjust to the seniority you're targeting.
   - `complex_ic_signals` — individual-contributor titles that should count
     as a fit even without a management title. Replace the current
     engineering/ML-heavy list (staff engineer, ML, computer vision, etc.)
     with signals for your own field — e.g. for policy: `policy analyst`,
     `regulatory affairs`, `program manager`; for finance:
     `investment analyst`, `portfolio manager`, `climate finance`; for
     supply chain: `procurement`, `supply chain manager`, `logistics`.
   - `excluded_functions` — title words that disqualify an otherwise-matching
     `management_titles` hit (e.g. "sales manager" shouldn't match if you're
     not looking for sales roles). The current list excludes sales,
     marketing, HR, legal, and similar business functions — **delete any of
     these that are actually your target function**, since as shipped it
     would filter out roles you might want.
   - The comment in the file referencing "Aviva's technical-leadership
     background" is a leftover from the original owner — safe to delete or
     rewrite once you've customized the lists.

4. **Update the personal settings in `config/settings.yaml`**:
   `salary_min`/`salary_max` for your target range, and `home_lat`/`home_lon`
   plus `max_commute_miles` for your commute radius (get coordinates from
   any map/geocoding site by searching your address).

5. **Leave `config/companies_seed.yaml` and `config/companies.yaml` alone**
   (or add to them) — they're climate-tech company boards, which should be
   equally relevant regardless of your role, and `src/seed_refresh.py` keeps
   growing the list automatically.

6. **Run the pipeline locally first** (`python -m src.run`) to sanity-check
   your keyword and settings changes before letting the scheduled GitHub
   Actions workflows take over.
