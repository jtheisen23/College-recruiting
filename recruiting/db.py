"""SQLite database helpers: connection, schema init, and upserts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import RecruitIn

DEFAULT_DB_PATH = Path("recruiting.db")
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()


def upsert_recruit(conn: sqlite3.Connection, recruit: RecruitIn) -> int:
    """Insert or update a player by (source, source_id). Returns the row id."""
    r = recruit.normalized()
    cur = conn.execute(
        """
        INSERT INTO players (
            full_name, position, grad_year, high_school, city, state,
            height_in, weight_lb, stars, rating, ranking, committed_to,
            source, source_id, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))
        ON CONFLICT(source, source_id) DO UPDATE SET
            full_name=excluded.full_name,
            position=excluded.position,
            grad_year=excluded.grad_year,
            high_school=excluded.high_school,
            city=excluded.city,
            state=excluded.state,
            height_in=excluded.height_in,
            weight_lb=excluded.weight_lb,
            stars=excluded.stars,
            rating=excluded.rating,
            ranking=excluded.ranking,
            committed_to=excluded.committed_to,
            updated_at=datetime('now')
        """,
        (
            r.full_name, r.position, r.grad_year, r.high_school, r.city, r.state,
            r.height_in, r.weight_lb, r.stars, r.rating, r.ranking, r.committed_to,
            r.source, r.source_id,
        ),
    )
    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute(
        "SELECT id FROM players WHERE source=? AND source_id=?",
        (r.source, r.source_id),
    ).fetchone()
    return row["id"]


def get_or_create_college(conn: sqlite3.Connection, name: str) -> int:
    name = name.strip()
    conn.execute("INSERT OR IGNORE INTO colleges (name) VALUES (?)", (name,))
    row = conn.execute("SELECT id FROM colleges WHERE name=?", (name,)).fetchone()
    return row["id"]


def add_offer(
    conn: sqlite3.Connection,
    player_id: int,
    college_name: str,
    offer_date: str | None = None,
    source: str = "manual",
    source_url: str | None = None,
) -> None:
    """Record that a college has offered a player (idempotent)."""
    college_id = get_or_create_college(conn, college_name)
    conn.execute(
        """
        INSERT INTO offers (player_id, college_id, offer_date, source, source_url)
        VALUES (?,?,?,?,?)
        ON CONFLICT(player_id, college_id) DO UPDATE SET
            offer_date=COALESCE(excluded.offer_date, offers.offer_date),
            source=excluded.source,
            source_url=COALESCE(excluded.source_url, offers.source_url)
        """,
        (player_id, college_id, offer_date, source, source_url),
    )
