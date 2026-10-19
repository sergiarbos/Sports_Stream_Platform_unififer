from django.urls import path

from . import views

app_name = "schedule"

urlpatterns = [
    # -----------------------------------------------------------------------
    # Web views (unchanged)
    # -----------------------------------------------------------------------
    path("", views.home, name="home"),
    path("api/events/", views.events_api, name="events_api"),
    path("results/<int:event_id>/", views.event_details, name="event_details"),
    path("api/live-status/", views.live_status_api, name="live_status_api"),
    # -----------------------------------------------------------------------
    # REST API v1 — consumed by the Flutter mobile app
    # -----------------------------------------------------------------------
    path("api/v1/events/", views.EventListAPIView.as_view(), name="api_events"),
    path(
        "api/v1/events/<int:event_id>/", views.EventDetailAPIView.as_view(), name="api_event_detail"
    ),
    path("api/v1/sports/", views.SportListAPIView.as_view(), name="api_sports"),
]
