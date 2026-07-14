from django.conf.urls.i18n import set_language
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/set-language/", set_language, name="set_language"),
    path("", include("schedule.urls")),
]
