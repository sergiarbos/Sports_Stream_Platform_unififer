from django.db import models
from django.utils import timezone


class Sport(models.Model):
    """Top-level sport category (Football, Basketball, Motorsport, Tennis, Winter sports...)."""

    CATEGORY_FOOTBALL = "football"
    CATEGORY_BASKETBALL = "basketball"
    CATEGORY_MOTORSPORT = "motorsport"
    CATEGORY_TENNIS = "tennis"
    CATEGORY_WINTER = "winter_sports"

    CATEGORY_CHOICES = [
        (CATEGORY_FOOTBALL, "Fútbol"),
        (CATEGORY_BASKETBALL, "Baloncesto"),
        (CATEGORY_MOTORSPORT, "Motor"),
        (CATEGORY_TENNIS, "Tenis"),
        (CATEGORY_WINTER, "Deportes de invierno"),
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


class Competition(models.Model):
    """A specific competition within a sport (Champions League, NBA, F1...)."""

    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="competitions")
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    # Identifies which data source/adapter this competition uses.
    # See schedule/services/adapters.py for the list of supported sources.
    source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Data adapter identifier (e.g. 'thesportsdb', 'jolpica_f1', 'manual').",
    )
    external_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["sport__order", "name"]
        verbose_name_plural = "competitions"

    def __str__(self):
        return f"{self.name} ({self.sport.name})"


class Platform(models.Model):
    """Platform where the event can be watched (DAZN, Movistar Plus+, ESPN, ViX...)."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    website_url = models.URLField(blank=True)
    # Hex colour used to render the badge in the UI, avoiding the need
    # to host copyrighted logos for each platform.
    color = models.CharField(max_length=7, default="#2563eb")
    requires_subscription = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Event(models.Model):
    """A concrete sports event: a match, a race, a session..."""

    STATUS_SCHEDULED = "scheduled"
    STATUS_LIVE = "live"
    STATUS_FINISHED = "finished"

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Programado"),
        (STATUS_LIVE, "En directo"),
        (STATUS_FINISHED, "Finalizado"),
    ]

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

    class Meta:
        ordering = ["start_datetime"]

    def __str__(self):
        return f"{self.title} - {self.start_datetime:%d/%m/%Y %H:%M}"

    @property
    def is_past(self):
        return self.start_datetime < timezone.now() and self.status != Event.STATUS_LIVE

    @property
    def spanish_broadcasts(self):
        """Only broadcasts with Spanish-language commentary."""
        return self.broadcasts.filter(language__startswith="es")

    @property
    def is_visible(self):
        """
        Core project rule:
        - If the event is upcoming or live -> always shown (with its schedule).
        - If the event has already finished -> only shown if AT LEAST one
          Spanish-language broadcast has a replay/VOD available.
        """
        broadcasts = self.spanish_broadcasts
        if not broadcasts.exists():
            return False
        if self.status == Event.STATUS_FINISHED:
            return broadcasts.filter(vod_available=True).exists()
        return True


class Broadcast(models.Model):
    """Event <-> platform relationship: where and how a given event can be watched."""

    LANGUAGE_ES_ES = "es-ES"
    LANGUAGE_ES_LA = "es-LA"

    LANGUAGE_CHOICES = [
        (LANGUAGE_ES_ES, "Español (España)"),
        (LANGUAGE_ES_LA, "Español (Latinoamérica)"),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="broadcasts")
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name="broadcasts")
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default=LANGUAGE_ES_ES)
    commentary_region = models.CharField(
        max_length=80,
        blank=True,
        help_text="Optional, e.g. 'Mexico', 'Argentina', 'Pan-Latin America'.",
    )
    is_live_stream = models.BooleanField(
        default=True, help_text="Does this platform broadcast it live?"
    )
    vod_available = models.BooleanField(
        default=False,
        help_text="Is a replay/VOD available once the event has finished?",
    )
    vod_url = models.URLField(blank=True)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("event", "platform", "language")
        ordering = ["platform__name"]

    def __str__(self):
        return f"{self.event} on {self.platform} ({self.get_language_display()})"

    @property
    def is_latam(self):
        return self.language == Broadcast.LANGUAGE_ES_LA
