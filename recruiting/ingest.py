"""Ingestion pipeline: pull recruits from CFBD into the database."""

from __future__ import annotations

import sqlite3

from .cfbd_client import CFBDClient
from .db import upsert_recruit


def ingest_year(
    conn: sqlite3.Connection,
    client: CFBDClient,
    year: int,
    classification: str = "HighSchool",
    state: str | None = None,
    position: str | None = None,
) -> int:
    """Ingest a full recruiting class year. Returns number of players upserted."""
    recruits = client.recruiting_players(
        year=year, classification=classification, state=state, position=position
    )
    count = 0
    for recruit in recruits:
        upsert_recruit(conn, recruit)
        count += 1
    conn.commit()
    return count
