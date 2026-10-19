"""
DRF serializers for the mobile REST API.

These are read-only (no write operations needed — the app only consumes data).
They mirror the shapes used by the existing web views so the Flutter client
can drive the same three-section layout (live / upcoming / on_demand).
"""

from rest_framework import serializers

from .models import Broadcast, Competition, Event, Platform, Sport


class SportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sport
        fields = ["id", "name", "slug", "category", "icon", "order"]


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = ["id", "name", "slug", "website_url", "color", "requires_subscription"]


class CompetitionSerializer(serializers.ModelSerializer):
    sport = SportSerializer(read_only=True)

    class Meta:
        model = Competition
        fields = ["id", "name", "slug", "short_code", "badge_initials", "sport"]


class BroadcastSerializer(serializers.ModelSerializer):
    platform = PlatformSerializer(read_only=True)
    # Expose the computed property so the Flutter app doesn't need to
    # re-implement the URL-fallback logic.
    url = serializers.CharField(source="direct_url", read_only=True)
    is_latam = serializers.BooleanField(read_only=True)

    class Meta:
        model = Broadcast
        fields = [
            "id",
            "platform",
            "language",
            "is_latam",
            "commentary_region",
            "is_live_stream",
            "vod_available",
            "url",
            "notes",
        ]


class EventSerializer(serializers.ModelSerializer):
    competition = CompetitionSerializer(read_only=True)
    # Only Spanish-language broadcasts (mirrors Event.spanish_broadcasts).
    broadcasts = serializers.SerializerMethodField()
    # Computed status for this request (may differ from DB value).
    effective_status = serializers.CharField(read_only=True)
    status_label = serializers.CharField(read_only=True)
    # Score as a single formatted string for convenience ("2 - 1" or null).
    score = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "competition",
            "participant_home",
            "participant_away",
            "start_datetime",
            "effective_status",
            "status_label",
            "round_name",
            "score",
            "result_text",
            "broadcasts",
        ]

    def get_broadcasts(self, obj):
        spanish = obj.broadcasts.filter(language__startswith="es").select_related("platform")
        return BroadcastSerializer(spanish, many=True).data

    def get_score(self, obj):
        if obj.score_home is not None and obj.score_away is not None:
            return f"{obj.score_home} - {obj.score_away}"
        return None


class EventListSerializer(serializers.Serializer):
    """Wrapper that groups events into the three sections the home screen uses."""

    live = EventSerializer(many=True)
    upcoming = EventSerializer(many=True)
    on_demand = EventSerializer(many=True)
    live_count = serializers.IntegerField()
    generated_at = serializers.DateTimeField()
