"""
Unit tests for the schedule app.
Covers the core business rules and the home view.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Broadcast, Competition, Event, Platform, Sport


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
