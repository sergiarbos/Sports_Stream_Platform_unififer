"""
Demo seeder: creates sports, competitions, platforms, and sample events
so the project works locally without needing to configure any real API.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --flush   (wipes and recreates everything)
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from schedule.models import Broadcast, Competition, Event, Platform, Sport


class Command(BaseCommand):
    help = "Creates sample data (sports, competitions, platforms and events) for local development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Deletes all app data before recreating it.",
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
                slug=slug,
                defaults={"name": name, "category": category, "icon": icon, "order": order},
            )
            sports[slug] = sport

        # ------------------------------------------------------------------
        # 2. Competitions
        # ------------------------------------------------------------------
        competitions = {}
        comp_data = [
            ("champions-league", "UEFA Champions League", "CL", "futbol", "api_football"),
            ("europa-league", "UEFA Europa League", "EL", "futbol", "api_football"),
            ("mundial-2026", "Copa Mundial 2026", "WC", "futbol", "api_football"),
            ("la-liga", "LaLiga", "LL", "futbol", "api_football"),
            ("premier-league", "Premier League", "PL", "futbol", "api_football"),
            ("serie-a", "Serie A", "SA", "futbol", "api_football"),
            ("bundesliga", "Bundesliga", "BL", "futbol", "api_football"),
            ("ligue-1", "Ligue 1", "L1", "futbol", "api_football"),
            ("nba", "NBA", "NBA", "baloncesto", "thesportsdb"),
            ("f1", "Fórmula 1", "F1", "motor", "jolpica_f1"),
            ("motogp", "MotoGP", "MGP", "motor", "thesportsdb"),
            ("wimbledon", "Wimbledon", "WIM", "tenis", "api_tennis"),
            ("esqui-alpino", "Copa del Mundo de Esquí Alpino", "ALP", "invierno", "manual"),
            ("salto-esqui", "Copa del Mundo de Salto de Esquí", "SAL", "invierno", "manual"),
            ("esqui-fondo", "Copa del Mundo de Esquí de Fondo", "FON", "invierno", "manual"),
        ]
        for slug, name, short_code, sport_slug, source in comp_data:
            comp, _ = Competition.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "short_code": short_code,
                    "sport": sports[sport_slug],
                    "source": source,
                },
            )
            competitions[slug] = comp

        # ------------------------------------------------------------------
        # 3. Platforms
        # ------------------------------------------------------------------
        platforms = {}
        plat_data = [
            ("dazn", "DAZN", "#00B2FF", True, "https://www.dazn.com"),
            ("movistar-plus", "Movistar Plus+", "#0033A0", True, "https://www.movistarplus.es"),
            ("espn", "ESPN", "#D6001C", True, "https://www.espn.com"),
            ("vix", "ViX", "#00C2CB", True, "https://vix.com"),
            ("eurosport", "Eurosport", "#003DA5", True, "https://www.eurosport.es"),
            ("rtve-play", "RTVE Play", "#E30613", False, "https://www.rtve.es/play"),
            ("bein-sports", "beIN Sports", "#6A1B9A", True, "https://www.beinsports.com"),
        ]
        for slug, name, color, sub, website in plat_data:
            plat, _ = Platform.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "color": color,
                    "requires_subscription": sub,
                    "website_url": website,
                },
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
                "mundial-2026",
                "Argentina vs Francia",
                "Round of 16",
                -0.5,
                Event.STATUS_LIVE,
                [("dazn", ES, True, False), ("vix", LA, True, False)],
            ),
            (
                "wimbledon",
                "Carlos Alcaraz vs Novak Djokovic",
                "Quarter-finals",
                -0.3,
                Event.STATUS_LIVE,
                [("movistar-plus", ES, True, False)],
            ),
            (
                "motogp",
                "Dutch GP Qualifying",
                "Q2",
                -0.2,
                Event.STATUS_LIVE,
                [("dazn", ES, True, False)],
            ),
            # --- UPCOMING ---
            (
                "la-liga",
                "FC Barcelona vs Atlético de Madrid",
                "Matchday 1",
                96,
                Event.STATUS_SCHEDULED,
                [("dazn", ES, True, False)],
            ),
            (
                "premier-league",
                "Liverpool vs Arsenal",
                "Matchday 1",
                120,
                Event.STATUS_SCHEDULED,
                [("dazn", ES, True, False)],
            ),
            (
                "nba",
                "Boston Celtics vs Denver Nuggets",
                "Preseason",
                72,
                Event.STATUS_SCHEDULED,
                [("vix", LA, True, False), ("espn", ES, True, False)],
            ),
            (
                "f1",
                "British Grand Prix",
                "Race",
                30,
                Event.STATUS_SCHEDULED,
                [("dazn", ES, True, False)],
            ),
            (
                "motogp",
                "Dutch GP Race",
                "Race",
                6,
                Event.STATUS_SCHEDULED,
                [("dazn", ES, True, False)],
            ),
            (
                "wimbledon",
                "Women's Final",
                "Final",
                168,
                Event.STATUS_SCHEDULED,
                [("movistar-plus", ES, True, False), ("eurosport", ES, True, False)],
            ),
            (
                "esqui-alpino",
                "Sölden Giant Slalom (preseason)",
                "Single run",
                240,
                Event.STATUS_SCHEDULED,
                [("eurosport", ES, True, False)],
            ),
            (
                "salto-esqui",
                "Summer Grand Prix - Ski Jump",
                "Individual",
                200,
                Event.STATUS_SCHEDULED,
                [("rtve-play", ES, True, False)],
            ),
            (
                "europa-league",
                "Real Sociedad vs AS Roma",
                "League stage",
                144,
                Event.STATUS_SCHEDULED,
                [("movistar-plus", ES, True, False)],
            ),
            # --- PAST WITH REPLAY, WITHIN THE LAST 7 DAYS (should be visible) ---
            (
                "mundial-2026",
                "España vs Brasil",
                "Group stage",
                -72,
                Event.STATUS_FINISHED,
                [("dazn", ES, False, True), ("vix", LA, False, True)],
            ),
            (
                "serie-a",
                "Juventus vs Inter de Milán",
                "Matchday 30",
                -120,
                Event.STATUS_FINISHED,
                [("bein-sports", ES, False, True)],
            ),
            # --- PAST WITH REPLAY BUT EXPIRED (>7 days, should NOT be visible) ---
            (
                "f1",
                "Monaco Grand Prix",
                "Race",
                -240,
                Event.STATUS_FINISHED,
                [("dazn", ES, False, True)],
            ),
            (
                "esqui-fondo",
                "Holmenkollen 50km",
                "Distance",
                -480,
                Event.STATUS_FINISHED,
                [("rtve-play", ES, False, True), ("eurosport", ES, False, True)],
            ),
            # --- PAST WITHOUT REPLAY (should NOT be visible regardless of date) ---
            (
                "bundesliga",
                "Bayern Múnich vs Borussia Dortmund",
                "Matchday 28",
                -96,
                Event.STATUS_FINISHED,
                [("dazn", ES, False, False)],
            ),
            (
                "ligue-1",
                "PSG vs Olympique de Marsella",
                "Matchday 29",
                -100,
                Event.STATUS_FINISHED,
                [],  # no Spanish broadcast -> hidden
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
            event_slug = slugify(title)[:60]
            for plat_slug, language, is_live, vod in broadcasts:
                platform = platforms[plat_slug]
                # Deep link example pointing directly to THIS event on THIS platform.
                # In production this will come from each source API (api_football, jolpica_f1...).
                direct_link = f"{platform.website_url}/es/evento/{event.pk or 'x'}-{event_slug}"
                Broadcast.objects.create(
                    event=event,
                    platform=platform,
                    language=language,
                    is_live_stream=is_live,
                    event_url=direct_link if is_live else "",
                    vod_available=vod,
                    vod_url=direct_link if vod else "",
                    commentary_region="Latin America" if language == LA else "",
                )
            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Sample data ready: {created} events created/updated.")
        )
