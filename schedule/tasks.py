import logging

from django_huey import db_periodic_task
from huey import crontab

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(minute="*/5"), queue="main")
def auto_update_statuses():
    from datetime import timedelta

    from django.utils import timezone

    from schedule.models import Event

    LIVE_WINDOW = timedelta(hours=2, minutes=30)
    now = timezone.now()

    n_finished = (
        Event.objects.filter(start_datetime__lt=now - LIVE_WINDOW)
        .exclude(status=Event.STATUS_FINISHED)
        .update(status=Event.STATUS_FINISHED)
    )
    n_live = (
        Event.objects.filter(
            start_datetime__gte=now - LIVE_WINDOW,
            start_datetime__lte=now,
        )
        .exclude(status=Event.STATUS_LIVE)
        .update(status=Event.STATUS_LIVE)
    )
    n_scheduled = (
        Event.objects.filter(start_datetime__gt=now)
        .exclude(status=Event.STATUS_SCHEDULED)
        .update(status=Event.STATUS_SCHEDULED)
    )

    logger.info(
        "Huey auto_update_statuses: %d→live, %d→finished, %d→scheduled",
        n_live,
        n_finished,
        n_scheduled,
    )


@db_periodic_task(crontab(hour="3", minute="0"), queue="main")
def auto_import_all_sports():
    import time

    from django.utils import timezone

    from schedule.models import Broadcast, Competition, Event, Platform
    from schedule.services.jolpica_f1 import JolpicaF1Adapter
    from schedule.services.static_calendar import StaticCalendarAdapter
    from schedule.services.thesportsdb import TheSportsDBAdapter

    logger.info("Huey auto_import_all_sports: starting at %s", timezone.now())

    from schedule.management.commands.import_all_sports import BROADCAST_MAP, IMPORT_PLAN

    LA = Broadcast.LANGUAGE_ES_LA

    platforms = {p.slug: p for p in Platform.objects.all()}
    if not platforms:
        logger.error("Huey auto_import_all_sports: no platforms found, aborting.")
        return

    adapters = {
        "jolpica_f1": JolpicaF1Adapter(),
        "thesportsdb": TheSportsDBAdapter(),
        "static_calendar": StaticCalendarAdapter(),
    }

    total_imported = 0

    for comp_slug, source, fetch_kwargs in IMPORT_PLAN:
        try:
            competition = Competition.objects.get(slug=comp_slug)
        except Competition.DoesNotExist:
            logger.warning("Huey import: competition '%s' not found, skipping.", comp_slug)
            continue

        adapter = adapters[source]
        try:
            events_data = adapter.fetch_events(**fetch_kwargs)
        except Exception as exc:
            logger.error("Huey import: error fetching %s: %s", comp_slug, exc)
            continue

        if not events_data:
            continue

        for event_data in events_data:
            event, _ = Event.objects.update_or_create(
                competition=competition,
                external_id=event_data["external_id"],
                defaults={
                    "title": event_data["title"],
                    "round_name": event_data.get("round_name", ""),
                    "start_datetime": event_data["start_datetime"],
                    "status": event_data["status"],
                    "participant_home": event_data.get("participant_home", ""),
                    "participant_away": event_data.get("participant_away", ""),
                },
            )
            total_imported += 1

            if not event.broadcasts.exists():
                for plat_slug, language, is_live in BROADCAST_MAP.get(comp_slug, []):
                    plat = platforms.get(plat_slug)
                    if not plat:
                        continue
                    vod = event.status == Event.STATUS_FINISHED
                    Broadcast.objects.get_or_create(
                        event=event,
                        platform=plat,
                        language=language,
                        defaults={
                            "is_live_stream": is_live,
                            "vod_available": vod,
                            "commentary_region": "Latin America" if language == LA else "",
                        },
                    )

        if source == "thesportsdb":
            time.sleep(2)

    logger.info("Huey auto_import_all_sports: done, %d events upserted.", total_imported)
