"""
Lightweight command that syncs Event.status in the database with the
current wall-clock time. Does NOT call any external API.

When to run:
  - Via cron at 01:00 daily (right after import_all_sports) so the
    Django admin panel shows accurate statuses.
  - Manually at any time to force a refresh.

Note: the web view (views.py) calculates status dynamically on every
request and does NOT depend on this DB field, so the public site is
always accurate even if you forget to run this command.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from schedule.models import Event

# Keep in sync with views.py LIVE_WINDOW
LIVE_WINDOW = timedelta(hours=2, minutes=30)


class Command(BaseCommand):
    help = "Updates Event.status in the DB based on current time (no API calls)."

    def handle(self, *args, **options):
        now = timezone.now()

        # → FINISHED: started more than LIVE_WINDOW ago
        n_finished = (
            Event.objects.filter(start_datetime__lt=now - LIVE_WINDOW)
            .exclude(status=Event.STATUS_FINISHED)
            .update(status=Event.STATUS_FINISHED)
        )

        # → LIVE: started within the last LIVE_WINDOW
        n_live = (
            Event.objects.filter(
                start_datetime__gte=now - LIVE_WINDOW,
                start_datetime__lte=now,
            )
            .exclude(status=Event.STATUS_LIVE)
            .update(status=Event.STATUS_LIVE)
        )

        # → SCHEDULED: in the future (correct any stale status)
        n_scheduled = (
            Event.objects.filter(start_datetime__gt=now)
            .exclude(status=Event.STATUS_SCHEDULED)
            .update(status=Event.STATUS_SCHEDULED)
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Statuses updated: {n_live} → live, "
                f"{n_finished} → finished, "
                f"{n_scheduled} → scheduled."
            )
        )
