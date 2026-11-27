from django import template

from schedule.utils import (
    broadcast_meta as broadcast_meta_util,
)
from schedule.utils import (
    competition_flag,
    short_team_name,
    team_colors,
    team_initials,
)
from schedule.utils import (
    live_minute as live_minute_util,
)
from schedule.utils import (
    local_timezone_label as local_timezone_label_util,
)
from schedule.utils import (
    platform_code as platform_code_util,
)
from schedule.utils import (
    result_detail as result_detail_util,
)
from schedule.utils import (
    result_note as result_note_util,
)
from schedule.utils import (
    session_label as session_label_util,
)

register = template.Library()


@register.filter
def team_short(name):
    """Short, widely used club name (full name is kept in the title tooltip)."""
    return short_team_name(name)


@register.filter
def team_code(name):
    return team_initials(name)


@register.filter
def team_gradient(name):
    """CSS custom properties with the club's two main colours."""
    return team_colors(name)


@register.filter
def comp_flag(competition):
    return competition_flag(competition)


@register.filter
def platform_code(platform):
    return platform_code_util(platform)


@register.filter
def broadcast_meta(broadcast):
    return broadcast_meta_util(broadcast)


@register.filter
def live_minute(event):
    return live_minute_util(event)


@register.filter
def result_detail(event):
    return result_detail_util(event)


@register.filter
def es_broadcasts(event):
    broadcasts = event.broadcasts.all()
    return [broadcast for broadcast in broadcasts if broadcast.language.startswith("es")][:2]


@register.filter
def session_label(event):
    return session_label_util(event)


@register.filter
def result_note(event):
    return result_note_util(event)


@register.simple_tag
def local_timezone_label():
    return local_timezone_label_util()
