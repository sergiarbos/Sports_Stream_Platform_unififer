from django.shortcuts import render

from .models import Event, Sport


def home(request):
    """
    SportLink home page.

    Business rules applied here (see Event.is_visible and
    Event.spanish_broadcasts in models.py for details):
      1. Only events with at least one Spanish-language broadcast are listed.
      2. Future or live events -> always visible, with their schedule.
      3. Past events -> only visible if they have a replay/VOD available.
    """
    sports = Sport.objects.all()
    selected_sport_slug = request.GET.get("sport", "all")

    events_qs = (
        Event.objects.select_related("competition", "competition__sport")
        .prefetch_related("broadcasts__platform")
        .all()
    )
    if selected_sport_slug != "all":
        events_qs = events_qs.filter(competition__sport__slug=selected_sport_slug)

    live, upcoming, past = [], [], []
    for event in events_qs:
        if not event.is_visible:
            continue
        if event.status == Event.STATUS_LIVE:
            live.append(event)
        elif event.status == Event.STATUS_FINISHED:
            past.append(event)
        else:
            upcoming.append(event)

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
