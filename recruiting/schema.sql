-- College Recruiting Database schema (SQLite; portable to Postgres)
-- Phase 1: players sourced from the CollegeFootballData (CFBD) API.
-- Phase 2: offers populated via manual/admin entry.

CREATE TABLE IF NOT EXISTS players (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    position      TEXT,              -- normalized: QB, RB, WR, TE, OL, DL, EDGE, LB, DB, ATH, K, P, LS
    grad_year     INTEGER,           -- HS graduation / recruiting class year
    high_school   TEXT,
    city          TEXT,
    state         TEXT,
    height_in     INTEGER,
    weight_lb     INTEGER,
    stars         INTEGER,           -- 0-5
    rating        REAL,
    ranking       INTEGER,           -- national ranking within class (if available)
    committed_to  TEXT,              -- school the player committed to (NULL if uncommitted)
    source        TEXT NOT NULL,     -- 'cfbd', etc.
    source_id     TEXT,              -- id in the source system (dedupe key)
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS colleges (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    conference    TEXT
);

-- The Class B table: which colleges have offered a recruit.
CREATE TABLE IF NOT EXISTS offers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id     INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    college_id    INTEGER NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    offer_date    TEXT,              -- ISO date, if known
    source        TEXT,              -- 'manual', 'x', 'on3', ...
    source_url    TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(player_id, college_id)
);

CREATE TABLE IF NOT EXISTS commitments (
    player_id     INTEGER PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,
    college_id    INTEGER REFERENCES colleges(id) ON DELETE CASCADE,
    committed_on  TEXT
);

-- Sorting/filtering by grad year and position is a core requirement.
CREATE INDEX IF NOT EXISTS idx_players_grad_year ON players(grad_year);
CREATE INDEX IF NOT EXISTS idx_players_position  ON players(position);
CREATE INDEX IF NOT EXISTS idx_players_year_pos  ON players(grad_year, position);
CREATE INDEX IF NOT EXISTS idx_offers_player     ON offers(player_id);
CREATE INDEX IF NOT EXISTS idx_offers_college    ON offers(college_id);
