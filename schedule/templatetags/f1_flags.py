from django import template

register = template.Library()

FLAGS = {
    "bahrain": "🇧🇭",
    "saudi": "🇸🇦",
    "australian": "🇦🇺",
    "japanese": "🇯🇵",
    "chinese": "🇨🇳",
    "miami": "🇺🇸",
    "emilia": "🇮🇹",
    "monaco": "🇲🇨",
    "mónaco": "🇲🇨",
    "canadian": "🇨🇦",
    "spanish": "🇪🇸",
    "españa": "🇪🇸",
    "austrian": "🇦🇹",
    "british": "🇬🇧",
    "gran bretaña": "🇬🇧",
    "hungarian": "🇭🇺",
    "belgian": "🇧🇪",
    "dutch": "🇳🇱",
    "netherlands": "🇳🇱",
    "italian": "🇮🇹",
    "azerbaijan": "🇦🇿",
    "singapore": "🇸🇬",
    "united states": "🇺🇸",
    "mexican": "🇲🇽",
    "são paulo": "🇧🇷",
    "brazilian": "🇧🇷",
    "las vegas": "🇺🇸",
    "qatar": "🇶🇦",
    "abu dhabi": "🇦🇪"
}

@register.filter
def add_flag(title):
    """
    Looks for a country/location name in the title and prepends the corresponding flag.
    """
    if not title:
        return title
        
    lower_title = title.lower()
    for key, flag in FLAGS.items():
        if key in lower_title:
            return f"{flag} {title}"
            
    return title
