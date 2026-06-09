"""Client for the CollegeFootballData (CFBD) v2 recruiting API.

Free API key: https://collegefootballdata.com/key
Set it in the CFBD_API_KEY environment variable.
"""

from __future__ import annotations

import os
import time

import httpx

from .models import RecruitIn

BASE_URL = "https://apinext.collegefootballdata.com"


class CFBDError(RuntimeError):
    pass


class CFBDClient:
    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        self.api_key = api_key or os.environ.get("CFBD_API_KEY")
        if not self.api_key:
            raise CFBDError(
                "No CFBD API key. Get a free key at https://collegefootballdata.com/key "
                "and set CFBD_API_KEY."
            )
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=timeout,
        )

    def __enter__(self) -> "CFBDClient":
        return self

    def __exit__(self, *exc) -> None:
        self._client.close()

    def recruiting_players(
        self,
        year: int,
        classification: str = "HighSchool",
        position: str | None = None,
        state: str | None = None,
        team: str | None = None,
        max_retries: int = 4,
    ) -> list[RecruitIn]:
        """Fetch recruits for a class year. Returns normalized RecruitIn objects."""
        params: dict[str, object] = {"year": year, "classification": classification}
        if position:
            params["position"] = position
        if state:
            params["state"] = state
        if team:
            params["team"] = team

        backoff = 2.0
        for attempt in range(max_retries):
            resp = self._client.get("/recruiting/players", params=params)
            if resp.status_code == 429:  # rate limited — back off and retry
                time.sleep(backoff)
                backoff *= 2
                continue
            if resp.status_code == 401:
                raise CFBDError("CFBD rejected the API key (401). Check CFBD_API_KEY.")
            resp.raise_for_status()
            data = resp.json()
            return [RecruitIn.model_validate(item).normalized() for item in data]

        raise CFBDError(f"CFBD rate limit retries exhausted for year={year}")
