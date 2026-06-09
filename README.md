# College Recruiting Database

A database of high school football players, the college **offers** they've
received, their **position**, and their **high school graduation year** — with
fast **filtering/sorting by graduation year and position**.

> See [`docs/RESEARCH.md`](docs/RESEARCH.md) for the data-source research that
> shaped this design.

## How it's built (the two data classes)

| Data | Source | Status |
|---|---|---|
| Player name, **position**, **grad year**, HS, location, stars, rating, committed school | **CollegeFootballData (CFBD) API** — free | ✅ Phase 1 (built) |
| The **list of college offers** per recruit | Manual / admin entry | ✅ Phase 2 path (built); see research for why no free feed exists |

We're following the **"A then B"** plan: ingest the player/position/grad-year
backbone from the free, legal CFBD API now, and enter offers manually for the
recruits you care about.

## Setup

```bash
pip install -e .            # or: pip install httpx pydantic
cp .env.example .env        # then add your free CFBD key
```

Get a free CFBD API key at https://collegefootballdata.com/key (free tier =
1,000 calls/month), then:

```bash
export CFBD_API_KEY=your_key_here
```

## Usage

```bash
# 1. Create the database
recruiting init

# 2. Ingest one or more recruiting classes from CFBD (needs CFBD_API_KEY)
recruiting ingest --year 2026 2027
recruiting ingest --year 2027 --state TX        # optional filters

# 3. Filter & sort — the core feature
recruiting list --grad-year 2027 --position WR --sort rating --limit 25
recruiting list --grad-year 2026 --position QB --committed no
recruiting list --grad-year 2027 --sort ranking --ascending

# 4. Offers (manual entry)
recruiting add-player --name "Jadyn Carter" --position EDGE --grad-year 2027 --state TX
recruiting offer --player-id 1 --college "Alabama" --date 2026-03-01
recruiting offer --player-id 1 --college "Georgia"
recruiting offers --player-id 1

# 5. Stats
recruiting stats        # player counts by grad year and position

# 6. Export for the public web viewer
recruiting export       # writes site/data.json
```

(If not installed as a script, use `python3 -m recruiting.cli <command>`.)

## Public web viewer (GitHub Pages)

A static, read-only viewer lives in [`site/`](site/) and is published to GitHub
Pages — no server or database hosting required. It loads `site/data.json` and
gives viewers **grad-year and position filters**, a state filter, committed/
uncommitted toggle, name/school search, sortable columns, and click-to-expand
offer lists.

**Publish/update flow:**

```bash
recruiting ingest --year 2026 2027   # pull latest data (needs CFBD_API_KEY)
recruiting export                    # regenerate site/data.json
git add site/data.json && git commit -m "Update recruiting data" && git push
```

Deployment is automated by [`.github/workflows/pages.yml`](.github/workflows/pages.yml),
which publishes `site/` to Pages on every push to **`main`** (Pages source must be
set to *GitHub Actions* in repo settings). Once the feature branch is merged to
`main`, the site goes live at:

```
https://jtheisen23.github.io/college-recruiting/
```

The repo ships with clearly-labeled **sample data** so the page renders before
your first real ingest; `recruiting export` overwrites it with live data.

## Fully automated (no local machine needed)

[`.github/workflows/refresh-data.yml`](.github/workflows/refresh-data.yml) runs
the **entire loop on GitHub's runners** — pull from the CFBD API → regenerate
`site/data.json` → commit → publish to Pages. It runs **weekly** (Mondays 09:00
UTC) and can be triggered manually from the **Actions** tab (with a custom list
of class years).

**One-time setup:** add your CFBD key as a repo secret —
**Settings → Secrets and variables → Actions → New repository secret**, name it
`CFBD_API_KEY`. (The runner can reach the CFBD API, so nothing runs on your
machine.) Free-tier usage is tiny: ~1 API call per class year per run.

> **Note on offers:** the automated pull populates player **name, position,
> grad year, high school, location, stars, ranking, and committed school** from
> CFBD. The per-recruit **offer list** has no free/legal API (see
> [`docs/RESEARCH.md`](docs/RESEARCH.md)), so it stays empty unless added by
> another method. The committed-school column is filled automatically.

## Project layout

```
recruiting/
  schema.sql        SQLite schema (players / colleges / offers / commitments)
  models.py         Pydantic models + position normalization (WDE→EDGE, etc.)
  db.py             connection, schema init, upserts (idempotent)
  cfbd_client.py    CollegeFootballData v2 recruiting API client (rate-limit aware)
  ingest.py         ingestion pipeline
  query.py          filter/sort by grad year & position; offer counts
  cli.py            command-line interface
tests/              pytest suite (no network required)
docs/RESEARCH.md    data-source research & architecture
```

## Stack

Python 3.11+, `httpx`, `pydantic`, SQLite (single-file; portable to Postgres).
All free. Run `pytest` for the test suite.

## Notes & limits

- **Filtering/sorting by grad year and position** is indexed and first-class.
- Positions are normalized to a consistent set so filters are reliable.
- CFBD free tier is 1,000 calls/month; a full class is ~1 call. ~$10/mo lifts
  this to 75,000 if you backfill many years.
- The **offers** list is the one thing with no free feed — see the research doc
  for the legal/cost tradeoffs of automating it (paid X API, etc.).
