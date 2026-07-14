from django.contrib import admin

from .models import Broadcast, Competition, Event, Platform, Sport


class BroadcastInline(admin.TabularInline):
    model = Broadcast
    extra = 1


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "icon", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ("name", "sport", "source")
    list_filter = ("sport",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ("name", "website_url", "requires_subscription", "color")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "competition", "start_datetime", "status", "is_visible")
    list_filter = ("status", "competition__sport", "competition")
    search_fields = ("title", "participant_home", "participant_away")
    inlines = [BroadcastInline]

    @admin.display(boolean=True, description="¿Visible en la web?")
    def is_visible(self, obj):
        return obj.is_visible


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "platform",
        "language",
        "is_live_stream",
        "event_url",
        "vod_available",
        "vod_url",
    )
    list_filter = ("platform", "language", "vod_available")
