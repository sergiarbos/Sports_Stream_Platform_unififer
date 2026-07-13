from django.urls import path

from . import views

app_name = "schedule"

urlpatterns = [
    path("", views.home, name="home"),
    path("results/<int:event_id>/", views.event_details, name="event_details"),
    path("api/live-status/", views.live_status_api, name="live_status_api"),
]
