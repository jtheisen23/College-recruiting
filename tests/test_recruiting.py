"""Tests for the recruiting DB, models, and query layer (no network)."""

import pytest

from recruiting import db as dbm
from recruiting import query as q
from recruiting.models import RecruitIn, normalize_position


@pytest.fixture
def conn():
    c = dbm.connect(":memory:")
    dbm.init_db(c)
    yield c
    c.close()


def test_normalize_position():
    assert normalize_position("OT") == "OL"
    assert normalize_position("wde") == "EDGE"
    assert normalize_position("cb") == "DB"
    assert normalize_position(None) is None
    assert normalize_position("XYZ") == "XYZ"


def test_recruit_accepts_cfbd_camelcase():
    r = RecruitIn.model_validate(
        {
            "id": 12345,
            "name": "John Doe",
            "year": 2027,
            "school": "Central HS",
            "stateProvince": "TX",
            "committedTo": "Alabama",
            "position": "WDE",
            "stars": 4,
            "rating": 0.95,
        }
    ).normalized()
    assert r.full_name == "John Doe"
    assert r.grad_year == 2027
    assert r.state == "TX"
    assert r.committed_to == "Alabama"
    assert r.position == "EDGE"
    assert r.source_id == "12345"


def test_float_height_weight_rounded():
    # CFBD returns height/weight as floats; they must coerce to rounded ints.
    r = RecruitIn.model_validate(
        {"id": 9, "name": "Tall Guy", "height": 75.5, "weight": 220.4}
    ).normalized()
    assert r.height_in == 76
    assert r.weight_lb == 220


def test_upsert_is_idempotent(conn):
    r = RecruitIn(source="cfbd", id="1", name="A B", year=2026, position="QB")
    pid1 = dbm.upsert_recruit(conn, r)
    r.stars = 5
    pid2 = dbm.upsert_recruit(conn, r)
    assert pid1 == pid2
    rows = conn.execute("SELECT stars FROM players").fetchall()
    assert len(rows) == 1
    assert rows[0]["stars"] == 5


def test_filter_and_sort(conn):
    dbm.upsert_recruit(conn, RecruitIn(source="cfbd", id="1", name="WR1", year=2027, position="WR", rating=0.9))
    dbm.upsert_recruit(conn, RecruitIn(source="cfbd", id="2", name="WR2", year=2027, position="WR", rating=0.95))
    dbm.upsert_recruit(conn, RecruitIn(source="cfbd", id="3", name="QB1", year=2027, position="QB", rating=0.99))
    dbm.upsert_recruit(conn, RecruitIn(source="cfbd", id="4", name="WR3", year=2026, position="WR", rating=0.99))
    conn.commit()

    rows = q.list_players(conn, grad_year=2027, position="WR", sort_by="rating")
    assert [r["full_name"] for r in rows] == ["WR2", "WR1"]


def test_search_by_name(conn):
    dbm.upsert_recruit(conn, RecruitIn(source="cfbd", id="1", name="Caleb Williams", year=2027, position="QB"))
    dbm.upsert_recruit(conn, RecruitIn(source="cfbd", id="2", name="Marvin Harrison", year=2027, position="WR"))
    dbm.upsert_recruit(conn, RecruitIn(source="cfbd", id="3", name="Will Anderson", year=2027, position="EDGE"))
    conn.commit()

    # Case-insensitive substring match on the athlete's name ("will" matches
    # both "Caleb Williams" and "Will Anderson").
    assert {r["full_name"] for r in q.list_players(conn, name="will")} \
        == {"Caleb Williams", "Will Anderson"}
    assert {r["full_name"] for r in q.list_players(conn, name="harrison")} == {"Marvin Harrison"}
    # Combines with other filters.
    assert {r["full_name"] for r in q.list_players(conn, name="will", position="QB")} == {"Caleb Williams"}


def test_offers(conn):
    pid = dbm.upsert_recruit(conn, RecruitIn(source="manual", id="x", name="Star Rec", year=2027, position="ATH"))
    dbm.add_offer(conn, pid, "Alabama", offer_date="2026-01-01")
    dbm.add_offer(conn, pid, "Georgia")
    dbm.add_offer(conn, pid, "Alabama")  # duplicate -> still one
    conn.commit()

    offers = q.player_offers(conn, pid)
    assert {o["college"] for o in offers} == {"Alabama", "Georgia"}

    rows = q.list_players(conn, grad_year=2027)
    assert rows[0]["offer_count"] == 2
