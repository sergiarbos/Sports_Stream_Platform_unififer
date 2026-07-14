"""
Adapter for a tennis API (e.g. api-tennis.com via RapidAPI).
Covers Wimbledon, ATP, WTA, Grand Slams, etc.

⚠️ PRIVATE KEY — DO NOT PUBLISH
---------------------------------
Same as API-Football: the key identifies your personal account/quota.
It must live only in .env (variable API_TENNIS_KEY) and never in the
code or the repository.

This adapter is a skeleton: adapt the endpoint names/parameters to
whichever tennis provider you choose, as they vary quite a lot between
providers (unlike football, there is no widely adopted standard).
"""

from django.conf import settings

from .adapters import BaseSourceAdapter


class ApiTennisAdapter(BaseSourceAdapter):
    source_id = "api_tennis"

    def fetch_events(self, tournament="wimbledon", **kwargs):
        api_key = settings.API_TENNIS_KEY
        if not api_key:
            raise RuntimeError(
                "API_TENNIS_KEY is missing from your .env file. "
                "Choose a provider (e.g. api-tennis.com) and add your key to .env."
            )

        # TODO: replace with the real endpoint for your chosen provider.
        # response = requests.get(..., headers={"X-RapidAPI-Key": api_key})
        raise NotImplementedError(
            "Implement the call to your chosen tennis provider here. "
            "The key is already read safely from settings.API_TENNIS_KEY."
        )
