# Results Section Documentation

This document explains the architecture and functionality of the newly added **Results Section** (Resultados) in the Sports Stream Platform Unifier.

## Overview

The Results section allows users to view the final outcomes of past sporting events, specifically focusing on **Football** and **Motorsport (Formula 1)**.

Users can toggle between the standard "LINKS" mode (which shows upcoming/live streams) and the "RESULTADOS" mode using the top navigation tabs. When the Results mode is active, platform filters are hidden, as the focus shifts to post-match data rather than where to watch it.

## 1. Data Retrieval and Storage (Basic Results)

The system relies on Background Sync Adapters to fetch the schedule. These adapters have been enhanced to also capture basic result data when an event finishes.

### Football (API-Football)
- During the regular sync (`python manage.py import_all_sports`), the `ApiFootballAdapter` checks if a fixture is marked as finished.
- If finished, it automatically extracts `goals.home` and `goals.away` from the API response.
- These values are stored in the database fields `score_home` and `score_away` of the `Event` model.

### Formula 1 (Jolpica F1)
- The `JolpicaF1Adapter` makes an additional request to the `/results.json` endpoint for the current season.
- For each completed race, it extracts the Top 3 drivers (e.g., "1º Russell, 2º Antonelli, 3º Leclerc").
- This string is stored in the `result_text` field of the `Event` model.

### Static / Manual Events
- For competitions updated via JSON files (like MotoGP or Winter Sports), the `static_calendar.py` adapter now parses `score_home`, `score_away`, and `result_text` directly from the JSON dictionaries.

## 2. Display Logic & Filtering

When the user switches to `?view_mode=results`, the following rules apply:

- **Sport Filtering:** Only events categorized as `football` or `motorsport` are shown.
- **Status:** Only events with `STATUS_FINISHED` are displayed.
- **Time Limits (The 14-Day Rule):**
  - **Football:** The queryset is strictly filtered to only show matches that have concluded within the **last 14 days**.
  - **Motorsport (F1):** The 14-day limit is bypassed. The system will load all finished races from the current season.
- **Exclusions:** The World Cup (`mundial-2026`) is explicitly excluded from the results view, as there is no direct, free API available to reliably fetch its historical results in this implementation.

## 3. UI/UX Design (The Glassmorphism Row)

The results list is designed with a premium, frosted glass aesthetic:
- **No Scores on the Main View for F1:** To keep the interface clean, F1 events only show the Grand Prix name (with a dynamically generated country flag) and the session.
- **Football Scores:** Football matches display the actual score (`X - Y`) enclosed in a subtle translucent box.
- **Dynamic Flags:** A custom Django template filter (`f1_flags.py`) automatically parses the name of the F1 Grand Prix and prepends the corresponding country's emoji flag to the title.

## 4. The Live Details Page (`/results/<id>/`)

Clicking the "VER DETALLES COMPLETOS" button does not just expand a dropdown; it redirects the user to a dedicated details page.

**Live API Fetching:**
To prevent database bloat, we do not store every single statistic, yellow card, or lap time in our local SQLite database. Instead:
1. The `event_details` view receives the local `Event` ID.
2. It looks up the `external_id` (e.g., the API-Football fixture ID or the Jolpica round number).
3. **It makes a live HTTP request** directly to the respective third-party API at the moment the user loads the page.
4. The rich data (referees, stadiums, full race grids, constructors, points) is then passed to the template and rendered beautifully.

> **Note:** For the Football details to work, a valid `API_FOOTBALL_KEY` must be present in your `.env` file. F1 (Jolpica) requires no key.
