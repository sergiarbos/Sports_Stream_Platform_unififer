from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.conf import settings
import requests

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

    view_mode = request.GET.get("view_mode", "links")
    if view_mode == "results":
        sports = sports.filter(category__in=[Sport.CATEGORY_FOOTBALL, Sport.CATEGORY_MOTORSPORT])

    selected_sport_slug = request.GET.get("sport", "all")
    selected_platform_slug = request.GET.get("platform", "all")

    if view_mode == "results":
        from django.db.models import Q
        cutoff = timezone.now() - timezone.timedelta(days=14)
        
        condition = Q(competition__sport__category=Sport.CATEGORY_MOTORSPORT) | Q(competition__sport__category=Sport.CATEGORY_FOOTBALL, start_datetime__gte=cutoff)
        
        qs = Event.objects.select_related("competition", "competition__sport").filter(
            status=Event.STATUS_FINISHED
        ).filter(condition).exclude(competition__slug="mundial-2026")
        if selected_sport_slug != "all":
            qs = qs.filter(competition__sport__slug=selected_sport_slug)
        
        results_events = qs.order_by("-start_datetime")
        
        context = {
            "sports": sports,
            "platforms": platforms,
            "selected_sport_slug": selected_sport_slug,
            "selected_platform_slug": selected_platform_slug,
            "view_mode": view_mode,
            "results_events": results_events,
        }
        return render(request, "schedule/home.html", context)

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
        "view_mode": view_mode,
        "live_events": live,
        "upcoming_events": upcoming,
        "past_events": past,
        "live_count": len(live),
        "featured_events": featured,
        "link_events": link_events,
        "archive_window_days": Event.ARCHIVE_WINDOW_DAYS,
    }
    return render(request, "schedule/home.html", context)


def event_details(request, event_id):
    """
    Shows detailed API data for an event when clicking VER DETALLES COMPLETOS.
    Currently supports api_football and jolpica_f1.
    """
    event = get_object_or_404(Event.objects.select_related("competition"), pk=event_id)
    api_data = None
    
    if event.competition.source == "api_football" and event.external_id:
        api_key = settings.API_FOOTBALL_KEY
        if api_key:
            headers = {"x-apisports-key": api_key}
            params = {"id": event.external_id}
            try:
                response = requests.get(
                    "https://v3.football.api-sports.io/fixtures", headers=headers, params=params, timeout=10
                )
                if response.status_code == 200:
                    resp_json = response.json()
                    data = resp_json.get("response", [])
                    if data:
                        api_data = data[0]
            except Exception:
                pass

    elif event.competition.source == "jolpica_f1" and event.external_id:
        # e.g. external_id = "f1-2026-8-race"
        parts = event.external_id.split("-")
        if len(parts) >= 3:
            season = parts[1]
            round_val = parts[2]
            try:
                # the user specifically asked for API data, Jolpica's result endpoint for a specific round is:
                url = f"https://api.jolpi.ca/ergast/f1/{season}/{round_val}/results.json"
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    res_json = res.json()
                    races = res_json.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                    if races:
                        api_data = races[0]
            except Exception:
                pass

    context = {
        "event": event,
        "api_data": api_data,
    }
    return render(request, "schedule/event_details.html", context)
