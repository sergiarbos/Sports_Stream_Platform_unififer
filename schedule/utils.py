from django.utils import timezone
from datetime import timedelta
from .models import Event

def categorize_event(event):
    """
    Categorizes an event as 'Live', 'Today', 'Tomorrow', or None.
    Uses the currently active timezone to determine the local date.
    """
    if event.status == Event.STATUS_LIVE:
        return "Live"
        
    now = timezone.localtime(timezone.now())
    event_local = timezone.localtime(event.start_datetime)
    
    if event_local.date() == now.date():
        return "Today"
    elif event_local.date() == (now + timedelta(days=1)).date():
        return "Tomorrow"
        
    return None

def filter_events(events, category):
    """
    Filters a list/queryset of events by the given category ('Live', 'Today', 'Tomorrow').
    """
    return [e for e in events if categorize_event(e) == category]
