"""
Data adapter architecture.

Each external source (paid API, free API, or a future scraper you want
to write yourself) is implemented as a subclass of BaseSourceAdapter
with a single method: fetch_events().

This allows adding new sources without touching the views or models,
and switching data providers without rewriting the rest of the project.

NOTE on DAZN and Movistar Plus+
---------------------------------
Neither service offers a public/official API to query their schedule.
The only way to obtain that data would be through web scraping (reading
their HTML and extracting information), which:

  1. May violate their Terms of Service.
  2. Breaks easily whenever they redesign their site.
  3. Is not something that should be automated without you actively
     deciding to do so and reviewing their legal terms first.

This project therefore does NOT include a ready-to-use DAZN/Movistar
scraper. What it does include is the exact hook (see ManualSourceAdapter
below) where you could plug in your own scraper if you choose to do so
under your own responsibility, alongside real adapters for legal open
sports APIs that cover most of the same calendar.
"""

from abc import ABC, abstractmethod


class BaseSourceAdapter(ABC):
    """Interface that every data source must implement."""

    #: Must match the Competition.source field set in the seeder/admin.
    source_id = "base"

    @abstractmethod
    def fetch_events(self, **kwargs):
        """
        Must return a list of dicts containing at minimum the keys:
            title, start_datetime (timezone-aware), status, external_id
        Extra keys are safely ignored by the caller.
        """
        raise NotImplementedError


class ManualSourceAdapter(BaseSourceAdapter):
    """
    Empty adapter for competitions managed manually through the admin
    panel (/admin/) — for example winter sports, where no decent free
    API exists.

    This is also the recommended place to plug in your own
    DAZN/Movistar+ scraper if you decide to build one (see legal notice
    above).
    """

    source_id = "manual"

    def fetch_events(self, **kwargs):
        return []
