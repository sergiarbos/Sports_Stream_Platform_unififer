import re
import unicodedata
from datetime import timedelta

from django.utils import timezone

from .models import Event

PLATFORM_CODES = {
    "dazn": "DAZN",
    "movistar-plus": "M+",
    "espn": "ESPN",
    "vix": "ViX",
    "eurosport": "E",
    "rtve-play": "TVE",
    "bein-sports": "beIN",
}

ACRONYM_PREFIXES = {
    "fc": "FC",
    "fk": "FK",
    "psv": "PSV",
    "ssc": "SSC",
    "sk": "SK",
    "vfb": "VfB",
    "as": "AS",
    "ac": "AC",
}

COMPETITION_FLAGS = {
    "champions-league": "🇪🇺",
    "champions": "🇪🇺",
    "europa-league": "🇪🇺",
    "europa": "🇪🇺",
    "conference-league": "🇪🇺",
    "la-liga": "🇪🇸",
    "laliga": "🇪🇸",
    "copa-del-rey": "🇪🇸",
    "premier-league": "🇬🇧",
    "premier": "🇬🇧",
    "serie-a": "🇮🇹",
    "seriea": "🇮🇹",
    "coppa-italia": "🇮🇹",
    "bundesliga": "🇩🇪",
    "ligue-1": "🇫🇷",
    "ligue1": "🇫🇷",
    "nba": "🇺🇸",
    "f1": "🏁",
    "motogp": "🏁",
}

TEAM_STYLES = {
    "barcelona": ("Barcelona", "FCB", "#a50044", "#004d98"),
    "fc barcelona": ("Barcelona", "FCB", "#a50044", "#004d98"),
    "real madrid": ("Real Madrid", "RM", "#d4af37", "#4c3a11"),
    "atletico de madrid": ("Atlético", "ATM", "#cb3524", "#7f1d1d"),
    "club atletico de madrid": ("Atlético", "ATM", "#cb3524", "#7f1d1d"),
    "atletico": ("Atlético", "ATM", "#cb3524", "#7f1d1d"),
    "inter de milan": ("Inter", "INT", "#0068a8", "#111827"),
    "fc internazionale milano": ("Inter", "INT", "#0068a8", "#111827"),
    "internazionale": ("Inter", "INT", "#0068a8", "#111827"),
    "inter": ("Inter", "INT", "#0068a8", "#111827"),
    "psg": ("PSG", "PSG", "#004170", "#da291c"),
    "paris saint germain": ("PSG", "PSG", "#004170", "#da291c"),
    "manchester city": ("Man. City", "MC", "#3cbcfc", "#1d2b4f"),
    "manchester united": ("Man. Utd", "MU", "#da291c", "#111827"),
    "liverpool": ("Liverpool", "LFC", "#c8102e", "#7f0f1f"),
    "arsenal": ("Arsenal", "ARS", "#ef0107", "#7f0f1f"),
    "juventus": ("Juventus", "JUV", "#1c1c1c", "#4b4b4b"),
    "milan": ("Milan", "MIL", "#c8102e", "#111827"),
    "roma": ("Roma", "ASR", "#8e1f2f", "#b45309"),
    "napoli": ("SSC Napoli", "SSC", "#12a0d7", "#1c4c78"),
    "ssc napoli": ("SSC Napoli", "SSC", "#12a0d7", "#1c4c78"),
    "sevilla": ("Sevilla", "SEV", "#d10714", "#7f1d1d"),
    "real sociedad": ("Real Sociedad", "RS", "#3f7d34", "#123b1b"),
    "valencia": ("Valencia", "VAL", "#f18e00", "#1f2937"),
    "villarreal": ("Villarreal", "VIL", "#fde100", "#1f2937"),
    "villarreal cf": ("Villarreal", "VIL", "#fde100", "#1f2937"),
    "betis": ("Betis", "BET", "#22c55e", "#14532d"),
    "dortmund": ("Dortmund", "BVB", "#fde100", "#1c1c1c"),
    "vfb stuttgart": ("VfB Stuttgart", "VFB", "#d8232a", "#111827"),
    "bayern munich": ("Bayern", "FCB", "#dc052d", "#5b0f1b"),
    "marseille": ("Marsella", "OM", "#2fabd8", "#ffffff"),
    "psv": ("PSV", "PSV", "#e30613", "#7f1d1d"),
    "sabah fk": ("Sabah FK", "SF", "#065f46", "#022c22"),
    "viking fk": ("Viking FK", "VF", "#1e3a8a", "#0f172a"),
    "slavia praga": ("SK Slavia Praha", "SLA", "#d10714", "#ffffff"),
    "slavia praha": ("SK Slavia Praha", "SLA", "#d10714", "#ffffff"),
    "sk slavia praha": ("SK Slavia Praha", "SLA", "#d10714", "#ffffff"),
    "sk slovan bratislava": ("SK Slovan", "SKS", "#1d4ed8", "#0f172a"),
    "porto": ("Porto", "FCP", "#00428c", "#2e2e2e"),
}

IGNORED_TEAM_WORDS = {"fc", "cf", "ac", "as", "if", "club", "de", "del", "la", "el", "the"}
TEAM_ACRONYM_RE = re.compile(r"\b(sv|kv|osc|fk|fc|vfb|psv|ssc|sk)\b", re.IGNORECASE)
SESSION_LABELS = {
    "free practice 1": "FP1",
    "free practice 2": "FP2",
    "free practice 3": "FP3",
    "sprint qualifying": "SPR Q",
    "qualifying": "QUALY",
}


