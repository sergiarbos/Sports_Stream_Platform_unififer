from django.shortcuts import render
from django.utils import timezone

from .models import Event, Platform, Sport


def home(request):
    """
    Home page ("Split Screen & Multi-View" layout):
      - Left column: compact schedule (live / upcoming / on-demand).
      - Right column: fixed links panel showing direct links for each event.

    Business rules applied here (see Event.is_visible in models.py):
      1. Only events with at least one Spanish-language broadcast are listed.
      2. Future or live events -> always visible, with their scheduled time.
      3. Past events -> only visible if they have a replay/VOD AND occurred
         within the last Event.ARCHIVE_WINDOW_DAYS days.

    Available querystring filters:
      ?sport=<slug>     filters by sport (or "all").
      ?platform=<slug>  filters to events broadcast in Spanish on that
                        platform (or "all"). Only platforms that actually
                        have at least one Spanish broadcast are listed
                        to avoid empty options.
    """
    sports = Sport.objects.all()
    platforms = Platform.objects.filter(
        broadcasts__language__startswith="es"
    ).distinct().order_by("name")

    selected_sport_slug = request.GET.get("sport", "all")
    selected_platform_slug = request.GET.get("platform", "all")

    events_qs = (
        Event.objects.select_related("competition", "competition__sport")
        .prefetch_related("broadcasts__platform")
        .exclude(
            status=Event.STATUS_SCHEDULED,
            start_datetime__gt=(
                timezone.now() + timezone.timedelta(days=Event.UPCOMING_WINDOW_DAYS)
            ),
        )
    )
    if selected_sport_slug != "all":
        events_qs = events_qs.filter(competition__sport__slug=selected_sport_slug)
    if selected_platform_slug != "all":
        events_qs = events_qs.filter(
            broadcasts__platform__slug=selected_platform_slug,
            broadcasts__language__startswith="es",
        ).distinct()

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

    # Featured strip (top banner): prioritises currently live events;
    # fills up with the nearest upcoming ones if there aren't enough.
    featured = (live + upcoming)[:2]

    # Links panel (right column): same order as the left-hand schedule
    # so that the "Get links" anchor always stays in view.
    link_events = live + upcoming + past

    context = {
        "sports": sports,
        "platforms": platforms,
        "selected_sport_slug": selected_sport_slug,
        "selected_platform_slug": selected_platform_slug,
        "live_events": live,
        "upcoming_events": upcoming,
        "past_events": past,
        "live_count": len(live),
        "featured_events": featured,
        "link_events": link_events,
        "archive_window_days": Event.ARCHIVE_WINDOW_DAYS,
    }
    return render(request, "schedule/home.html", context)
