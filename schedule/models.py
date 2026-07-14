from django.db import models
from django.utils import timezone


class Sport(models.Model):
    """Top-level sport category (Football, Basketball, Motorsport, Tennis, Winter Sports...)."""

    CATEGORY_FOOTBALL = "football"
    CATEGORY_BASKETBALL = "basketball"
    CATEGORY_MOTORSPORT = "motorsport"
    CATEGORY_TENNIS = "tennis"
    CATEGORY_WINTER = "winter_sports"

    CATEGORY_CHOICES = [
        (CATEGORY_FOOTBALL, "Football"),
        (CATEGORY_BASKETBALL, "Basketball"),
        (CATEGORY_MOTORSPORT, "Motorsport"),
        (CATEGORY_TENNIS, "Tennis"),
        (CATEGORY_WINTER, "Winter Sports"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    icon = models.CharField(
        max_length=10,
        blank=True,
        help_text="Emoji used as a quick icon in the UI (e.g. ⚽).",
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def accent_class(self):
        """CSS colour class by category, used in monograms and featured cards."""
        return f"accent-{self.category}"


class Competition(models.Model):
    """A specific competition within a sport (Champions League, NBA, F1...)."""

    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="competitions")
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    short_code = models.CharField(
        max_length=6,
        blank=True,
        help_text=(
            "Short initials for the competition badge (e.g. 'CL', "
            "'NBA', 'F1'). Used instead of copyrighted logos."
        ),
    )
    # Identifies which data source/adapter this competition comes from.
    # See schedule/services/adapters.py for the list of supported sources.
    source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Data adapter identifier (e.g. 'api_football', 'jolpica_f1', 'manual').",
    )
    external_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["sport__order", "name"]
        verbose_name_plural = "competitions"

    def __str__(self):
        return f"{self.name} ({self.sport.name})"

    @property
    def badge_initials(self):
        """Initials to display on the badge when no short_code is defined."""
        if self.short_code:
            return self.short_code
        words = [w for w in self.name.split() if w.lower() not in ("de", "del", "la", "el")]
        return "".join(w[0] for w in words[:3]).upper()


class Platform(models.Model):
    """Streaming platform where an event can be watched (DAZN, Movistar Plus+, ESPN, ViX...)."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    website_url = models.URLField(blank=True)
    # Hex colour used to render the platform badge in the UI,
    # avoiding the need to host copyrighted logos for each platform.
    color = models.CharField(max_length=7, default="#2563eb")
    requires_subscription = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Event(models.Model):
    """A concrete sporting event: a match, a race, a bout..."""

    STATUS_SCHEDULED = "scheduled"
    STATUS_LIVE = "live"
    STATUS_FINISHED = "finished"

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_LIVE, "Live"),
        (STATUS_FINISHED, "Finished"),
    ]

    # Number of days a finished event remains in "On demand" before
    # disappearing from the listing (even if a VOD is still available).
    ARCHIVE_WINDOW_DAYS = 14

    # Maximum forward horizon: scheduled events further away than this
    # number of days are hidden from the schedule (prevents infinite lists).
    UPCOMING_WINDOW_DAYS = 365

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(
        max_length=200,
        help_text="E.g. 'Real Madrid vs Manchester City' or 'Monaco Grand Prix'.",
    )
    participant_home = models.CharField(max_length=120, blank=True)
    participant_away = models.CharField(max_length=120, blank=True)
    start_datetime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    external_id = models.CharField(max_length=100, blank=True)
    round_name = models.CharField(
        max_length=120, blank=True, help_text="E.g. 'Matchday 12', 'Round of 16', 'Qualifying'."
    )
    score_home = models.PositiveSmallIntegerField(blank=True, null=True)
    score_away = models.PositiveSmallIntegerField(blank=True, null=True)
    result_text = models.CharField(
        max_length=200, blank=True, help_text="E.g. '1st Verstappen, 2nd Norris' for F1."
    )

    class Meta:
        ordering = ["start_datetime"]

    def __str__(self):
        return f"{self.title} - {self.start_datetime:%d/%m/%Y %H:%M}"

    @property
    def is_past(self):
        return self.start_datetime < timezone.now() and self.status != Event.STATUS_LIVE

    @property
    def is_within_archive_window(self):
        """Did this finished event fall within the last ARCHIVE_WINDOW_DAYS days?"""
        cutoff = timezone.now() - timezone.timedelta(days=Event.ARCHIVE_WINDOW_DAYS)
        return self.start_datetime >= cutoff

    @property
    def spanish_broadcasts(self):
        """Only broadcasts with Spanish-language commentary."""
        return self.broadcasts.filter(language__startswith="es")

    @property
    def is_visible(self):
        """
        Core visibility rule:
        - If the event is upcoming or live -> always shown (with its scheduled time).
        - If the event has already finished -> only shown if the
          event occurred within the last ARCHIVE_WINDOW_DAYS days
          (after that window it disappears from "On demand").
        """
        broadcasts = self.spanish_broadcasts
        if not broadcasts.exists():
            return False
        if self.status == Event.STATUS_FINISHED:
            return self.is_within_archive_window
        return True

    @property
    def status_label(self):
        if self.status == Event.STATUS_LIVE:
            return "LIVE"
        if self.status == Event.STATUS_FINISHED:
            return "ON DEMAND"
        return "UPCOMING"


class Broadcast(models.Model):
    """Event <-> platform relationship: where and how the event can be watched/heard."""

    LANGUAGE_ES_ES = "es-ES"
    LANGUAGE_ES_LA = "es-LA"

    LANGUAGE_CHOICES = [
        (LANGUAGE_ES_ES, "Spanish (Spain)"),
        (LANGUAGE_ES_LA, "Spanish (Latin America)"),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="broadcasts")
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name="broadcasts")
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default=LANGUAGE_ES_ES)
    commentary_region = models.CharField(
        max_length=80,
        blank=True,
        help_text="Optional, e.g. 'Mexico', 'Argentina', 'Pan-LATAM'.",
    )
    is_live_stream = models.BooleanField(
        default=True, help_text="Does this platform stream it live?"
    )
    event_url = models.URLField(
        blank=True,
        help_text=(
            "Direct link to THIS specific event on the platform "
            "(not to the platform homepage). Used for live/upcoming events."
        ),
    )
    vod_available = models.BooleanField(
        default=False,
        help_text="Is a replay/on-demand version available after the event finishes?",
    )
    vod_url = models.URLField(
        blank=True, help_text="Direct link to the replay/on-demand version of THIS event."
    )
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("event", "platform", "language")
        ordering = ["platform__name"]

    def __str__(self):
        return f"{self.event} on {self.platform} ({self.get_language_display()})"

    @property
    def is_latam(self):
        return self.language == Broadcast.LANGUAGE_ES_LA

    @property
    def direct_url(self):
        """
        URL the badge should link to.

        Currently always prioritises Platform.website_url: APIs don't
        always resolve the exact per-event deep-link (event_url/vod_url
        may be empty), which previously left buttons showing "link not
        available" even though the event was being broadcast. Falling back
        to the platform homepage (which always exists) is safer than an
        exact link that might be missing. If data sources start reliably
        providing deep-links in the future, just reorder the fallback chain
        here to prioritise them again.
        """
        return self.platform.website_url or self.vod_url or self.event_url
