"""
Static calendar adapter for competitions that the free TheSportsDB API
fails to fetch accurately (like MotoGP and the World Cup).
"""

import json
import os
from datetime import UTC, datetime

from .adapters import BaseSourceAdapter


class StaticCalendarAdapter(BaseSourceAdapter):
    source_id = "static_calendar"

    def fetch_events(self, competition_slug=None, **kwargs):
        if not competition_slug:
            return []

        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "calendars", f"{competition_slug}.json")

        if not os.path.exists(json_path):
            return []

        with open(json_path, encoding="utf-8") as f:
            raw_events = json.load(f)

        events = []
        now = datetime.now(UTC)

        for i, item in enumerate(raw_events):
            start = datetime.strptime(item["start"], "%Y-%m-%dT%H:%M:%S")
            start = start.replace(tzinfo=UTC)

            # Determine status dynamically based on current time
            if start > now:
                status = "scheduled"
            elif (now - start).total_seconds() < 9000:  # 2.5 hours live window
                status = "live"
            else:
                status = "finished"

            events.append(
                {
                    "title": item["title"],
                    "participant_home": item.get("home", ""),
                    "participant_away": item.get("away", ""),
                    "round_name": item.get("round", ""),
                    "start_datetime": start,
                    "external_id": f"static-{competition_slug}-{i}",
                    "status": status,
                    "score_home": item.get("score_home"),
                    "score_away": item.get("score_away"),
                    "result_text": item.get("result_text", ""),
                }
            )

        return events
