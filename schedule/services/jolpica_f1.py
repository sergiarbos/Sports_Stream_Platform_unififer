"""
Formula 1 adapter using the Jolpica API (successor to Ergast).

100% free, no API key required, and safe to publish in the repository
since there are no secrets involved.

Documentation: https://github.com/jolpica/jolpica-f1
Endpoint used: https://api.jolpi.ca/ergast/f1/{season}/races/?format=json

For each Grand Prix, all available sessions are imported:
  FP1, FP2, FP3 (or Sprint + SQ when applicable), Qualifying and Race.

API responses are cached (Django cache framework) for API_CACHE_TTL
seconds (default 1 h) to avoid hitting the free API repeatedly.
"""

from datetime import UTC, datetime

import requests
from django.conf import settings
from django.core.cache import cache

from .adapters import BaseSourceAdapter

JOLPICA_BASE_URL = "https://api.jolpi.ca/ergast/f1"

# API key → human-readable session label
SESSION_MAP = [
    ("FirstPractice", "Free Practice 1"),
    ("SecondPractice", "Free Practice 2"),
    ("ThirdPractice", "Free Practice 3"),
    ("Sprint", "Sprint"),
    ("SprintQualifying", "Sprint Qualifying"),
    ("Qualifying", "Qualifying"),
]


def _parse_dt(date_str, time_str):
    """Converts a date + time pair from the API into a UTC-aware datetime."""
    time_str = time_str or "00:00:00Z"
    dt = datetime.strptime(f"{date_str}T{time_str}", "%Y-%m-%dT%H:%M:%SZ")
    return dt.replace(tzinfo=UTC)


def _status(dt):
    now = datetime.now(UTC)
    if dt > now:
        return "scheduled"
    # If the session started less than 3 h ago it could still be live;
    # we mark it finished and let the admin adjust manually if needed.
    return "finished"


class JolpicaF1Adapter(BaseSourceAdapter):
    source_id = "jolpica_f1"

    def _cached_get(self, url, cache_key):
        """GET with cache. Returns parsed JSON data dict or raises on error."""
        ttl = getattr(settings, "API_CACHE_TTL", 3600)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        cache.set(cache_key, data, ttl)
        return data

    def fetch_events(self, season="current", **kwargs):
        url = f"{JOLPICA_BASE_URL}/{season}/races/?format=json"
        data = self._cached_get(url, f"jolpica:races:{season}")
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])

        # Fetch results (cached separately)
        results_url = f"{JOLPICA_BASE_URL}/{season}/results/?format=json"
        try:
            res_data = self._cached_get(results_url, f"jolpica:results:{season}")
            res_races = res_data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        except Exception:
            res_races = []

        results_by_round = {}
        for r in res_races:
            round_val = r.get("round")
            results = r.get("Results", [])
            if results:
                top_3 = [f"{res['position']}º {res['Driver']['familyName']}" for res in results[:3]]
                results_by_round[round_val] = ", ".join(top_3)

        events = []

        for race in races:
            season_val = race.get("season")
            round_val = race.get("round")
            gp_name = race.get("raceName", "Grand Prix")
            round_label = f"Round {round_val}"

            # --- Additional sessions (FP1, FP2, FP3, Qualifying, Sprint…) ---
            for api_key, session_label in SESSION_MAP:
                session = race.get(api_key)
                if not session:
                    continue
                dt = _parse_dt(session["date"], session.get("time"))
                events.append(
                    {
                        "title": f"{gp_name} · {session_label}",
                        "round_name": round_label,
                        "start_datetime": dt,
                        "external_id": f"f1-{season_val}-{round_val}-{api_key.lower()}",
                        "status": _status(dt),
                    }
                )

            # --- Main race ---
            race_dt = _parse_dt(race.get("date"), race.get("time"))
            events.append(
                {
                    "title": gp_name,
                    "round_name": round_label,
                    "start_datetime": race_dt,
                    "external_id": f"f1-{season_val}-{round_val}-race",
                    "status": _status(race_dt),
                    "result_text": results_by_round.get(round_val, ""),
                }
            )

        return events
