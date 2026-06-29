from django.shortcuts import render

from .models import Event, Sport


def home(request):
    """
    Página principal (layout "Split Screen & Multi-View"):
      - Columna izquierda: agenda compacta (directo / próximos / diferido).
      - Columna derecha: panel fijo con los enlaces directos de cada evento.

    Reglas de negocio aplicadas aquí (ver Event.is_visible en models.py):
      1. Solo se listan eventos con al menos una retransmisión en español.
      2. Eventos futuros o en directo -> siempre visibles, con su horario.
      3. Eventos pasados -> solo visibles si tienen repetición/VOD Y ocurrieron
         dentro de los últimos Event.ARCHIVE_WINDOW_DAYS días.
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

    # Eventos destacados para la franja superior (prioriza lo que está en
    # directo ahora mismo; si no hay suficiente, rellena con lo más próximo).
    featured = (live + upcoming)[:2]

    # Panel de enlaces (columna derecha): mismo orden que la agenda de la
    # izquierda, para que el anclaje "Ver enlaces" siempre quede a la vista.
    link_events = live + upcoming + past

    context = {
        "sports": sports,
        "selected_sport_slug": selected_sport_slug,
        "live_events": live,
        "upcoming_events": upcoming,
        "past_events": past,
        "live_count": len(live),
        "featured_events": featured,
        "link_events": link_events,
        "archive_window_days": Event.ARCHIVE_WINDOW_DAYS,
    }
    return render(request, "schedule/home.html", context)
