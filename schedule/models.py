from django.db import models
from django.utils import timezone


class Sport(models.Model):
    """Categoría deportiva de alto nivel (Fútbol, Baloncesto, Motor, Tenis, Invierno...)."""

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
        help_text="Emoji usado como icono rápido en la interfaz (ej: ⚽).",
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def accent_class(self):
        """Clase CSS de color por categoría, usada en monogramas y tarjetas destacadas."""
        return f"accent-{self.category}"


class Competition(models.Model):
    """Competición concreta dentro de un deporte (Champions, NBA, F1...)."""

    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="competitions")
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    short_code = models.CharField(
        max_length=6,
        blank=True,
        help_text=(
            "Siglas cortas para la insignia visual de la competición (ej: 'CL', "
            "'NBA', 'F1'). Se usan en vez de logotipos con copyright."
        ),
    )
    # Identifica de qué fuente/adaptador de datos proviene esta competición.
    # Ver schedule/services/adapters.py para la lista de fuentes soportadas.
    source = models.CharField(
        max_length=50,
        blank=True,
        help_text="Identificador del adaptador de datos (ej: 'api_football', 'jolpica_f1', 'manual').",
    )
    external_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["sport__order", "name"]
        verbose_name_plural = "competitions"

    def __str__(self):
        return f"{self.name} ({self.sport.name})"

    @property
    def badge_initials(self):
        """Siglas a mostrar en la insignia visual si no se definió short_code."""
        if self.short_code:
            return self.short_code
        words = [w for w in self.name.split() if w.lower() not in ("de", "del", "la", "el")]
        return "".join(w[0] for w in words[:3]).upper()


class Platform(models.Model):
    """Plataforma donde se puede ver el evento (DAZN, Movistar Plus+, ESPN, ViX...)."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    website_url = models.URLField(blank=True)
    # Color en hexadecimal para pintar la insignia en la interfaz, evitando
    # tener que alojar logotipos con derechos de autor de cada plataforma.
    color = models.CharField(max_length=7, default="#2563eb")
    requires_subscription = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Event(models.Model):
    """Un acontecimiento deportivo concreto: un partido, una carrera, una prueba..."""

    STATUS_SCHEDULED = "scheduled"
    STATUS_LIVE = "live"
    STATUS_FINISHED = "finished"

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Programado"),
        (STATUS_LIVE, "En directo"),
        (STATUS_FINISHED, "Finalizado"),
    ]

    # Nº de días que un evento finalizado permanece en "Disponibles en diferido"
    # antes de desaparecer del listado (aunque siga teniendo VOD disponible).
    ARCHIVE_WINDOW_DAYS = 7

    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(
        max_length=200,
        help_text="Ej: 'Real Madrid vs Manchester City' o 'Gran Premio de Mónaco'.",
    )
    participant_home = models.CharField(max_length=120, blank=True)
    participant_away = models.CharField(max_length=120, blank=True)
    start_datetime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)
    external_id = models.CharField(max_length=100, blank=True)
    round_name = models.CharField(
        max_length=120, blank=True, help_text="Ej: 'Jornada 12', 'Octavos de final', 'Clasificación'."
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
        """¿Este evento finalizado cayó dentro de los últimos ARCHIVE_WINDOW_DAYS días?"""
        cutoff = timezone.now() - timezone.timedelta(days=Event.ARCHIVE_WINDOW_DAYS)
        return self.start_datetime >= cutoff

    @property
    def spanish_broadcasts(self):
        """Solo las retransmisiones con comentarios en español."""
        return self.broadcasts.filter(language__startswith="es")

    @property
    def is_visible(self):
        """
        Regla central del proyecto:
        - Si el evento es futuro o está en directo -> se muestra siempre (con su horario).
        - Si el evento ya ha pasado -> solo se muestra si existe AL MENOS una
          retransmisión en español con repetición/VOD disponible, Y además
          el evento ocurrió dentro de los últimos ARCHIVE_WINDOW_DAYS días
          (pasado ese plazo, desaparece de "Disponibles en diferido").
        """
        broadcasts = self.spanish_broadcasts
        if not broadcasts.exists():
            return False
        if self.status == Event.STATUS_FINISHED:
            return broadcasts.filter(vod_available=True).exists() and self.is_within_archive_window
        return True

    @property
    def status_label(self):
        if self.status == Event.STATUS_LIVE:
            return "DIRECTO"
        if self.status == Event.STATUS_FINISHED:
            return "DIFERIDO"
        return "PRÓXIMO"


class Broadcast(models.Model):
    """Relación evento <-> plataforma: dónde y cómo se puede ver/escuchar ese evento."""

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
        help_text="Opcional, ej: 'México', 'Argentina', 'Conjunta Latam'.",
    )
    is_live_stream = models.BooleanField(
        default=True, help_text="¿Esta plataforma lo retransmite en directo?"
    )
    event_url = models.URLField(
        blank=True,
        help_text=(
            "Link directo a ESTE evento concreto dentro de la plataforma "
            "(no a la home general). Se usa para directo/próximos."
        ),
    )
    vod_available = models.BooleanField(
        default=False,
        help_text="¿Hay repetición/diferido disponible una vez finalizado el evento?",
    )
    vod_url = models.URLField(
        blank=True, help_text="Link directo a la repetición/diferido de ESTE evento."
    )
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("event", "platform", "language")
        ordering = ["platform__name"]

    def __str__(self):
        return f"{self.event} en {self.platform} ({self.get_language_display()})"

    @property
    def is_latam(self):
        return self.language == Broadcast.LANGUAGE_ES_LA

    @property
    def direct_url(self):
        """
        Link al que debe apuntar la insignia en la interfaz.

        Por ahora prioriza SIEMPRE Platform.website_url: las APIs no
        siempre consiguen resolver el link exacto del evento dentro de
        la plataforma (event_url/vod_url quedan vacíos), y eso dejaba
        botones en "enlace no disponible" aunque el evento sí se
        retransmitiera. Ir a lo seguro (la home, que siempre existe) es
        mejor que un link exacto que puede fallar. Si en el futuro las
        fuentes de datos resuelven bien el link profundo, basta con
        cambiar el orden aquí para volver a priorizarlo.
        """
        return self.platform.website_url or self.vod_url or self.event_url
