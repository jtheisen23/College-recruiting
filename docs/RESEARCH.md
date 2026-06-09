# Data Source Research — HS Football Recruiting Offers Database

**Date:** 2026-06-09
**Goal:** Build a database of high school football players, the college **offers**
they've received, their **position**, and their **HS graduation year**.
**Constraint chosen:** Use whatever is free/recommended; scrape only public pages
where permitted.

---

## 1. The key finding (read this first)

Your request quietly contains **two different data problems** with wildly
different difficulty and legality. Designing for both as if they were one is the
trap to avoid.

### Class A — Player attributes (EASY, free, legal)
Name, **position**, **graduation/recruiting year**, high school, hometown/state,
height/weight, star rating, national/position/state ranking, and the **school
they committed to**.

➡️ All of this is available from the **CollegeFootballData (CFBD) API** for free,
with a real API and no scraping required.

### Class B — The offer list per recruit (HARD)
"Which colleges have offered this player" — i.e. a player having 15, 30, 50
standing offers from different programs.

➡️ This is the **central thing you asked for**, and it is **not** available from
any free API. It exists only:
- On **proprietary recruit profile pages** (247Sports/On3/Rivals "Offers"
  timeline), which **actively block bots** (see §4), or
- Scattered across **X/Twitter announcements** ("Blessed to receive an offer
  from…"), which requires paid API access and messy NLP parsing.

**Bottom line:** We can stand up the player/position/grad-year database cheaply
and legally this week. The *offers* layer is the part that needs a real decision
about cost vs. legal risk vs. completeness — covered in §5.

---

## 2. Source-by-source assessment

| Source | Has player+pos+year? | Has offer list? | Free? | Scrape-friendly? | Verdict |
|---|---|---|---|---|---|
| **CFBD API** (collegefootballdata.com) | ✅ | ❌ (committed school only) | ✅ Free tier (1,000 calls/mo); $10/mo for 75k | n/a (real API) | **Backbone for Class A** |
| **247Sports** | ✅ | ✅ (on profile pages) | ❌ paywalled | ❌ blocks bots (403) | Offers exist here, but ToS-restricted + bot-blocked |
| **On3 / Rivals** | ✅ | ✅ (on profile pages) | Partial | ❌ blocks bots (403) | Same as 247 |
| **ESPN** | ✅ | Partial | Partial | ❌ | Feeds into CFBD already |
| **X / Twitter** | ➖ (in text) | ✅ (announcements) | ❌ API now paid ($100+/mo) | ❌ ToS prohibits scraping | Only realistic *offer* signal, but costly/messy |
| **Apify "On3 recruit scraper"** | ✅ | partial | ❌ paid marketplace actor | (3rd-party) | Outsources the ToS risk to a vendor; still risky |

### CFBD API details (confirmed)
- **Free tier:** 1,000 API calls/month, API key issued instantly by email
  (`collegefootballdata.com/key`).
- **Paid:** Patreon Tier 3 ≈ **$10/mo → 75,000 calls/month** + GraphQL + realtime.
- **Recruiting player endpoint returns:** `ranking, name, school (HS),
  committed_to, position, height, weight, stars, rating, city, state_province,
  year`. Filters: year, team, recruit type (HighSchool / JUCO / PrepSchool),
  state, position.
- **Does NOT return:** the full list of offers a recruit has received. Only the
  committed school.
- Data is itself aggregated from 247Sports/Rivals/ESPN, so it's the legal,
  pre-cleaned version of most of what you'd otherwise scrape.

---

## 3. What this means for "offers"

There is **no free, legal, structured feed of per-recruit offer lists.** This is
the single most important takeaway. The data you most want is the data that's
hardest to get. Realistic ways to obtain it, worst-to-best on the
legality/effort axis:

1. **Scrape 247/On3/Rivals profile pages** — they aggressively block bots (we got
   HTTP 403 just fetching their `robots.txt`), it violates their ToS, and risks
   IP bans / legal letters. Not recommended.
2. **Pay a 3rd-party scraper (Apify actor)** — shifts the work but not the ToS
   problem, and costs money per run.
3. **X/Twitter offer announcements** — coaches and players post offers publicly.
   Requires paid X API ($100+/mo basic), plus NLP to extract
   `{player, school, offering_college, date}` from free-text posts. Noisy but the
   most "internet-scale" approach and arguably the most defensible (public posts,
   official API).
4. **Manual / crowd-sourced entry** — start the offers table by hand or via a
   small admin UI for the recruits you care about. Zero cost, fully legal, slow.

---

## 4. Legal & ToS reality

- **robots.txt is a signal, not a law**, but ignoring it is strong evidence
  against any "implied license to crawl" if a dispute arises.
- 247Sports/On3/Rivals **return 403 to automated requests** and their ToS prohibit
  scraping/redistribution of their proprietary ratings and offer data.
- X/Twitter ToS prohibit scraping; their **paid API** is the only sanctioned path.
- The **CFBD API is explicitly built so you don't have to scrape** — using it is
  the clean route for everything it covers.
- Safe-by-default posture for anything we *do* fetch: respect robots.txt, set an
  identifying User-Agent, rate-limit, cache, and only store/redistribute data we
  have the right to.

---

## 5. Recommended architecture

**Stack (free):** Python 3.11+, `httpx` (API), `pydantic` (validation), `uv`
(deps), **SQLite** to start → clean migration path to **Postgres**.

```
                 ┌─────────────────────────┐
                 │   CFBD API (free key)    │  ← Class A: players, position,
                 └───────────┬─────────────┘     year, HS, location, stars,
                             │                    committed school
                             ▼
   ┌──────────────────────────────────────────────┐
   │   Ingestion layer (Python)                     │
   │   - cfbd_client.py  (paged, rate-limited)      │
   │   - normalize → pydantic models                │
   │   - upsert into DB                             │
   └───────────────────┬────────────────────────────┘
                        ▼
   ┌──────────────────────────────────────────────┐
   │   SQLite (recruiting.db)  →  later Postgres    │
   │   players / colleges / offers / commitments    │
   └───────────────────┬────────────────────────────┘
                        ▲
   ┌────────────────────┴───────────────────────────┐
   │   OFFERS layer (the hard part — pick a path §3) │
   │   e.g. X API parser  OR  manual admin entry     │
   └─────────────────────────────────────────────────┘
```

### Proposed schema (draft)

```sql
CREATE TABLE players (
    id            INTEGER PRIMARY KEY,
    full_name     TEXT NOT NULL,
    position      TEXT,              -- QB, WR, EDGE, ...
    grad_year     INTEGER,           -- HS graduation / recruiting class year
    high_school   TEXT,
    city          TEXT,
    state         TEXT,
    height_in     INTEGER,
    weight_lb     INTEGER,
    stars         INTEGER,           -- 0-5
    rating        REAL,
    source        TEXT,              -- 'cfbd', etc.
    source_id     TEXT,              -- id in the source system (dedupe key)
    UNIQUE(source, source_id)
);

CREATE TABLE colleges (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    conference    TEXT
);

CREATE TABLE offers (              -- the Class B table
    id            INTEGER PRIMARY KEY,
    player_id     INTEGER NOT NULL REFERENCES players(id),
    college_id    INTEGER NOT NULL REFERENCES colleges(id),
    offer_date    TEXT,
    source        TEXT,            -- 'x', 'manual', 'on3', ...
    source_url    TEXT,
    UNIQUE(player_id, college_id)
);

CREATE TABLE commitments (
    player_id     INTEGER PRIMARY KEY REFERENCES players(id),
    college_id    INTEGER REFERENCES colleges(id),
    committed_on  TEXT
);

-- Sorting/filtering by grad year and position is a core requirement,
-- so index both (and the common combined filter).
CREATE INDEX idx_players_grad_year ON players(grad_year);
CREATE INDEX idx_players_position  ON players(position);
CREATE INDEX idx_players_year_pos  ON players(grad_year, position);
```

### Filtering & sorting (core requirement)

You want to **sort/filter by graduating year and by position**. The schema makes
both first-class, indexed columns on `players`, so queries like the following are
fast and trivial:

```sql
-- All 2027 wide receivers, best-rated first
SELECT * FROM players
WHERE grad_year = 2027 AND position = 'WR'
ORDER BY rating DESC;

-- Count offers per recruit, filtered by class & position
SELECT p.full_name, p.position, p.grad_year, COUNT(o.id) AS offer_count
FROM players p LEFT JOIN offers o ON o.player_id = p.id
WHERE p.grad_year = 2026 AND p.position IN ('QB','EDGE')
GROUP BY p.id ORDER BY offer_count DESC;
```

Whatever query API / UI we build in Phase 3 will expose **grad year** and
**position** as the primary filter + sort controls. Note: positions need a small
normalization map (e.g. `DL/DT/EDGE`, `OL/OT/IOL`, `S/CB/DB`) so filtering is
consistent across sources.

---

## 6. Recommended phased plan

- **Phase 1 (cheap, legal, this week):** Stand up the repo + schema, get a free
  CFBD key, ingest a full recruiting class (e.g. 2026/2027) → players with
  position, grad year, HS, location, stars, and committed school. Proves the
  pipeline end-to-end.
- **Phase 2 (decision required):** Choose the offers strategy from §3. My
  recommendation: start with **manual/admin entry** for a target subset to
  validate the model and the product idea, and evaluate the **paid X API + NLP**
  path only if you need internet-scale offer coverage.
- **Phase 3:** Scheduling/refresh, dedup/entity-resolution across sources, a
  query API or simple UI, migrate SQLite → Postgres if the data grows.

---

## 7. The decision I need from you

**How do you want to source the "offers" data (§3/§5)?** This is the one choice
that changes the whole build. Options: (a) manual/admin entry to start, (b) pay
for the X API and parse announcements, (c) pay a 3rd-party scraper, or (d) defer
offers and build the player/position/year database first via CFBD.

---

## Sources

- [College Football Data API (v2)](https://apinext.collegefootballdata.com/)
- [CFBD API access tiers](https://collegefootballdata.com/api-tiers) · [Free key](https://collegefootballdata.com/key)
- [sportsdataverse/recruitR (field list)](https://github.com/sportsdataverse/recruitR/blob/main/README.md)
- [cfbfastR recruiting reference](https://cran.r-project.org/web/packages/cfbfastR/refman/cfbfastR.html)
- [247Sports recruiting](https://247sports.com/college/football/recruiting/) · [On3](https://www.on3.com/) · [Rivals](https://www.on3.com/rivals/)
- [On3 recruit scraper (Apify)](https://apify.com/erikhiggy96/on3-recruit-scraper)
- [Robots.txt scraping compliance guide](https://www.promptcloud.com/blog/robots-txt-scraping-compliance-guide/)
