import datetime
import json

import responses as resp
from django.test import TestCase, override_settings
from django.utils import timezone

from schedule.services.api_football import ApiFootballAdapter
from schedule.services.jolpica_f1 import JolpicaF1Adapter
from schedule.services.thesportsdb import TheSportsDBAdapter

JOLPICA_RACES_URL = "https://api.jolpi.ca/ergast/f1/2026/races/?format=json"
JOLPICA_RESULTS_URL = "https://api.jolpi.ca/ergast/f1/2026/results/?format=json"

JOLPICA_RACE_FIXTURE = {
    "MRData": {
        "RaceTable": {
            "Races": [
                {
                    "season": "2026",
                    "round": "1",
                    "raceName": "Bahrain Grand Prix",
                    "date": "2026-03-02",
                    "time": "15:00:00Z",
                    "FirstPractice": {"date": "2026-02-28", "time": "11:30:00Z"},
                    "Qualifying": {"date": "2026-03-01", "time": "14:00:00Z"},
                }
            ]
        }
    }
}

JOLPICA_RESULTS_FIXTURE = {
    "MRData": {
        "RaceTable": {
            "Races": [
                {
                    "round": "1",
                    "Results": [
                        {"position": "1", "Driver": {"familyName": "Verstappen"}},
                        {"position": "2", "Driver": {"familyName": "Norris"}},
                        {"position": "3", "Driver": {"familyName": "Leclerc"}},
                    ],
                }
            ]
        }
    }
}

TSDB_EVENTS_FIXTURE = [
    {
        "idEvent": "1234567",
        "strEvent": "Real Madrid vs Barcelona",
        "strHomeTeam": "Real Madrid",
        "strAwayTeam": "Barcelona",
        "dateEvent": "2026-10-25",
        "strTime": "20:00:00",
        "strStatus": "NS",
        "intRound": "10",
    },
    {
        "idEvent": "1234568",
        "strEvent": "Atletico vs Sevilla",
        "strHomeTeam": "Atletico",
        "strAwayTeam": "Sevilla",
        "dateEvent": "2026-09-01",
        "strTime": "18:00:00",
        "strStatus": "FT",
        "intHomeScore": 2,
        "intRound": "5",
    },
]

API_FOOTBALL_FIXTURE = {
    "response": [
        {
            "fixture": {
                "id": 999001,
                "timestamp": 1769436000,
                "status": {"short": "NS"},
            },
            "teams": {
                "home": {"name": "Manchester City"},
                "away": {"name": "Arsenal"},
            },
            "goals": {"home": None, "away": None},
        }
    ]
}


@override_settings(
    API_CACHE_TTL=0, CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
)
class TestJolpicaF1Adapter(TestCase):
    """
    Verifies that JolpicaF1Adapter correctly parses the API response
    into a list of event dicts without making real HTTP requests.
    """

    @resp.activate
    def test_fetch_events_returns_race_and_sessions(self):
        resp.add(resp.GET, JOLPICA_RACES_URL, json=JOLPICA_RACE_FIXTURE, status=200)
        resp.add(resp.GET, JOLPICA_RESULTS_URL, json=JOLPICA_RESULTS_FIXTURE, status=200)

        adapter = JolpicaF1Adapter()
        events = adapter.fetch_events(season="2026")

        # Should have the main race + FP1 + Qualifying = 3 events
        self.assertEqual(len(events), 3)

        titles = [e["title"] for e in events]
        self.assertIn("Bahrain Grand Prix", titles)
        self.assertTrue(any("Free Practice 1" in t for t in titles))
        self.assertTrue(any("Qualifying" in t for t in titles))

    @resp.activate
    def test_race_external_id_format(self):
        resp.add(resp.GET, JOLPICA_RACES_URL, json=JOLPICA_RACE_FIXTURE, status=200)
        resp.add(resp.GET, JOLPICA_RESULTS_URL, json=JOLPICA_RESULTS_FIXTURE, status=200)

        adapter = JolpicaF1Adapter()
        events = adapter.fetch_events(season="2026")

        race = next(e for e in events if e["title"] == "Bahrain Grand Prix")
        self.assertEqual(race["external_id"], "f1-2026-1-race")
        self.assertIsNotNone(race["start_datetime"])
        self.assertIn(race["status"], ("scheduled", "finished"))

    @resp.activate
    def test_result_text_populated(self):
        resp.add(resp.GET, JOLPICA_RACES_URL, json=JOLPICA_RACE_FIXTURE, status=200)
        resp.add(resp.GET, JOLPICA_RESULTS_URL, json=JOLPICA_RESULTS_FIXTURE, status=200)

        adapter = JolpicaF1Adapter()
        events = adapter.fetch_events(season="2026")

        race = next(e for e in events if e["title"] == "Bahrain Grand Prix")
        self.assertIn("Verstappen", race.get("result_text", ""))

    @resp.activate
    def test_handles_results_api_error_gracefully(self):
        """Results endpoint failure should not prevent races from being returned."""
        resp.add(resp.GET, JOLPICA_RACES_URL, json=JOLPICA_RACE_FIXTURE, status=200)
        resp.add(resp.GET, JOLPICA_RESULTS_URL, body=Exception("Connection error"))

        adapter = JolpicaF1Adapter()
        events = adapter.fetch_events(season="2026")
        self.assertGreater(len(events), 0)


