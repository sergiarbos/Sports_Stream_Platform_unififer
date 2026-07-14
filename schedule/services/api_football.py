"""
Adapter for API-Football (https://www.api-football.com/), via RapidAPI
or directly. Covers Champions League, Europa League, World Cup, LaLiga,
Premier League, Serie A, Bundesliga, Ligue 1 and many more.

⚠️ PRIVATE KEY — DO NOT PUBLISH
---------------------------------
The free plan (100 requests/day) requires a personal API key.
That key identifies your account and quota: if published on GitHub,
anyone can exhaust your quota or use it on your behalf.
  -> Must live ONLY in your .env file (variable API_FOOTBALL_KEY)
  -> .env is in .gitignore and must never be pushed to the repository.

This adapter is implemented as a functional SKELETON: the parsing logic
is complete, but no real request is made until you add your own key
to .env.
"""

from datetime import UTC, datetime

import requests
from django.conf import settings
from django.core.cache import cache

from .adapters import BaseSourceAdapter

API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"

# Sample league IDs in API-Football (query /leagues for the full list)
LEAGUE_IDS = {
    "champions-league": 2,
    "europa-league": 3,
    "la-liga": 140,
    "premier-league": 39,
    "serie-a": 135,
    "bundesliga": 78,
    "ligue-1": 61,
    "mundial-2026": 1,
}


class ApiFootballAdapter(BaseSourceAdapter):
    source_id = "api_football"

    def fetch_events(self, competition_slug="la-liga", season=2026, **kwargs):
        api_key = settings.API_FOOTBALL_KEY
        if not api_key:
            raise RuntimeError(
                "API_FOOTBALL_KEY is missing from your .env file. "
                "Get a free key at https://www.api-football.com/ "
                "and add it to .env (never to the code)."
            )

        league_id = LEAGUE_IDS.get(competition_slug)
        cache_key = f"apifootball:{league_id}:{season}"
        ttl = getattr(settings, "API_CACHE_TTL", 3600)

        data = cache.get(cache_key)
        if data is None:
            headers = {"x-apisports-key": api_key}
            params = {"league": league_id, "season": season}
            response = requests.get(
                f"{API_FOOTBALL_BASE_URL}/fixtures", headers=headers, params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()
            cache.set(cache_key, data, ttl)

        events = []
        for item in data.get("response", []):
            fixture = item["fixture"]
            teams = item["teams"]
            start = datetime.fromtimestamp(fixture["timestamp"], tz=UTC)
            goals = item.get("goals", {})
            events.append(
                {
                    "title": f"{teams['home']['name']} vs {teams['away']['name']}",
                    "participant_home": teams["home"]["name"],
                    "participant_away": teams["away"]["name"],
                    "start_datetime": start,
                    "external_id": str(fixture["id"]),
                    "status": "scheduled"
                    if fixture["status"]["short"] in ("NS", "TBD")
                    else "finished",
                    "score_home": goals.get("home"),
                    "score_away": goals.get("away"),
                }
            )
        return events
