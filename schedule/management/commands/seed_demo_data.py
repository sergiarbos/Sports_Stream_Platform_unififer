"""
Demo command: creates sports, competitions, platforms and sample events
so the project runs locally without needing to configure any real API yet.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --flush   (wipes and recreates everything)
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from schedule.models import Broadcast, Competition, Event, Platform, Sport


class Command(BaseCommand):
    help = "Creates sample data (sports, competitions, platforms and events) for local development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all app data before recreating it.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Deleting existing schedule data...")
            Broadcast.objects.all().delete()
            Event.objects.all().delete()
            Competition.objects.all().delete()
            Platform.objects.all().delete()
            Sport.objects.all().delete()

        now = timezone.now()

        # ------------------------------------------------------------------
        # 1. Sports
        # ------------------------------------------------------------------
        sports = {}
        for slug, name, category, icon, order in [
            ("futbol", "Fútbol", Sport.CATEGORY_FOOTBALL, "⚽", 1),
            ("baloncesto", "Baloncesto", Sport.CATEGORY_BASKETBALL, "🏀", 2),
            ("motor", "Motor", Sport.CATEGORY_MOTORSPORT, "🏎️", 3),
            ("tenis", "Tenis", Sport.CATEGORY_TENNIS, "🎾", 4),
            ("invierno", "Deportes de invierno", Sport.CATEGORY_WINTER, "❄️", 5),
        ]:
            sport, _ = Sport.objects.update_or_create(
                slug=slug, defaults={"name": name, "category": category, "icon": icon, "order": order}
            )
            sports[slug] = sport

        # ------------------------------------------------------------------
        # 2. Competitions
        # ------------------------------------------------------------------
        competitions = {}
        comp_data = [
            ("champions-league", "UEFA Champions League", "futbol", "thesportsdb"),
            ("europa-league", "UEFA Europa League", "futbol", "thesportsdb"),
            ("mundial-2026", "Copa Mundial 2026", "futbol", "thesportsdb"),
            ("la-liga", "LaLiga", "futbol", "thesportsdb"),
            ("premier-league", "Premier League", "futbol", "thesportsdb"),
            ("serie-a", "Serie A", "futbol", "thesportsdb"),
            ("bundesliga", "Bundesliga", "futbol", "thesportsdb"),
            ("ligue-1", "Ligue 1", "futbol", "thesportsdb"),
            ("nba", "NBA", "baloncesto", "thesportsdb"),
            ("f1", "Fórmula 1", "motor", "jolpica_f1"),
            ("motogp", "MotoGP", "motor", "thesportsdb"),
            ("wimbledon", "Wimbledon", "tenis", "thesportsdb"),
            ("esqui-alpino", "Copa del Mundo de Esquí Alpino", "invierno", "manual"),
            ("salto-esqui", "Copa del Mundo de Salto de Esquí", "invierno", "manual"),
            ("esqui-fondo", "Copa del Mundo de Esquí de Fondo", "invierno", "manual"),
        ]
        for slug, name, sport_slug, source in comp_data:
            comp, _ = Competition.objects.update_or_create(
                slug=slug, defaults={"name": name, "sport": sports[sport_slug], "source": source}
            )
            competitions[slug] = comp

        # ------------------------------------------------------------------
        # 3. Platforms
        # ------------------------------------------------------------------
        platforms = {}
        plat_data = [
            ("dazn", "DAZN", "#00B2FF", True),
            ("movistar-plus", "Movistar Plus+", "#0033A0", True),
            ("espn", "ESPN", "#D6001C", True),
            ("vix", "ViX", "#00C2CB", True),
            ("eurosport", "Eurosport", "#003DA5", True),
            ("rtve-play", "RTVE Play", "#E30613", False),
            ("bein-sports", "beIN Sports", "#6A1B9A", True),
        ]
        for slug, name, color, sub in plat_data:
            plat, _ = Platform.objects.update_or_create(
                slug=slug, defaults={"name": name, "color": color, "requires_subscription": sub}
            )
            platforms[slug] = plat

        # ------------------------------------------------------------------
        # 4. Events + broadcasts
        # ------------------------------------------------------------------
        # Each tuple: (competition, title, round, hours_delta_from_now, status, [broadcasts])
        # broadcast = (platform, language, is_live_stream, vod_available)
        ES, LA = Broadcast.LANGUAGE_ES_ES, Broadcast.LANGUAGE_ES_LA

        events_data = [
            # --- LIVE ---
            (
                "mundial-2026", "Argentina vs Francia", "Round of 16", -0.5, Event.STATUS_LIVE,
                [("dazn", ES, True, False), ("vix", LA, True, False)],
            ),
            (
                "wimbledon", "Carlos Alcaraz vs Novak Djokovic", "Quarter-finals", -0.3, Event.STATUS_LIVE,
                [("movistar-plus", ES, True, False)],
            ),
            (
                "motogp", "Dutch GP Qualifying", "Q2", -0.2, Event.STATUS_LIVE,
                [("dazn", ES, True, False)],
            ),
            # --- UPCOMING ---
            (
                "champions-league", "Real Madrid vs Manchester City", "Round of 16 draw", 48, Event.STATUS_SCHEDULED,
                [("movistar-plus", ES, True, False), ("vix", LA, True, False)],
            ),
            (
                "la-liga", "FC Barcelona vs Atlético de Madrid", "Matchday 1", 96, Event.STATUS_SCHEDULED,
                [("dazn", ES, True, False)],
            ),
            (
                "premier-league", "Liverpool vs Arsenal", "Matchday 1", 120, Event.STATUS_SCHEDULED,
                [("dazn", ES, True, False)],
            ),
            (
                "nba", "Boston Celtics vs Denver Nuggets", "Pre-season", 72, Event.STATUS_SCHEDULED,
                [("vix", LA, True, False), ("espn", ES, True, False)],
            ),
            (
                "f1", "British Grand Prix", "Race", 30, Event.STATUS_SCHEDULED,
                [("dazn", ES, True, False)],
            ),
            (
                "motogp", "Dutch GP Race", "Race", 6, Event.STATUS_SCHEDULED,
                [("dazn", ES, True, False)],
            ),
            (
                "wimbledon", "Women's Final", "Final", 168, Event.STATUS_SCHEDULED,
                [("movistar-plus", ES, True, False), ("eurosport", ES, True, False)],
            ),
            (
                "esqui-alpino", "Sölden Giant Slalom (pre-season)", "Single run", 240, Event.STATUS_SCHEDULED,
                [("eurosport", ES, True, False)],
            ),
            (
                "salto-esqui", "Summer Grand Prix - Ski Jump", "Individual", 200, Event.STATUS_SCHEDULED,
                [("rtve-play", ES, True, False)],
            ),
            (
                "europa-league", "Real Sociedad vs AS Roma", "League phase", 144, Event.STATUS_SCHEDULED,
                [("movistar-plus", ES, True, False)],
            ),
            # --- PAST WITH VOD (should be visible) ---
            (
                "mundial-2026", "Spain vs Brazil", "Group stage", -72, Event.STATUS_FINISHED,
                [("dazn", ES, False, True), ("vix", LA, False, True)],
            ),
            (
                "f1", "Monaco Grand Prix", "Race", -240, Event.STATUS_FINISHED,
                [("dazn", ES, False, True)],
            ),
            (
                "esqui-fondo", "Holmenkollen 50km", "Distance", -480, Event.STATUS_FINISHED,
                [("rtve-play", ES, False, True), ("eurosport", ES, False, True)],
            ),
            (
                "serie-a", "Juventus vs Inter Milan", "Matchday 30", -120, Event.STATUS_FINISHED,
                [("bein-sports", ES, False, True)],
            ),
            # --- PAST WITHOUT VOD (should NOT be visible) ---
            (
                "bundesliga", "Bayern Munich vs Borussia Dortmund", "Matchday 28", -96, Event.STATUS_FINISHED,
                [("dazn", ES, False, False)],
            ),
            (
                "ligue-1", "PSG vs Olympique de Marseille", "Matchday 29", -100, Event.STATUS_FINISHED,
                [],  # no Spanish broadcast → hidden
            ),
        ]

        created = 0
        for comp_slug, title, round_name, hours_delta, status, broadcasts in events_data:
            start = now + timedelta(hours=hours_delta)
            event, _ = Event.objects.update_or_create(
                competition=competitions[comp_slug],
                title=title,
                start_datetime=start,
                defaults={"status": status, "round_name": round_name},
            )
            event.broadcasts.all().delete()
            for plat_slug, language, is_live, vod in broadcasts:
                Broadcast.objects.create(
                    event=event,
                    platform=platforms[plat_slug],
                    language=language,
                    is_live_stream=is_live,
                    vod_available=vod,
                    commentary_region="Latin America" if language == LA else "",
                )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Sample data ready: {created} events created/updated."))
