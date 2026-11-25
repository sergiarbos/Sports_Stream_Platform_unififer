"""
Unit tests for the schedule app.
Covers the core business rules and the home view.
"""

import datetime
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Broadcast, Competition, Event, Platform, Sport
from .utils import (
    broadcast_meta,
    categorize_event,
    competition_flag,
    filter_events,
    live_minute,
    mark_competition_sections,
    platform_code,
    result_detail,
    short_team_name,
    team_colors,
    team_initials,
    team_text_style,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_sport():
    return Sport.objects.create(
        name="Football", slug="football", category=Sport.CATEGORY_FOOTBALL, order=0
    )


def make_competition(sport):
    return Competition.objects.create(sport=sport, name="Champions League", slug="champions")


def make_platform():
    return Platform.objects.create(
        name="DAZN", slug="dazn", website_url="https://dazn.com", color="#000"
    )


def make_event(comp, hours_delta=3, status=Event.STATUS_SCHEDULED):
    return Event.objects.create(
        competition=comp,
        title="Test Match",
        start_datetime=timezone.now() + timedelta(hours=hours_delta),
        status=status,
    )


def make_broadcast(event, platform, vod=False):
    return Broadcast.objects.create(
        event=event,
        platform=platform,
        language=Broadcast.LANGUAGE_ES_ES,
        vod_available=vod,
    )


class StatusLabelTest(TestCase):
    def setUp(self):
        self.comp = make_competition(make_sport())

    def test_live(self):
        self.assertEqual(make_event(self.comp, status=Event.STATUS_LIVE).status_label, "LIVE")

    def test_finished(self):
        self.assertEqual(
            make_event(self.comp, status=Event.STATUS_FINISHED).status_label, "ON DEMAND"
        )

    def test_scheduled(self):
        self.assertEqual(
            make_event(self.comp, status=Event.STATUS_SCHEDULED).status_label, "UPCOMING"
        )


class HomeViewTest(TestCase):
    def setUp(self):
        sport = make_sport()
        comp = make_competition(sport)
        platform = make_platform()
        self.event = make_event(comp, hours_delta=+3)
        make_broadcast(self.event, platform)

    def test_returns_200(self):
        response = self.client.get(reverse("schedule:home"))
        self.assertEqual(response.status_code, 200)

    def test_upcoming_event_appears_in_context(self):
        response = self.client.get(reverse("schedule:home"))
        self.assertIn(self.event, response.context["upcoming_events"])

    def test_event_beyond_30_days_is_excluded(self):
        comp = Competition.objects.get(slug="champions")
        platform = Platform.objects.get(slug="dazn")
        far_event = Event.objects.create(
            competition=comp,
            title="Far future final",
            start_datetime=timezone.now() + timedelta(days=35),
            status=Event.STATUS_SCHEDULED,
        )
        make_broadcast(far_event, platform)
        response = self.client.get(reverse("schedule:home"))
        self.assertNotIn(far_event, response.context["upcoming_events"])


class CompetitionFilterTest(TestCase):
    def setUp(self):
        sport = make_sport()
        self.la_liga = Competition.objects.create(
            sport=sport, name="LaLiga", slug="la-liga", short_code="LL"
        )
        self.champions = make_competition(sport)
        platform = make_platform()
        self.la_liga_event = make_event(self.la_liga, hours_delta=+3)
        self.champions_event = make_event(self.champions, hours_delta=+5)
        make_broadcast(self.la_liga_event, platform)
        make_broadcast(self.champions_event, platform)

    def test_competitions_are_shown_only_for_a_selected_sport(self):
        response = self.client.get(reverse("schedule:home"), {"sport": "football"})
        self.assertIn(self.la_liga, response.context["competitions"])
        self.assertIn(self.champions, response.context["competitions"])
        self.assertContains(response, "COMPETICIÓN")
        self.assertContains(response, "LaLiga")

        response = self.client.get(reverse("schedule:home"))
        self.assertFalse(response.context["competitions"].exists())
        self.assertNotContains(response, "COMPETICIÓN")

    def test_competition_filter_limits_events(self):
        response = self.client.get(
            reverse("schedule:home"), {"sport": "football", "competition": "la-liga"}
        )
        self.assertIn(self.la_liga_event, response.context["upcoming_events"])
        self.assertNotIn(self.champions_event, response.context["upcoming_events"])

    def test_filter_links_keep_sport_platform_and_competition(self):
        response = self.client.get(
            reverse("schedule:home"),
            {"sport": "football", "platform": "dazn", "competition": "la-liga"},
        )
        self.assertContains(response, "sport=football&amp;platform=dazn&amp;competition=all")
        self.assertContains(response, "sport=football&amp;platform=dazn&amp;competition=la-liga")

    def test_competition_filter_also_applies_to_results(self):
        finished = Event.objects.create(
            competition=self.la_liga,
            title="Finished match",
            start_datetime=timezone.now() - timedelta(hours=5),
            status=Event.STATUS_FINISHED,
            score_home=2,
            score_away=1,
        )
        make_broadcast(finished, Platform.objects.get(slug="dazn"))

        response = self.client.get(
            reverse("schedule:home"),
            {"view_mode": "results", "sport": "football", "competition": "la-liga"},
        )
        self.assertIn(finished, response.context["results_events"])
        self.assertNotContains(response, "Test Match")


class TeamPresentationTest(TestCase):
    def test_short_names_initials_and_colors(self):
        cases = (
            ("FC Barcelona", "Barcelona", "FCB"),
            ("Real Madrid", "Real Madrid", "RM"),
            ("Inter de Milán", "Inter", "INT"),
            ("PSG", "PSG", "PSG"),
            ("Club Atlético de Madrid", "Atlético", "ATM"),
            ("Sabah FK", "Sabah FK", "SF"),
            ("VfB Stuttgart", "VfB Stuttgart", "VFB"),
            ("Viking FK", "Viking FK", "VF"),
            ("PSV", "PSV", "PSV"),
            ("SSC Napoli", "SSC Napoli", "SSC"),
            ("SK Slovan Bratislava", "SK Slovan", "SKS"),
            ("SK Slavia Praha", "SK Slavia Praha", "SLA"),
            ("Villarreal", "Villarreal", "VIL"),
        )
        for full, short, code in cases:
            self.assertEqual(short_team_name(full), short)
            self.assertEqual(team_initials(full), code)
            self.assertLessEqual(len(code), 3)

        self.assertIn("#a50044", team_colors("FC Barcelona"))
        self.assertIn("#d4af37", team_colors("Real Madrid"))
        self.assertIn("--team-text: #0a0a0a", team_colors("Villarreal"))
        self.assertIn("--team-text: #ffffff", team_colors("FC Barcelona"))
        self.assertEqual(team_text_style("Villarreal")[0], "#0a0a0a")

    def test_competition_flags(self):
        self.assertEqual(competition_flag("champions-league"), "🇪🇺")
        self.assertEqual(competition_flag("la-liga"), "🇪🇸")
        self.assertEqual(competition_flag("unknown-league"), "")

    def test_platform_codes_and_broadcast_metadata(self):
        sport = make_sport()
        comp = make_competition(sport)
        event = make_event(comp, hours_delta=1)

        dazn = make_platform()
        self.assertEqual(platform_code(dazn), "DAZN")
        self.assertIn("SUSCRIPCIÓN", broadcast_meta(make_broadcast(event, dazn)))

        rtve = Platform.objects.create(
            name="RTVE Play",
            slug="rtve-play",
            color="#e30613",
            website_url="https://www.rtve.es/play",
            requires_subscription=False,
        )
        self.assertIn("EN ABIERTO", broadcast_meta(make_broadcast(event, rtve)))

        movistar = Platform.objects.create(
            name="Movistar Plus+",
            slug="movistar-plus",
            color="#0033a0",
            website_url="https://www.movistarplus.es",
            requires_subscription=True,
        )
        self.assertIn("M+ CL", broadcast_meta(make_broadcast(event, movistar)))

    def test_live_minute_and_result_detail(self):
        sport = make_sport()
        comp = make_competition(sport)

        live = make_event(comp, status=Event.STATUS_LIVE)
        live.start_datetime = timezone.now() - timedelta(minutes=64)
        live.save()
        minute = int(live_minute(live).rstrip("'"))
        self.assertIn(minute, (63, 64, 65))
        self.assertEqual(live_minute(make_event(comp)), "")

        finished = make_event(comp, status=Event.STATUS_FINISHED)
        finished.result_text = "Pen. 4-3"
        finished.save()
        self.assertIn("PEN.", result_detail(finished))

    def test_competition_section_grouping(self):
        sport = make_sport()
        comp = make_competition(sport)
        first = make_event(comp, hours_delta=+3)
        first.round_name = "Jornada 5"
        second = make_event(comp, hours_delta=+4)
        second.round_name = "Jornada 5"
        other = Competition.objects.create(sport=sport, name="LaLiga", slug="la-liga")
        third = make_event(other, hours_delta=+5)

        mark_competition_sections([first, second, third])

        self.assertTrue(first.is_competition_start)
        self.assertFalse(second.is_competition_start)
        self.assertTrue(third.is_competition_start)
        self.assertIn("🇪🇺", first.competition_section_label)
        self.assertIn("JORNADA 5", first.competition_section_label)


class ListPresentationTest(TestCase):
    def setUp(self):
        sport = make_sport()
        comp = make_competition(sport)
        platform = make_platform()
        pairs = (
            ("FC Internazionale Milano", "Slavia Praga"),
            ("FC Barcelona", "PSG"),
        )
        for index, (home, away) in enumerate(pairs):
            event = make_event(comp, hours_delta=+26 + index)
            event.title = f"{home} vs {away}"
            event.participant_home = home
            event.participant_away = away
            event.round_name = "Jornada 5"
            event.save()
            make_broadcast(event, platform)

    def test_schedule_rows_use_short_names_tooltips_and_competition_header(self):
        response = self.client.get(reverse("schedule:home"), {"sport": "football"})
        html = response.content.decode()

        self.assertEqual(html.count('class="competition-subheader"'), 1)
        self.assertContains(response, 'Inter <span class="vs-sep">vs</span> SK Slavia Praha')
        self.assertContains(response, 'title="FC Internazionale Milano vs Slavia Praga"')
        self.assertContains(response, "FCB")
        self.assertContains(response, "platform-hint")
        self.assertContains(response, 'class="search-shortcut"')
        self.assertNotContains(response, "VER EMISIONES")

    def test_results_use_minimal_detail_icon(self):
        finished = Event.objects.create(
            competition=Competition.objects.get(slug="champions"),
            title="FC Barcelona vs PSG",
            participant_home="FC Barcelona",
            participant_away="PSG",
            start_datetime=timezone.now() - timedelta(hours=5),
            status=Event.STATUS_FINISHED,
            score_home=2,
            score_away=1,
        )
        make_broadcast(finished, Platform.objects.get(slug="dazn"))

        response = self.client.get(
            reverse("schedule:home"), {"view_mode": "results", "sport": "football"}
        )
        self.assertContains(response, 'class="result-open"')
        self.assertNotContains(response, "DETALLES")

    def test_rows_do_not_repeat_competition_subtitle(self):
        response = self.client.get(reverse("schedule:home"), {"sport": "football"})
        html = response.content.decode()
        self.assertNotIn("schedule-row-comp", html)
        self.assertNotIn("result-comp", html)

    def test_live_row_shows_minute_score_and_platform_codes(self):
        comp = Competition.objects.get(slug="champions")
        live = make_event(comp, hours_delta=-1, status=Event.STATUS_LIVE)
        live.title = "Live Match"
        live.score_home = 1
        live.score_away = 0
        live.save()
        make_broadcast(live, Platform.objects.get(slug="dazn"))

        response = self.client.get(reverse("schedule:home"), {"sport": "football"})
        html = response.content.decode()
        self.assertIn("live-time", html)
        self.assertIn("live-score", html)
        self.assertIn("platform-hint-code", html)
        upcoming_row = html[
            html.index('data-event-id="event-1"') : html.index('data-event-id="event-2"')
        ]
        self.assertLess(upcoming_row.index("reminder-bell-btn"), upcoming_row.index("row-open"))

    def test_date_navigation_and_panel_placeholder_summary(self):
        comp = Competition.objects.get(slug="champions")
        platform = Platform.objects.get(slug="dazn")
        extra = make_event(comp, hours_delta=+50)
        extra.title = "Extra Match"
        extra.participant_home = "PSG"
        extra.participant_away = "Villarreal"
        extra.save()
        make_broadcast(extra, platform)

        response = self.client.get(reverse("schedule:home"), {"sport": "football"})
        html = response.content.decode()
        self.assertIn("date-nav", html)
        self.assertIn("date-pill", html)
        self.assertIn('id="date-', html)
        self.assertIn("placeholder-open", html)

    def test_motorsport_results_use_single_event_layout(self):
        sport = Sport.objects.create(
            name="Motor",
            slug="motor",
            category=Sport.CATEGORY_MOTORSPORT,
            icon="🏁",
            order=1,
        )
        comp = Competition.objects.create(sport=sport, name="Fórmula 1", slug="f1", short_code="F1")
        event = make_event(comp, hours_delta=-5, status=Event.STATUS_FINISHED)
        event.title = "GP de Abu Dabi · Carrera"
        event.result_text = "1º Verstappen, 2º Norris, 3º Leclerc"
        event.save()

        response = self.client.get(
            reverse("schedule:home"), {"view_mode": "results", "sport": "motor"}
        )
        html = response.content.decode()
        self.assertIn("result-single", html)
        self.assertIn("result-top3", html)
        self.assertIn("result-when", html)
        self.assertNotIn("result-score", html)


class MobileApiTest(TestCase):
    def setUp(self):
        sport = make_sport()
        comp = make_competition(sport)
        platform = make_platform()
        self.event = make_event(comp, hours_delta=+3)
        make_broadcast(self.event, platform)

    def test_mobile_events_api_returns_visible_events_json(self):
        response = self.client.get(reverse("schedule:events_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("events", payload)
        self.assertTrue(any(event["id"] == self.event.id for event in payload["events"]))


class DateTimeFilterTest(TestCase):
    def setUp(self):
        self.sport = make_sport()
        self.comp = make_competition(self.sport)

    @patch("schedule.utils.timezone.now")
    def test_categorize_event_today_tomorrow_live(self, mock_now):
        fixed_now = datetime.datetime(2026, 7, 1, 12, 0, tzinfo=datetime.UTC)
        mock_now.return_value = fixed_now

        live_event = make_event(self.comp, status=Event.STATUS_LIVE)
        self.assertEqual(categorize_event(live_event), "Live")

        today_event = Event.objects.create(
            competition=self.comp,
            title="Today Match",
            start_datetime=fixed_now + timedelta(hours=2),
            status=Event.STATUS_SCHEDULED,
        )
        self.assertEqual(categorize_event(today_event), "Today")

        tomorrow_event = Event.objects.create(
            competition=self.comp,
            title="Tomorrow Match",
            start_datetime=fixed_now + timedelta(days=1, hours=2),
            status=Event.STATUS_SCHEDULED,
        )
        self.assertEqual(categorize_event(tomorrow_event), "Tomorrow")

        other_event = Event.objects.create(
            competition=self.comp,
            title="Other Match",
            start_datetime=fixed_now + timedelta(days=3),
            status=Event.STATUS_SCHEDULED,
        )
        self.assertIsNone(categorize_event(other_event))

    @patch("schedule.utils.timezone.now")
    def test_timezone_offsets(self, mock_now):
        fixed_utc_now = datetime.datetime(2026, 7, 1, 23, 0, tzinfo=datetime.UTC)
        mock_now.return_value = fixed_utc_now

        event = Event.objects.create(
            competition=self.comp,
            title="Late Match",
            start_datetime=fixed_utc_now + timedelta(hours=1, minutes=30),
            status=Event.STATUS_SCHEDULED,
        )

        # 1. Test UTC
        # Event is at 00:30 next day UTC -> "Tomorrow"
        with timezone.override("UTC"):
            self.assertEqual(categorize_event(event), "Tomorrow")

        # 2. Test CET (Europe/Madrid)
        # Now is 01:00 on 2nd July. Event is at 02:30 on 2nd July -> "Today"
        with timezone.override("Europe/Madrid"):
            self.assertEqual(categorize_event(event), "Today")

        # 3. Test EST (America/New_York)
        # Now is 18:00 on 1st July. Event is at 20:30 on 1st July -> "Today"
        with timezone.override("America/New_York"):
            self.assertEqual(categorize_event(event), "Today")

    @patch("schedule.utils.timezone.now")
    def test_filter_events_helper(self, mock_now):
        fixed_now = datetime.datetime(2026, 7, 1, 12, 0, tzinfo=datetime.UTC)
        mock_now.return_value = fixed_now

        live_event = make_event(self.comp, status=Event.STATUS_LIVE)
        today_event = Event.objects.create(
            competition=self.comp,
            title="Today Match",
            start_datetime=fixed_now + timedelta(hours=2),
            status=Event.STATUS_SCHEDULED,
        )
        tomorrow_event = Event.objects.create(
            competition=self.comp,
            title="Tomorrow Match",
            start_datetime=fixed_now + timedelta(days=1),
            status=Event.STATUS_SCHEDULED,
        )

        events = [live_event, today_event, tomorrow_event]

        with timezone.override("UTC"):
            self.assertListEqual(filter_events(events, "Live"), [live_event])
            self.assertListEqual(filter_events(events, "Today"), [today_event])
            self.assertListEqual(filter_events(events, "Tomorrow"), [tomorrow_event])
