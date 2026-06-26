"""
Imports real events from ALL sports via their respective APIs.

Usage:
    python manage.py import_all_sports
    python manage.py import_all_sports --sport motogp
    python manage.py import_all_sports --sport f1
    python manage.py import_all_sports --sport la-liga

Sources:
  - Formula 1         → Jolpica (free, no key required)
  - MotoGP            → TheSportsDB (public key "3")
  - Football (7 leagues) → TheSportsDB (public key "3")
  - NBA               → TheSportsDB (public key "3")
  - Wimbledon         → TheSportsDB (public key "3")
  - Winter sports     → Manual (no reliable free API available)

Broadcast assignment
---------------------
After importing events, the command automatically assigns broadcast
platforms based on the BROADCAST_MAP table defined below.
Update it if a competition airs on a different platform.
"""

import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from schedule.models import Broadcast, Competition, Event, Platform
from schedule.services.jolpica_f1 import JolpicaF1Adapter
from schedule.services.thesportsdb import TheSportsDBAdapter

# ---------------------------------------------------------------------------
# Competition slug → [(platform_slug, language, is_live_stream)]
# ---------------------------------------------------------------------------
ES = Broadcast.LANGUAGE_ES_ES
LA = Broadcast.LANGUAGE_ES_LA

BROADCAST_MAP = {
    # Football
    "champions-league": [
        ("movistar-plus", ES, True),
    ],
    "europa-league": [
        ("movistar-plus", ES, True),
    ],
    "la-liga":          [("dazn", ES, True)],
    "premier-league":   [("dazn", ES, True)],
    "serie-a":          [("dazn", ES, True)],
    "bundesliga":       [("dazn", ES, True)],
    "ligue-1":          [("dazn", ES, True)],
    "mundial-2026":     [
        ("dazn", ES, True),
        ("la-1", ES, True),         # Free-to-air on La 1 TVE (all WC 2026 matches)
        ("rtve-play", ES, True),
        ("vix", LA, True),
    ],
    # Basketball
    "nba":              [
        ("vix", LA, True),
        ("espn", ES, True),
    ],
    # Motorsport
    "f1":               [("dazn", ES, True)],
    "motogp":           [("dazn", ES, True)],
    # Tennis
    "wimbledon":        [
        ("movistar-plus", ES, True),
        ("eurosport", ES, True),
    ],
}

# Competitions to import: (competition_slug, source, fetch_kwargs)
IMPORT_PLAN = [
    # F1 — Jolpica
    ("f1", "jolpica_f1", {"season": "2026"}),
    # Motorsport — TheSportsDB
    ("motogp", "thesportsdb", {"competition_slug": "motogp"}),
    # Football — TheSportsDB
    ("champions-league", "thesportsdb", {"competition_slug": "champions-league"}),
    ("europa-league",    "thesportsdb", {"competition_slug": "europa-league"}),
    ("la-liga",          "thesportsdb", {"competition_slug": "la-liga"}),
    ("premier-league",   "thesportsdb", {"competition_slug": "premier-league"}),
    ("serie-a",          "thesportsdb", {"competition_slug": "serie-a"}),
    ("bundesliga",       "thesportsdb", {"competition_slug": "bundesliga"}),
    ("ligue-1",          "thesportsdb", {"competition_slug": "ligue-1"}),
    ("mundial-2026",     "thesportsdb", {"competition_slug": "mundial-2026"}),
    # Basketball — TheSportsDB
    ("nba",              "thesportsdb", {"competition_slug": "nba"}),
    # Tennis — TheSportsDB
    ("wimbledon",        "thesportsdb", {"competition_slug": "wimbledon"}),
]


class Command(BaseCommand):
    help = "Imports real events from all APIs (Jolpica F1 + TheSportsDB) for every sport."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sport",
            default="all",
            help=(
                "Filter by competition slug (e.g. f1, motogp, la-liga) "
                "or 'all' to import everything. Default: all."
            ),
        )

    def handle(self, *args, **options):
        sport_filter = options["sport"].lower()

        # Load platforms into a dict {slug: Platform}
        platforms = {p.slug: p for p in Platform.objects.all()}
        if not platforms:
            self.stderr.write(
                "No platforms found in the database. "
                "Run first: python manage.py seed_demo_data"
            )
            return

        adapters = {
            "jolpica_f1": JolpicaF1Adapter(),
            "thesportsdb": TheSportsDBAdapter(),
        }

        total_imported = 0
        total_broadcasts = 0

        for comp_slug, source, fetch_kwargs in IMPORT_PLAN:
            if sport_filter != "all" and sport_filter != comp_slug:
                continue

            try:
                competition = Competition.objects.get(slug=comp_slug)
            except Competition.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Competition '{comp_slug}' not found in DB. Skipping.")
                )
                continue

            self.stdout.write(f"\n📥 Importing {competition.name} ({source})…")

            adapter = adapters[source]
            try:
                events_data = adapter.fetch_events(**fetch_kwargs)
            except Exception as exc:
                self.stderr.write(f"  ✗ Error fetching data: {exc}")
                continue

            if not events_data:
                self.stdout.write(self.style.WARNING(f"  ⚠ API returned no events for {comp_slug}."))
                # If the API returns nothing, keep whatever is already in the DB
                continue

            comp_imported = 0
            comp_broadcasts = 0

            for event_data in events_data:
                event, _ = Event.objects.update_or_create(
                    competition=competition,
                    external_id=event_data["external_id"],
                    defaults={
                        "title":          event_data["title"],
                        "round_name":     event_data.get("round_name", ""),
                        "start_datetime": event_data["start_datetime"],
                        "status":         event_data["status"],
                        "participant_home": event_data.get("participant_home", ""),
                        "participant_away": event_data.get("participant_away", ""),
                    },
                )
                comp_imported += 1

                # Assign broadcasts only if the event has none yet
                if not event.broadcasts.exists():
                    bcast_config = BROADCAST_MAP.get(comp_slug, [])
                    for plat_slug, language, is_live in bcast_config:
                        plat = platforms.get(plat_slug)
                        if not plat:
                            continue
                        # VOD is only available for already-finished events
                        vod = event.status == Event.STATUS_FINISHED
                        Broadcast.objects.get_or_create(
                            event=event,
                            platform=plat,
                            language=language,
                            defaults={
                                "is_live_stream": is_live,
                                "vod_available": vod,
                                "commentary_region": (
                                    "Latin America" if language == LA else ""
                                ),
                            },
                        )
                        comp_broadcasts += 1

            total_imported += comp_imported
            total_broadcasts += comp_broadcasts
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ {comp_imported} events imported, {comp_broadcasts} broadcasts assigned."
                )
            )

            # Pause between TheSportsDB calls to respect the rate limit
            if source == "thesportsdb":
                time.sleep(2)

        self.stdout.write(
            "\n" + self.style.SUCCESS(
                f"✅ Import complete: {total_imported} total events, "
                f"{total_broadcasts} broadcasts assigned."
            )
        )
