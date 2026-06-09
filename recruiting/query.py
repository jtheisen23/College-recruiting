"""Query helpers — filter and sort players (core: by grad year and position)."""

from __future__ import annotations

import sqlite3

SORTABLE = {"grad_year", "position", "stars", "rating", "ranking", "full_name"}


def list_players(
    conn: sqlite3.Connection,
    grad_year: int | None = None,
    position: str | None = None,
    state: str | None = None,
    committed: bool | None = None,
    sort_by: str = "rating",
    descending: bool = True,
    limit: int | None = None,
    with_offer_count: bool = True,
) -> list[sqlite3.Row]:
    """Return players filtered by grad year / position / state, sorted as requested.

    `committed`: True = only committed, False = only uncommitted, None = all.
    """
    if sort_by not in SORTABLE:
        raise ValueError(f"sort_by must be one of {sorted(SORTABLE)}")

    where: list[str] = []
    params: list[object] = []
    if grad_year is not None:
        where.append("p.grad_year = ?")
        params.append(grad_year)
    if position is not None:
        where.append("p.position = ?")
        params.append(position.upper())
    if state is not None:
        where.append("p.state = ?")
        params.append(state.upper())
    if committed is True:
        where.append("p.committed_to IS NOT NULL")
    elif committed is False:
        where.append("p.committed_to IS NULL")

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    offer_col = (
        ", (SELECT COUNT(*) FROM offers o WHERE o.player_id = p.id) AS offer_count"
        if with_offer_count
        else ""
    )
    # NULLS LAST so unrated players don't dominate a descending sort.
    direction = "DESC" if descending else "ASC"
    order_sql = f"ORDER BY p.{sort_by} IS NULL, p.{sort_by} {direction}"
    limit_sql = f"LIMIT {int(limit)}" if limit else ""

    sql = f"SELECT p.*{offer_col} FROM players p {where_sql} {order_sql} {limit_sql}"
    return conn.execute(sql, params).fetchall()


def player_offers(conn: sqlite3.Connection, player_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT c.name AS college, o.offer_date, o.source, o.source_url
        FROM offers o JOIN colleges c ON c.id = o.college_id
        WHERE o.player_id = ?
        ORDER BY o.offer_date IS NULL, o.offer_date
        """,
        (player_id,),
    ).fetchall()


def counts_by_year_position(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT grad_year, position, COUNT(*) AS n
        FROM players
        GROUP BY grad_year, position
        ORDER BY grad_year DESC, n DESC
        """
    ).fetchall()
