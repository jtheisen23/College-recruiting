"""Command-line interface for the college recruiting database."""

from __future__ import annotations

import argparse
import sqlite3
import sys

from . import db as dbm
from . import query as q
from .ingest import ingest_year
from .models import RecruitIn, normalize_position


def _print_players(rows: list[sqlite3.Row]) -> None:
    if not rows:
        print("(no players)")
        return
    header = f"{'ID':>5}  {'Name':<24} {'Pos':<5} {'Yr':<5} {'St':<3} {'★':<2} {'Rtg':<6} {'Offers':<6} Committed"
    print(header)
    print("-" * len(header))
    for r in rows:
        offers = r["offer_count"] if "offer_count" in r.keys() else ""
        print(
            f"{r['id']:>5}  {(r['full_name'] or '')[:24]:<24} "
            f"{(r['position'] or ''):<5} {str(r['grad_year'] or ''):<5} "
            f"{(r['state'] or ''):<3} {str(r['stars'] or ''):<2} "
            f"{str(r['rating'] or ''):<6} {str(offers):<6} {r['committed_to'] or ''}"
        )


def cmd_init(args: argparse.Namespace) -> int:
    with dbm.connect(args.db) as conn:
        dbm.init_db(conn)
    print(f"Initialized database at {args.db}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    from .cfbd_client import CFBDClient, CFBDError

    try:
        with dbm.connect(args.db) as conn, CFBDClient() as client:
            total = 0
            for year in args.year:
                n = ingest_year(
                    conn, client, year,
                    classification=args.classification,
                    state=args.state,
                    position=args.position,
                )
                print(f"  {year}: ingested {n} players")
                total += n
        print(f"Done. {total} players upserted.")
        return 0
    except CFBDError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    with dbm.connect(args.db) as conn:
        committed = {"yes": True, "no": False, "all": None}[args.committed]
        rows = q.list_players(
            conn,
            grad_year=args.grad_year,
            position=normalize_position(args.position),
            state=args.state,
            committed=committed,
            sort_by=args.sort,
            descending=not args.ascending,
            limit=args.limit,
        )
        _print_players(rows)
    return 0


def cmd_add_player(args: argparse.Namespace) -> int:
    with dbm.connect(args.db) as conn:
        recruit = RecruitIn(
            source="manual",
            id=args.source_id or args.name,
            name=args.name,
            position=args.position,
            year=args.grad_year,
            school=args.high_school,
            state=args.state,
        )
        pid = dbm.upsert_recruit(conn, recruit)
        conn.commit()
        print(f"player id {pid}: {args.name}")
    return 0


def cmd_offer_add(args: argparse.Namespace) -> int:
    with dbm.connect(args.db) as conn:
        dbm.add_offer(
            conn, args.player_id, args.college,
            offer_date=args.date, source=args.source, source_url=args.url,
        )
        conn.commit()
        print(f"recorded offer: player {args.player_id} <- {args.college}")
    return 0


def cmd_offers_show(args: argparse.Namespace) -> int:
    with dbm.connect(args.db) as conn:
        rows = q.player_offers(conn, args.player_id)
        if not rows:
            print("(no offers)")
            return 0
        for r in rows:
            date = r["offer_date"] or "?"
            print(f"  {r['college']:<28} {date:<12} [{r['source'] or ''}]")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from .export import export_json

    with dbm.connect(args.db) as conn:
        n = export_json(conn, args.out)
    print(f"Exported {n} players to {args.out}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    with dbm.connect(args.db) as conn:
        rows = q.counts_by_year_position(conn)
        for r in rows:
            print(f"  {r['grad_year'] or '?':<6} {r['position'] or '?':<5} {r['n']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="recruiting", description=__doc__)
    p.add_argument("--db", default="recruiting.db", help="path to SQLite db file")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="create the database schema")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("ingest", help="pull a recruiting class from CFBD")
    sp.add_argument("--year", type=int, nargs="+", required=True, help="class year(s)")
    sp.add_argument("--classification", default="HighSchool",
                    choices=["HighSchool", "JUCO", "PrepSchool"])
    sp.add_argument("--state", help="filter by state abbreviation (e.g. TX)")
    sp.add_argument("--position", help="filter by source position abbreviation")
    sp.set_defaults(func=cmd_ingest)

    sp = sub.add_parser("list", help="filter/sort players")
    sp.add_argument("--grad-year", type=int)
    sp.add_argument("--position")
    sp.add_argument("--state")
    sp.add_argument("--committed", choices=["yes", "no", "all"], default="all")
    sp.add_argument("--sort", default="rating", choices=sorted(q.SORTABLE))
    sp.add_argument("--ascending", action="store_true")
    sp.add_argument("--limit", type=int)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("add-player", help="manually add a player")
    sp.add_argument("--name", required=True)
    sp.add_argument("--position")
    sp.add_argument("--grad-year", type=int)
    sp.add_argument("--high-school")
    sp.add_argument("--state")
    sp.add_argument("--source-id")
    sp.set_defaults(func=cmd_add_player)

    sp = sub.add_parser("offer", help="record a college offer for a player")
    sp.add_argument("--player-id", type=int, required=True)
    sp.add_argument("--college", required=True)
    sp.add_argument("--date", help="ISO offer date, e.g. 2026-03-14")
    sp.add_argument("--source", default="manual")
    sp.add_argument("--url")
    sp.set_defaults(func=cmd_offer_add)

    sp = sub.add_parser("offers", help="show offers for a player")
    sp.add_argument("--player-id", type=int, required=True)
    sp.set_defaults(func=cmd_offers_show)

    sp = sub.add_parser("export", help="export the DB to JSON for the web viewer")
    sp.add_argument("--out", default="site/data.json", help="output JSON path")
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("stats", help="counts by grad year and position")
    sp.set_defaults(func=cmd_stats)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
