# College Recruiting Database

A project to build and maintain a database of high school football players, the
college **offers** they've received, their **position**, and their **high school
graduation year**.

> **Status:** Pre-implementation. This repo currently contains a **data-source
> research report** ([`docs/RESEARCH.md`](docs/RESEARCH.md)) and a recommended
> architecture. No collection code has been written yet — see the report for the
> recommended next steps and the key decision that needs to be made first.

## TL;DR of the research

Your goal splits into two very different problems:

| Data you want | Free & legal source? | Difficulty |
|---|---|---|
| Player name, **position**, **grad/recruiting year**, HS, hometown, stars, committed school | ✅ Yes — **CollegeFootballData (CFBD) API**, free | Easy |
| The **list of college offers** each recruit received | ❌ No free API — lives only on proprietary profiles (247Sports/On3/Rivals) or X posts | Hard |

The "offers" piece — the heart of your idea — is the hard part and is **not**
available from any free, scrape-friendly source. See
[`docs/RESEARCH.md`](docs/RESEARCH.md) for the full breakdown and options.

**Sorting/filtering by graduation year and position** is a core requirement and
is built into the schema as indexed, first-class columns — see the
[Filtering & sorting](docs/RESEARCH.md#filtering--sorting-core-requirement)
section.

## Recommended stack (free)

- **Python 3.11+** — best ecosystem for data collection
- **SQLite** to start (zero-setup, a single file), with a clean path to
  **Postgres** later
- **httpx** + **pydantic** for API access and validation
- **uv** for dependency management

See the research report for the proposed schema and a phased plan.
