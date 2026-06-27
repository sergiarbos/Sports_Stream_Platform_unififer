from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

from .models import Event, Sport

# ---------------------------------------------------------------------------
# Timing constants
# ---------------------------------------------------------------------------
# How long after start_datetime an event stays in the LIVE section.
# Most sports (football, F1, MotoGP, tennis sets) finish within 2h30m.
LIVE_WINDOW = timedelta(hours=2, minutes=30)

# Only show upcoming events that start within the next 2 days.
# Events further away are hidden until they enter this window.
UPCOMING_WINDOW = timedelta(days=2)


def home(request):
    """
    SportLink home page.

    Status is determined DYNAMICALLY from start_datetime on every request —
    the stored Event.status field is NOT used for display purposes, so the
    page is always accurate without needing to re-run the import.

    Visibility rules:
      1. Only events with at least one Spanish-language broadcast are shown.
      2. LIVE     → started within the last LIVE_WINDOW (2h30m).
      3. UPCOMING → not started yet AND within UPCOMING_WINDOW (next 2 days).
      4. PAST     → started more than LIVE_WINDOW ago, visible only if a
                    Spanish broadcast with VOD/replay is available.
    """
    now = timezone.now()
    upcoming_cutoff = now + UPCOMING_WINDOW

    sports = Sport.objects.all()
    selected_sport_slug = request.GET.get("sport", "all")

    # Pre-filter: only events that have at least one Spanish broadcast
    events_qs = (
        Event.objects.select_related("competition", "competition__sport")
        .prefetch_related("broadcasts__platform")
        .filter(broadcasts__language__startswith="es")
        .distinct()
    )
    if selected_sport_slug != "all":
        events_qs = events_qs.filter(competition__sport__slug=selected_sport_slug)

    live, upcoming, past = [], [], []

    for event in events_qs:
        start = event.start_datetime

        if start > now:
            # --- Event has not started yet ---
            # Only include if it starts within the next 2 days
            if start <= upcoming_cutoff:
                upcoming.append(event)
            # else: too far away — don't show yet

        elif start + LIVE_WINDOW >= now:
            # --- Event started within the last 2h30m → LIVE ---
            live.append(event)

        else:
            # --- Event started more than 2h30m ago → PAST ---
            # Only show if at least one Spanish broadcast has a replay/VOD
            if event.broadcasts.filter(
                language__startswith="es", vod_available=True
            ).exists():
                past.append(event)

    upcoming.sort(key=lambda e: e.start_datetime)
    past.sort(key=lambda e: e.start_datetime, reverse=True)

    context = {
        "sports": sports,
        "selected_sport_slug": selected_sport_slug,
        "live_events": live,
        "upcoming_events": upcoming,
        "past_events": past,
    }
    return render(request, "schedule/home.html", context)
