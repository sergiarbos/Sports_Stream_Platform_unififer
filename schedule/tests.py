"""
Unit tests for the schedule app.
Covers the core business rules and the home view.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch
import datetime

from .models import Broadcast, Competition, Event, Platform, Sport
from .utils import categorize_event, filter_events


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
        event=event, platform=platform,
        language=Broadcast.LANGUAGE_ES_ES, vod_available=vod,
    )


class StatusLabelTest(TestCase):
    def setUp(self):
        self.comp = make_competition(make_sport())

    def test_live(self):
        self.assertEqual(make_event(self.comp, status=Event.STATUS_LIVE).status_label, "LIVE")

    def test_finished(self):
        self.assertEqual(make_event(self.comp, status=Event.STATUS_FINISHED).status_label, "ON DEMAND")

    def test_scheduled(self):
        self.assertEqual(make_event(self.comp, status=Event.STATUS_SCHEDULED).status_label, "UPCOMING")


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
            competition=comp, title="Far future final",
            start_datetime=timezone.now() + timedelta(days=35),
            status=Event.STATUS_SCHEDULED,
        )
        make_broadcast(far_event, platform)
        response = self.client.get(reverse("schedule:home"))
        self.assertNotIn(far_event, response.context["upcoming_events"])

class DateTimeFilterTest(TestCase):
    def setUp(self):
        self.sport = make_sport()
        self.comp = make_competition(self.sport)

    @patch('schedule.utils.timezone.now')
    def test_categorize_event_today_tomorrow_live(self, mock_now):
        fixed_now = datetime.datetime(2026, 7, 1, 12, 0, tzinfo=datetime.timezone.utc)
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

    @patch('schedule.utils.timezone.now')
    def test_timezone_offsets(self, mock_now):
        fixed_utc_now = datetime.datetime(2026, 7, 1, 23, 0, tzinfo=datetime.timezone.utc)
        mock_now.return_value = fixed_utc_now
        
        event = Event.objects.create(
            competition=self.comp,
            title="Late Match",
            start_datetime=fixed_utc_now + timedelta(hours=1, minutes=30),
            status=Event.STATUS_SCHEDULED,
        )
        
        # 1. Test UTC
        # Event is at 00:30 next day UTC -> "Tomorrow"
        with timezone.override('UTC'):
            self.assertEqual(categorize_event(event), "Tomorrow")
            
        # 2. Test CET (Europe/Madrid)
        # Now is 01:00 on 2nd July. Event is at 02:30 on 2nd July -> "Today"
        with timezone.override('Europe/Madrid'):
            self.assertEqual(categorize_event(event), "Today")
            
        # 3. Test EST (America/New_York)
        # Now is 18:00 on 1st July. Event is at 20:30 on 1st July -> "Today"
        with timezone.override('America/New_York'):
            self.assertEqual(categorize_event(event), "Today")

    @patch('schedule.utils.timezone.now')
    def test_filter_events_helper(self, mock_now):
        fixed_now = datetime.datetime(2026, 7, 1, 12, 0, tzinfo=datetime.timezone.utc)
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
        
        with timezone.override('UTC'):
            self.assertListEqual(filter_events(events, "Live"), [live_event])
            self.assertListEqual(filter_events(events, "Today"), [today_event])
            self.assertListEqual(filter_events(events, "Tomorrow"), [tomorrow_event])