@override_settings(
    API_CACHE_TTL=0, CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
)
class TestTheSportsDBAdapter(TestCase):
    """
    Verifies TheSportsDBAdapter: date parsing, deduplication, status mapping.
    """

    NEXT_URL = "https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php"
    PAST_URL = "https://www.thesportsdb.com/api/v1/json/3/eventspastleague.php"

    @resp.activate
    def test_combines_next_and_past_events(self):
        resp.add(resp.GET, self.NEXT_URL, json={"events": [TSDB_EVENTS_FIXTURE[0]]}, status=200)
        resp.add(resp.GET, self.PAST_URL, json={"events": [TSDB_EVENTS_FIXTURE[1]]}, status=200)

        adapter = TheSportsDBAdapter()
        events = adapter.fetch_events(competition_slug="la-liga")
        self.assertEqual(len(events), 2)

    @resp.activate
    def test_deduplicates_events(self):
        """Same event ID in both next and past should appear only once."""
        resp.add(resp.GET, self.NEXT_URL, json={"events": [TSDB_EVENTS_FIXTURE[0]]}, status=200)
        resp.add(resp.GET, self.PAST_URL, json={"events": [TSDB_EVENTS_FIXTURE[0]]}, status=200)

        adapter = TheSportsDBAdapter()
        events = adapter.fetch_events(competition_slug="la-liga")
        self.assertEqual(len(events), 1)

    @resp.activate
    def test_status_mapping_ns_is_scheduled(self):
        resp.add(resp.GET, self.NEXT_URL, json={"events": [TSDB_EVENTS_FIXTURE[0]]}, status=200)
        resp.add(resp.GET, self.PAST_URL, json={"events": []}, status=200)

        adapter = TheSportsDBAdapter()
        events = adapter.fetch_events(competition_slug="la-liga")
        self.assertEqual(events[0]["status"], "scheduled")

    @resp.activate
    def test_status_mapping_ft_is_finished(self):
        resp.add(resp.GET, self.NEXT_URL, json={"events": []}, status=200)
        resp.add(resp.GET, self.PAST_URL, json={"events": [TSDB_EVENTS_FIXTURE[1]]}, status=200)

        adapter = TheSportsDBAdapter()
        events = adapter.fetch_events(competition_slug="la-liga")
        self.assertEqual(events[0]["status"], "finished")

    @resp.activate
    def test_unknown_competition_returns_empty(self):
        adapter = TheSportsDBAdapter()
        events = adapter.fetch_events(competition_slug="nonexistent-league")
        self.assertEqual(events, [])