def normalize_team_name(name):
    text = unicodedata.normalize("NFKD", str(name or ""))
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def team_style(name):
    normalized = normalize_team_name(name)
    if normalized in TEAM_STYLES:
        return TEAM_STYLES[normalized]

    raw_words = normalized.split()
    prefix = ACRONYM_PREFIXES.get(raw_words[0], "") if raw_words else ""
    source_words = raw_words[1:] if prefix else raw_words
    words = [word for word in source_words if word not in IGNORED_TEAM_WORDS]
    short_words = [word.capitalize() for word in words[:3]]
    if prefix:
        short_words = [prefix, *short_words[:2]]
    short = " ".join(short_words) or str(name or "")
    initials = "".join(word[:1] for word in words[:3]).upper()
    if len(initials) == 1:
        initials = words[0][:2].upper() if words else "?"
    if prefix and len(initials) < 2:
        initials = prefix[:2].upper()
    return (short, initials[:3], "#52525b", "#18181b")


def short_team_name(name):
    return TEAM_ACRONYM_RE.sub(lambda match: match.group(1).upper(), team_style(name)[0])


def team_initials(name):
    return team_style(name)[1]


def session_label(event):
    title = str(getattr(event, "title", "") or "")
    if " · " not in title:
        return ""
    session = title.split(" · ", 1)[1].strip()
    return SESSION_LABELS.get(session.lower(), session)


def favorite_key(value):
    return normalize_team_name(value).replace(" ", "-")


def favorite_keys(event):
    values = (
        getattr(event, "participant_home", ""),
        getattr(event, "participant_away", ""),
        getattr(event.competition, "name", ""),
        getattr(event.competition, "slug", ""),
    )
    return " ".join(dict.fromkeys(favorite_key(value) for value in values if value))


def result_note(event):
    result_text = (getattr(event, "result_text", "") or "").strip()
    round_name = (getattr(event, "round_name", "") or "").strip()
    if result_text and not result_text.isdigit():
        return result_text
    sport = getattr(getattr(event, "competition", None), "sport", None)
    if getattr(sport, "category", "") == "motorsport":
        return ""
    if round_name and not round_name.isdigit() and round_name.lower() != result_text.lower():
        return round_name
    return ""


def local_timezone_label():
    abbreviation = timezone.localtime(timezone.now()).strftime("%Z") or "LOCAL"
    return f"HORA LOCAL ({abbreviation})"


def _luminance(hex_color):
    value = str(hex_color or "").strip().lstrip("#")
    if len(value) != 6:
        return 0.0
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def team_text_style(name):
    _, _, light, dark = team_style(name)
    if (_luminance(light) + _luminance(dark)) / 2 > 0.28:
        return "#0a0a0a", "0 1px 0 rgba(255, 255, 255, 0.25)"
    return "#ffffff", "0 1px 3px rgba(0, 0, 0, 0.8)"


def team_colors(name):
    _, _, light, dark = team_style(name)
    text, shadow = team_text_style(name)
    return (
        f"--team-c1: {light}; --team-c2: {dark}; " f"--team-text: {text}; --team-shadow: {shadow}"
    )


def platform_code(platform):
    slug = getattr(platform, "slug", str(platform or "")).lower()
    if slug in PLATFORM_CODES:
        return PLATFORM_CODES[slug]
    name = str(getattr(platform, "name", platform or ""))
    return name[:3].upper() or "?"


def broadcast_meta(broadcast):
    platform = broadcast.platform
    notes = (broadcast.notes or "").strip()
    if notes:
        detail = notes
    elif not platform.requires_subscription:
        detail = "EN ABIERTO"
    elif platform.slug == "movistar-plus":
        competition = getattr(broadcast.event, "competition", None)
        code = getattr(competition, "short_code", "") or (
            competition.badge_initials if competition else ""
        )
        detail = f"M+ {code}".strip()
    else:
        detail = "SUSCRIPCIÓN"
    language = str(broadcast.language or "")[:2].upper() or "ES"
    return f"HD · {detail} · {language}"


def live_minute(event):
    if getattr(event, "status", None) != Event.STATUS_LIVE:
        return ""
    elapsed = int((timezone.now() - event.start_datetime).total_seconds() // 60)
    return f"{max(1, min(elapsed, 90))}'"


def result_detail(event):
    parts = [timezone.localtime(event.start_datetime).strftime("%d/%m %H:%M")]
    text = (event.result_text or "").lower()
    if "pen" in text:
        parts.append("PEN.")
    elif "aet" in text or "extra" in text:
        parts.append("PRÓRROGA")
    return " · ".join(parts)


def competition_flag(competition):
    """Emoji flag for a competition slug (usable without copyrighted logos)."""
    slug = getattr(competition, "slug", competition)
    return COMPETITION_FLAGS.get(str(slug).lower(), "")


def competition_section_label(event):
    """Compact label used once per competition/round group, not on every row."""
    parts = [event.competition.name.upper()]
    if event.round_name:
        parts.append(event.round_name.upper())
    flag = competition_flag(event.competition)
    return f"{flag} {' · '.join(parts)}".strip()


def mark_competition_sections(events):
    """Flag the first row of each competition/round run inside a date group."""
    previous_key = None
    previous_date = None
    for event in events:
        event_date = timezone.localtime(event.start_datetime).date()
        key = (event.competition_id, event.round_name or "", event_date)
        event.is_competition_start = key != previous_key or event_date != previous_date
        event.competition_section_label = competition_section_label(event)
        previous_key = key
        previous_date = event_date


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
