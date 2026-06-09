"""Export the database to a JSON file for the static web viewer."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_OUT = Path("site/data.json")


def export_json(conn: sqlite3.Connection, out_path: str | Path = DEFAULT_OUT) -> int:
    """Write all players (with their offers) to a JSON file. Returns player count."""
    players = conn.execute(
        """
        SELECT id, full_name, position, grad_year, high_school, city, state,
               height_in, weight_lb, stars, rating, ranking, committed_to
        FROM players
        """
    ).fetchall()

    # Pull all offers once and group in memory (avoids N+1 queries).
    offers_by_player: dict[int, list[str]] = {}
    for row in conn.execute(
        """
        SELECT o.player_id, c.name
        FROM offers o JOIN colleges c ON c.id = o.college_id
        ORDER BY c.name
        """
    ):
        offers_by_player.setdefault(row["player_id"], []).append(row["name"])

    out_players = []
    for p in players:
        offers = offers_by_player.get(p["id"], [])
        out_players.append(
            {
                "id": p["id"],
                "name": p["full_name"],
                "position": p["position"],
                "grad_year": p["grad_year"],
                "high_school": p["high_school"],
                "city": p["city"],
                "state": p["state"],
                "height_in": p["height_in"],
                "weight_lb": p["weight_lb"],
                "stars": p["stars"],
                "rating": p["rating"],
                "ranking": p["ranking"],
                "committed_to": p["committed_to"],
                "offer_count": len(offers),
                "offers": offers,
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "player_count": len(out_players),
        "sample": False,
        "players": out_players,
    }

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False))
    return len(out_players)
