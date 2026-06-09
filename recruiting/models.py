"""Pydantic models and position normalization."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Map the many position labels used across sources to a consistent set so that
# filtering by position is reliable. Anything unknown is passed through upper-cased.
POSITION_MAP: dict[str, str] = {
    "QB": "QB",
    "PRO": "QB",
    "DUAL": "QB",
    "RB": "RB",
    "APB": "RB",
    "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "OT": "OL",
    "OG": "OL",
    "OC": "OL",
    "IOL": "OL",
    "OL": "OL",
    "DT": "DL",
    "DL": "DL",
    "WDE": "EDGE",
    "SDE": "EDGE",
    "EDGE": "EDGE",
    "DE": "EDGE",
    "ILB": "LB",
    "OLB": "LB",
    "LB": "LB",
    "CB": "DB",
    "S": "DB",
    "SAF": "DB",
    "DB": "DB",
    "ATH": "ATH",
    "K": "K",
    "PK": "K",
    "P": "P",
    "LS": "LS",
}


def normalize_position(raw: str | None) -> str | None:
    if not raw:
        return None
    key = raw.strip().upper()
    return POSITION_MAP.get(key, key)


class RecruitIn(BaseModel):
    """A normalized recruit, accepting CFBD v2 (camelCase) or snake_case input."""

    source: str = "cfbd"
    source_id: str | int | None = Field(default=None, alias="id")
    full_name: str = Field(alias="name")
    position: str | None = None
    grad_year: int | None = Field(default=None, alias="year")
    high_school: str | None = Field(default=None, alias="school")
    city: str | None = None
    state: str | None = Field(default=None, alias="stateProvince")
    height_in: int | None = Field(default=None, alias="height")
    weight_lb: int | None = Field(default=None, alias="weight")
    stars: int | None = None
    rating: float | None = None
    ranking: int | None = None
    committed_to: str | None = Field(default=None, alias="committedTo")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    def normalized(self) -> "RecruitIn":
        self.position = normalize_position(self.position)
        if self.source_id is not None:
            self.source_id = str(self.source_id)
        return self
