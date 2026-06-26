"""
Demonstrates the adapter architecture working with a REAL and free API
(no key required): imports the current Formula 1 calendar from Jolpica.

Usage:
    python manage.py import_f1_calendar

Note: you need an internet connection to run this command. If you don't
have one right now, use `seed_demo_data` to load sample data instead.
"""

from django.core.management.base import BaseCommand

from schedule.models import Competition, Event
from schedule.services.jolpica_f1 import JolpicaF1Adapter


class Command(BaseCommand):
    help = "Imports the real F1 calendar from the free Jolpica API."

    def handle(self, *args, **options):
        try:
            competition = Competition.objects.get(slug="f1")
        except Competition.DoesNotExist:
            self.stderr.write(
                "Competition 'f1' does not exist. Run "
                "`python manage.py seed_demo_data` first to create sports and competitions."
            )
            return

        adapter = JolpicaF1Adapter()
        try:
            races = adapter.fetch_events(season="2026")
        except Exception as exc:  # noqa: BLE001 - display any network error clearly
            self.stderr.write(f"Could not reach the F1 API: {exc}")
            return

        created_or_updated = 0
        for race in races:
            Event.objects.update_or_create(
                competition=competition,
                external_id=race["external_id"],
                defaults={
                    "title": race["title"],
                    "round_name": race["round_name"],
                    "start_datetime": race["start_datetime"],
                    "status": race["status"],
                },
            )
            created_or_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"F1 calendar imported: {created_or_updated} sessions. "
                "Remember to assign broadcast platforms from /admin/."
            )
        )
