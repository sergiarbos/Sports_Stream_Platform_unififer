"""
Static calendar adapter for competitions that the free TheSportsDB API
fails to fetch accurately (like MotoGP and the World Cup).
"""

from datetime import datetime, timezone as dt_timezone

from .adapters import BaseSourceAdapter


STATIC_EVENTS = {
    "motogp": [
        # Past events
        {"title": "Italian GP", "start": "2026-05-31T14:00:00", "round": "Carrera"},
        {"title": "Catalunya GP", "start": "2026-06-14T14:00:00", "round": "Carrera"},
        {"title": "Dutch GP - Sprint", "start": "2026-06-27T15:00:00", "round": "Sprint"},
        {"title": "Dutch GP", "start": "2026-06-28T14:00:00", "round": "Carrera"},
        # Upcoming events
        {"title": "German GP", "start": "2026-07-12T14:00:00", "round": "Carrera"},
        {"title": "British GP", "start": "2026-08-02T14:00:00", "round": "Carrera"},
        {"title": "Austrian GP", "start": "2026-08-16T14:00:00", "round": "Carrera"},
    ],
    "mundial-2026": [
        # Dieciseisavos de final
        {"title": "España vs Austria", "start": "2026-07-02T21:00:00", "round": "Dieciseisavos de final", "home": "España", "away": "Austria"},
        {"title": "Portugal vs Croacia", "start": "2026-07-03T01:00:00", "round": "Dieciseisavos de final", "home": "Portugal", "away": "Croacia"},
        {"title": "Suiza vs Argelia", "start": "2026-07-03T05:00:00", "round": "Dieciseisavos de final", "home": "Suiza", "away": "Argelia"},
        {"title": "Australia vs Egipto", "start": "2026-07-03T20:00:00", "round": "Dieciseisavos de final", "home": "Australia", "away": "Egipto"},
        {"title": "Argentina vs Cabo Verde", "start": "2026-07-04T00:00:00", "round": "Dieciseisavos de final", "home": "Argentina", "away": "Cabo Verde"},
        {"title": "Colombia vs Ghana", "start": "2026-07-04T03:30:00", "round": "Dieciseisavos de final", "home": "Colombia", "away": "Ghana"},
        # Octavos de final
        {"title": "Canadá vs Marruecos", "start": "2026-07-04T19:00:00", "round": "Octavos de final", "home": "Canadá", "away": "Marruecos"},
        {"title": "Paraguay vs Francia", "start": "2026-07-04T23:00:00", "round": "Octavos de final", "home": "Paraguay", "away": "Francia"},
        {"title": "Brasil vs Noruega", "start": "2026-07-05T22:00:00", "round": "Octavos de final", "home": "Brasil", "away": "Noruega"},
        {"title": "México vs Inglaterra", "start": "2026-07-06T02:00:00", "round": "Octavos de final", "home": "México", "away": "Inglaterra"},
        {"title": "Estados Unidos vs Bélgica", "start": "2026-07-07T02:00:00", "round": "Octavos de final", "home": "Estados Unidos", "away": "Bélgica"},
        {"title": "TBD vs TBD", "start": "2026-07-07T18:00:00", "round": "Octavos de final", "home": "TBD", "away": "TBD"},
        {"title": "TBD vs TBD", "start": "2026-07-07T22:00:00", "round": "Octavos de final", "home": "TBD", "away": "TBD"},
        # Cuartos de final
        {"title": "TBD vs TBD", "start": "2026-07-09T22:00:00", "round": "Cuartos de final", "home": "TBD", "away": "TBD"},
        {"title": "TBD vs TBD", "start": "2026-07-10T21:00:00", "round": "Cuartos de final", "home": "TBD", "away": "TBD"},
        {"title": "TBD vs TBD", "start": "2026-07-11T23:00:00", "round": "Cuartos de final", "home": "TBD", "away": "TBD"},
        {"title": "TBD vs TBD", "start": "2026-07-12T03:00:00", "round": "Cuartos de final", "home": "TBD", "away": "TBD"},
        # Semifinales
        {"title": "TBD vs TBD", "start": "2026-07-14T21:00:00", "round": "Semifinal", "home": "TBD", "away": "TBD"},
        {"title": "TBD vs TBD", "start": "2026-07-15T21:00:00", "round": "Semifinal", "home": "TBD", "away": "TBD"},
    ]
}


class StaticCalendarAdapter(BaseSourceAdapter):
    source_id = "static_calendar"

    def fetch_events(self, competition_slug=None, **kwargs):
        if not competition_slug or competition_slug not in STATIC_EVENTS:
            return []

        events = []
        raw_events = STATIC_EVENTS[competition_slug]
        
        now = datetime.now(dt_timezone.utc)

        for i, item in enumerate(raw_events):
            start = datetime.strptime(item["start"], "%Y-%m-%dT%H:%M:%S")
            start = start.replace(tzinfo=dt_timezone.utc)

            # Determine status dynamically based on current time
            if start > now:
                status = "scheduled"
            elif (now - start).total_seconds() < 9000: # 2.5 hours live window
                status = "live"
            else:
                status = "finished"

            events.append({
                "title": item["title"],
                "participant_home": item.get("home", ""),
                "participant_away": item.get("away", ""),
                "round_name": item.get("round", ""),
                "start_datetime": start,
                "external_id": f"static-{competition_slug}-{i}",
                "status": status,
            })

        return events
