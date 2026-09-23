"""Adapter for the free football-data.org v4 API."""

from datetime import UTC, datetime

import requests
from django.conf import settings
from django.core.cache import cache

from .adapters import BaseSourceAdapter

BASE_URL = "https://api.football-data.org/v4"

COMPETITION_CODES = {
    "champions-league": "CL",
    "la-liga": "PD",
    "premier-league": "PL",
    "serie-a": "SA",
    "bundesliga": "BL1",
    "ligue-1": "FL1",
    "mundial-2026": "WC",
}


def _parse_datetime(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _status(match):
    status = match.get("status")
    if status in ("IN_PLAY", "PAUSED"):
        return "live"
    if status == "FINISHED":
        return "finished"
    return "scheduled"


class FootballDataAdapter(BaseSourceAdapter):
    source_id = "football_data"

    def fetch_events(self, competition_slug="la-liga", **kwargs):
        token = settings.FOOTBALL_DATA_TOKEN
        if not token:
            raise RuntimeError(
                "FOOTBALL_DATA_TOKEN is missing from .env. "
                "Create a free token at https://www.football-data.org/client/register"
            )

        code = COMPETITION_CODES.get(competition_slug)
        if not code:
            return []

        cache_key = f"football-data:matches:{code}"
        ttl = getattr(settings, "API_CACHE_TTL", 3600)
        data = cache.get(cache_key)
        if data is None:
            response = requests.get(
                f"{BASE_URL}/competitions/{code}/matches",
                headers={"X-Auth-Token": token},
                params={"status": "SCHEDULED,IN_PLAY,PAUSED,FINISHED"},
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
            cache.set(cache_key, data, ttl)

        events = []
        for match in data.get("matches", []):
            home = match.get("homeTeam", {}).get("name", "")
            away = match.get("awayTeam", {}).get("name", "")
            full_time = match.get("score", {}).get("fullTime", {})
            events.append(
                {
                    "title": f"{home} vs {away}",
                    "participant_home": home,
                    "participant_away": away,
                    "start_datetime": _parse_datetime(match["utcDate"]),
                    "external_id": f"football-data-{match['id']}",
                    "status": _status(match),
                    "score_home": full_time.get("home"),
                    "score_away": full_time.get("away"),
                    "result_text": match.get("score", {}).get("winner", "") or "",
                    "round_name": str(match.get("matchday") or ""),
                }
            )
        return events