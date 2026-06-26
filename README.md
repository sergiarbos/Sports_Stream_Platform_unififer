# SportLink

**SportLink** tells you which platform you can watch a sports event on (with
Spanish-language commentary), whether it is live right now, when it starts if
it hasn't begun yet, or whether you can watch a replay if it has already
finished. If a past event has no replay available anywhere, it simply isn't
shown.

A Django project designed to run locally first. Later (phase 2) it can be
wrapped in an Android Studio app that consumes the same data.

## Table of Contents

1. [Project rules](#project-rules)
2. [Architecture](#architecture)
3. [Local installation and setup](#local-installation-and-setup)
4. [APIs used: what you can publish and what you can't](#apis-used-what-you-can-publish-and-what-you-cant)
5. [Legal notice about DAZN / Movistar Plus+](#legal-notice-about-dazn--movistar-plus)
6. [Pushing the project to GitHub](#pushing-the-project-to-github)
7. [Phase 2: Android app](#phase-2-android-app)

## Project rules

Implemented in `schedule/models.py` (properties `Event.is_visible` and
`Event.spanish_broadcasts`):

1. Only events with **at least one Spanish-language broadcast** are listed
   (Spain or Latin America).
2. If the broadcast is in Latin American Spanish, a small icon is displayed
   next to the platform name (`Broadcast.language == "es-LA"`).
3. **Upcoming or live** events → always visible, showing their date/time
   (in the "Upcoming · schedule" section) or with a "● LIVE" badge.
4. **Past** events → only visible if a replay/VOD is available
   (`vod_available=True`) on at least one platform. Otherwise they are hidden.

Sports and competitions included as examples: Football (Champions League,
Europa League, World Cup 2026, LaLiga, Premier League, Serie A, Bundesliga,
Ligue 1), Basketball (NBA), Motorsport (F1, MotoGP), Tennis (Wimbledon) and
Winter sports (alpine skiing/slalom, ski jumping, cross-country skiing).

## Architecture

```
streamsync_repo/
├── manage.py
├── requirements.txt
├── .env.example          <- public template (IS committed to the repo)
├── .gitignore            <- excludes the real .env file
├── streamsync/           <- project configuration (settings, urls)
├── templates/base.html   <- shared template (header, fonts, CSS)
├── static/css/style.css  <- all visual identity
└── schedule/             <- the main app
    ├── models.py         <- Sport, Competition, Platform, Event, Broadcast
    ├── views.py          <- single view grouping live/upcoming/VOD sections
    ├── admin.py          <- for adding/editing events manually
    ├── templates/schedule/ <- home.html + partials (event card, LatAm icon)
    ├── services/         <- one adapter per external data source
    │   ├── adapters.py   <- shared interface (BaseSourceAdapter)
    │   ├── jolpica_f1.py <- REAL and functional, F1, no key required
    │   ├── api_football.py  <- skeleton, football, requires private key
    │   ├── thesportsdb.py   <- covers NBA/MotoGP/football, public test key
    │   └── api_tennis.py    <- skeleton, tennis, requires private key
    └── management/commands/
        ├── seed_demo_data.py      <- sample data (no API needed)
        ├── import_f1_calendar.py  <- demonstrates the F1 adapter working for real
        └── import_all_sports.py   <- imports all sports from all APIs at once
```

Each data source (paid API, free API, or something you add later) is an
independent **adapter** with a single `fetch_events()` method. This lets you
add or swap sources without touching the views or templates: you simply connect
the adapter's output with `Event.objects.update_or_create(...)`, exactly as
`import_all_sports.py` does.

## Local installation and setup

Requires Python 3.11+.

```bash
git clone <your-repository>
cd streamsync

python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # fill in any keys you want to use (optional at first)

python manage.py migrate
python manage.py seed_demo_data # creates sports, platforms and ~19 sample events

python manage.py runserver
```

Open `http://127.0.0.1:8000/` and you should see the site running with sample
data, without having configured any API yet.

To access the admin panel and add/edit events manually:

```bash
python manage.py createsuperuser
```

Then go to `http://127.0.0.1:8000/admin/`.

To import real data from all APIs at once (F1 requires no key at all):

```bash
python manage.py import_all_sports
```

Or to import only a specific sport:

```bash
python manage.py import_all_sports --sport f1
python manage.py import_all_sports --sport motogp
python manage.py import_all_sports --sport la-liga
```

## APIs used: what you can publish and what you can't

DAZN and Movistar Plus+ have no public API, so the schedule is reconstructed
by combining several real, open sports APIs plus whatever you add manually
from `/admin/`. Summary:

| Source | Covers | Key required? | Safe to publish on GitHub? |
|---|---|---|---|
| **Jolpica F1** (successor to Ergast) | F1 calendar + all sessions | No | ✅ Yes — no key at all, 100% open |
| **TheSportsDB** | NBA, MotoGP, football leagues | Public test key: `3` | ✅ Yes, that test key is officially public and shared. If you upgrade to a paid Patreon key (more requests, live scores), that one must **not** be published |
| **API-Football** | Champions, Europa League, World Cup, LaLiga, Premier, Serie A, Bundesliga, Ligue 1 | Personal key (free tier: 100 requests/day) | ❌ No — it identifies your account and quota. Keep it only in `.env` |
| **Tennis provider** (your choice, e.g. api-tennis.com) | Wimbledon, ATP, WTA | Personal key | ❌ No — only in `.env` |
| Winter sports (alpine skiing, ski jumping, cross-country) | — | — | No decent free API exists; events are entered manually from `/admin/` (`ManualSourceAdapter`) |

General rule: **any key that identifies your personal account or request quota
is private** and belongs only in your real `.env` file (which is in
`.gitignore` and never pushed). Test keys that the provider itself publishes
as shared (like TheSportsDB's `3`) are safe to keep in the repository,
although we still put them in `.env` for cleanliness and easy replacement.

## Legal notice about DAZN / Movistar Plus+

Neither platform offers a public API to query their schedule. The only way to
pull that data directly from their sites would be through *scraping* (reading
their HTML), and that:

- may violate their Terms of Service,
- breaks every time they redesign their site,
- is not something that should be automated without you actively deciding to do
  so and reviewing their legal terms first.

This project therefore does **not** include a ready-to-use DAZN/Movistar+
scraper. Instead:

- Use the real sports APIs from the table above to find out **what** the event
  is and **when** it takes place.
- You manually add, from `/admin/`, **which platform** it can be watched on
  (you look this up yourself on their sites/apps, as you would normally).
- If you decide to write your own scraper in the future under your own
  responsibility, the right place to plug it into the architecture is
  `ManualSourceAdapter` in `schedule/services/adapters.py`.

## Pushing the project to GitHub

```bash
git init
git add .
git commit -m "Initial SportLink release"
git branch -M main
git remote add origin <your-repository-url>
git push -u origin main
```

## Phase 2: Android app

The Django backend exposes data through standard views. In a future phase, the
project can be extended with a REST API (e.g. Django REST Framework) so that
an Android Studio app can consume the same event data natively.