@override_settings(
    API_CACHE_TTL=0,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}},
    API_FOOTBALL_KEY="test-key-123",
)
class TestApiFootballAdapter(TestCase):
    """
    Verifies ApiFootballAdapter: timestamp parsing, status mapping.
    """

    FIXTURES_URL = "https://v3.football.api-sports.io/fixtures"

    @resp.activate
    def test_fetch_returns_parsed_event(self):
        resp.add(resp.GET, self.FIXTURES_URL, json=API_FOOTBALL_FIXTURE, status=200)

        adapter = ApiFootballAdapter()
        events = adapter.fetch_events(competition_slug="premier-league", season=2026)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], "Manchester City vs Arsenal")
        self.assertEqual(events[0]["participant_home"], "Manchester City")
        self.assertEqual(events[0]["status"], "scheduled")

    @resp.activate
    def test_external_id_is_fixture_id(self):
        resp.add(resp.GET, self.FIXTURES_URL, json=API_FOOTBALL_FIXTURE, status=200)

        adapter = ApiFootballAdapter()
        events = adapter.fetch_events(competition_slug="premier-league", season=2026)
        self.assertEqual(events[0]["external_id"], "999001")

    def test_missing_api_key_raises(self):
        with self.settings(API_FOOTBALL_KEY=""):
            adapter = ApiFootballAdapter()
            with self.assertRaises(RuntimeError):
                adapter.fetch_events(competition_slug="la-liga")


class TestLiveStatusApi(TestCase):
    """
    Verifies the /api/live-status/ JSON endpoint.
    """

    def _make_live_event(self):
        from schedule.models import Competition, Event, Sport

        sport = Sport.objects.create(
            name="Football", slug="football-ls", category=Sport.CATEGORY_FOOTBALL, order=0
        )
        comp = Competition.objects.create(sport=sport, name="Test League", slug="test-league-ls")
        return Event.objects.create(
            competition=comp,
            title="Live Match",
            start_datetime=timezone.now() - datetime.timedelta(minutes=30),
            status=Event.STATUS_LIVE,
        )

    def test_live_status_returns_json(self):
        from django.urls import reverse

        response = self.client.get(reverse("schedule:live_status_api"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_live_count_reflects_live_events(self):
        from django.urls import reverse

        self._make_live_event()
        response = self.client.get(reverse("schedule:live_status_api"))
        data = json.loads(response.content)
        self.assertEqual(data["live_count"], 1)
        self.assertEqual(len(data["events"]), 1)
        self.assertEqual(data["events"][0]["title"], "Live Match")

    def test_empty_when_no_live_events(self):
        from django.urls import reverse

        response = self.client.get(reverse("schedule:live_status_api"))
        data = json.loads(response.content)
        self.assertEqual(data["live_count"], 0)
        self.assertEqual(data["events"], [])


class TestUpdateStatusesCommand(TestCase):
    """
    Verifies the update_statuses management command transitions events
    through scheduled → live → finished based on start_datetime.
    """

    def _make_competition(self):
        from schedule.models import Competition, Sport

        sport = Sport.objects.create(
            name="Football", slug="football-cmd", category=Sport.CATEGORY_FOOTBALL, order=0
        )
        return Competition.objects.create(sport=sport, name="Test Cup", slug="test-cup-cmd")

    def test_future_event_stays_scheduled(self):
        from django.core.management import call_command

        from schedule.models import Event

        comp = self._make_competition()
        event = Event.objects.create(
            competition=comp,
            title="Future Match",
            start_datetime=timezone.now() + datetime.timedelta(hours=5),
            status=Event.STATUS_SCHEDULED,
        )
        call_command("update_statuses", verbosity=0)
        event.refresh_from_db()
        self.assertEqual(event.status, Event.STATUS_SCHEDULED)

    def test_recent_past_event_becomes_live(self):
        from django.core.management import call_command

        from schedule.models import Event

        comp = self._make_competition()
        event = Event.objects.create(
            competition=comp,
            title="Recent Match",
            start_datetime=timezone.now() - datetime.timedelta(hours=1),
            status=Event.STATUS_SCHEDULED,
        )
        call_command("update_statuses", verbosity=0)
        event.refresh_from_db()
        self.assertEqual(event.status, Event.STATUS_LIVE)

    def test_old_past_event_becomes_finished(self):
        from django.core.management import call_command

        from schedule.models import Event

        comp = self._make_competition()
        event = Event.objects.create(
            competition=comp,
            title="Old Match",
            start_datetime=timezone.now() - datetime.timedelta(hours=5),
            status=Event.STATUS_SCHEDULED,
        )
        call_command("update_statuses", verbosity=0)
        event.refresh_from_db()
        self.assertEqual(event.status, Event.STATUS_FINISHED)
