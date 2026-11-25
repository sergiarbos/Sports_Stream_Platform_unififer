"""
TheSportsDB adapter (https://www.thesportsdb.com/api.php).
Covers football (LaLiga, PL, UCL, UEL, Bundesliga, Serie A, Ligue 1),
basketball (NBA), motorsport (MotoGP), tennis (Wimbledon) and
winter sports (FIS Alpine Ski, Biathlon, Ski Jumping, Cross-Country...).

✅ PUBLIC KEY — safe to publish
--------------------------------
The key "123" is TheSportsDB's official public test key
(the old key "3" was permanently disabled).
Stored in .env with default value "123".

⚠️  RATE LIMIT
--------------
With key=123 the limit is ~30 requests/minute per IP (Cloudflare).
The adapter therefore combines two endpoints (next + past) and adds
a sleep between calls to stay within the limit.

Validated league IDs:
  Football  : PL=4328, Bundesliga=4331, Serie A=4332, Ligue1=4334,
              LaLiga=4335, UCL=4418, UEL=4480
  Motorsport: MotoGP=4407
  Basketball: NBA=4387
  Tennis    : Wimbledon=4451
  Winter    : Alpine Ski WC=5625, Biathlon WC=5342, Ski Jumping WC=5724,
              Cross-Country WC=5722, Freestyle WC=5723, Nordic Combined WC=5725,
              Ski Cross WC=5726, Snowboard Alpine WC=5730
"""

import time
from datetime import UTC, datetime

import requests
from django.conf import settings
from django.core.cache import cache

from .adapters import BaseSourceAdapter

TSDB_BASE = "https://www.thesportsdb.com/api/v1/json"

# project slug → (idLeague, season_string)
# season_string: "2025-2026" for winter leagues, "2026" for summer/motorsport/tennis
LEAGUE_CONFIG = {
    # --- Football ---
    "champions-league": (4418, "2025-2026"),
    "europa-league": (4480, "2025-2026"),
    "la-liga": (4335, "2025-2026"),
    "premier-league": (4328, "2025-2026"),
    "serie-a": (4332, "2025-2026"),
    "bundesliga": (4331, "2025-2026"),
    "ligue-1": (4334, "2025-2026"),
    # --- Basketball ---
    "nba": (4387, "2025-2026"),
    # --- Motorsport ---
    "motogp": (4407, "2026"),
    # --- Tennis ---
    "wimbledon": (4451, "2026"),
    # --- Winter sports (FIS World Cups) ---
    "esqui-alpino": (5625, "2026"),  # FIS Alpine Ski World Cup
    "biathlon": (5342, "2026-2027"),  # Biathlon World Cup
    "salto-esqui": (5724, "2026"),  # FIS Ski Jumping World Cup
    "esqui-fondo": (5722, "2026"),  # FIS Cross-Country Ski World Cup
    "esqui-freestyle": (5723, "2026"),  # FIS Freestyle World Cup
    "nordic-combined": (5725, "2026"),  # FIS Nordic Combined World Cup
    "ski-cross": (5726, "2026"),  # FIS Ski Cross World Cup
    "snowboard-alpino": (5730, "2026"),  # FIS Snowboard Alpine World Cup
}


def _parse_event(item):
    """Converts a TheSportsDB event into the internal event dict format."""
    date_str = item.get("dateEvent") or ""
    time_str = item.get("strTime") or "00:00:00"
    try:
        start = datetime.strptime(f"{date_str}T{time_str}", "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    start = start.replace(tzinfo=UTC)

    raw_status = item.get("strStatus") or ""
    # TheSportsDB uses: "NS" (not started), "FT" (full time), "HT" (half time)…
    if raw_status in ("NS", "", "TBD"):
        status = "scheduled"
    elif raw_status == "FT" or item.get("intHomeScore") is not None:
        status = "finished"
    else:
        status = "scheduled"

    home = item.get("strHomeTeam") or ""
    away = item.get("strAwayTeam") or ""
    title = item.get("strEvent") or (f"{home} vs {away}" if home else "Event")

    return {
        "title": title,
        "participant_home": home,
        "participant_away": away,
        "round_name": f"Round {item.get('intRound', '')}" if item.get("intRound") else "",
        "start_datetime": start,
        "external_id": f"tsdb-{item.get('idEvent', '')}",
        "status": status,
    }


def _get(api_key, endpoint, params, retries=3):
    """HTTP GET with cache + retries that respects the rate limit."""
    # Build a stable cache key from endpoint + sorted params
    league_id = params.get("id", "")
    cache_key = f"tsdb:{endpoint}:{league_id}"
    ttl = getattr(settings, "API_CACHE_TTL", 3600)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = f"{TSDB_BASE}/{api_key}/{endpoint}.php"
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 30))
                time.sleep(wait + 2)
                continue
            if r.status_code != 200:
                return []
            result = r.json().get("events") or []
            cache.set(cache_key, result, ttl)
            return result
        except Exception:
            time.sleep(5)
    return []


class TheSportsDBAdapter(BaseSourceAdapter):
    source_id = "thesportsdb"

    def fetch_events(self, competition_slug="nba", **kwargs):
        api_key = settings.THESPORTSDB_KEY or "123"
        config = LEAGUE_CONFIG.get(competition_slug)
        if not config:
            return []

        league_id, season = config

        # Combine upcoming + recent past events
        next_events = _get(api_key, "eventsnextleague", {"id": league_id})
        time.sleep(1.5)  # respect rate limit between calls
        past_events = _get(api_key, "eventspastleague", {"id": league_id})

        all_raw = past_events + next_events
        seen = set()
        events = []
        for item in all_raw:
            eid = item.get("idEvent")
            if eid in seen:
                continue
            seen.add(eid)
            parsed = _parse_event(item)
            if parsed:
                events.append(parsed)

        return events
