# Sports Broadcast Aggregator

**Live Demo**: [sports-stream-platform-unififer.onrender.com](https://sports-stream-platform-unififer.onrender.com)

Tells you on which platform you can watch a sporting event (with
Spanish-language commentary), whether it is live right now, when it starts if
it hasn't begun yet, or whether you can watch a replay if it has already
finished. If a past event has no replay available anywhere, it is simply not
shown.

Django project designed to run locally first. Later (phase 2) it can be
wrapped in an Android Studio app that consumes the same data.

## Table of contents

1. [Project rules](#project-rules)
2. [Architecture](#architecture)
3. [Local installation and setup](#local-installation-and-setup)
4. [Deployment on Render](#deployment-on-render)
5. [APIs used: which ones you can publish and which ones you cannot](#apis-used-which-ones-you-can-publish-and-which-ones-you-cannot)
6. [Legal notice regarding DAZN / Movistar Plus+](#legal-notice-regarding-dazn--movistar-plus)
7. [Pushing the project to GitHub](#pushing-the-project-to-github)
8. [Phase 2: Android app](#phase-2-android-app)

## Project rules

Implemented in `schedule/models.py` (properties `Event.is_visible` and
`Event.spanish_broadcasts`):

1. Only events with **at least one Spanish-language broadcast** are listed
   (Spain or Latin America).
2. If the broadcast is in Latin American Spanish, a small icon is shown next
   to the platform name (`Broadcast.language == "es-LA"`).
3. **Upcoming or live** events → always visible (up to 365 days in the future), with their date/time
   (section "Upcoming · schedule") or with the "● LIVE" badge.
4. **Past** events → visible by default for **14 days** (in the "On Demand" section). After 14 days, they disappear automatically without exception.

Sports and competitions included as examples: Football (Champions League,
Europa League, 2026 World Cup, LaLiga, Premier League, Serie A, Bundesliga,
Ligue 1), Basketball (NBA), Motorsport (F1, MotoGP), Tennis (Wimbledon) and
Winter Sports (alpine/slalom skiing, ski jumping, cross-country skiing).

## Architecture

```
streamsync_repo/
├── manage.py
├── requirements.txt
├── .env.example          <- public template (IS committed to the repo)
├── .gitignore             <- the real .env is excluded here
├── streamsync/            <- project configuration (settings, urls)
├── templates/base.html    <- shared template (header, fonts, CSS)
├── static/css/style.css   <- all visual identity
└── schedule/               <- the main app
    ├── models.py           <- Sport, Competition, Platform, Event, Broadcast
    ├── views.py            <- single view that groups live/upcoming/on-demand
    ├── admin.py            <- for adding/editing events manually
    ├── templates/schedule/  <- home.html + partials (event card, LatAm icon)
    ├── services/            <- one adapter per external data source
    │   ├── adapters.py      <- common interface (BaseSourceAdapter)
    │   ├── jolpica_f1.py    <- REAL and functional, F1, no key required
    │   ├── api_football.py  <- skeleton, football, requires a private key
    │   ├── thesportsdb.py   <- skeleton, NBA, public test key
    │   ├── static_calendar.py <- static local calendar for MotoGP and World Cup to bypass API limits
    │   └── api_tennis.py    <- skeleton, tennis, requires a private key
    └── management/commands/
        ├── seed_demo_data.py     <- demo data (no API required)
        ├── import_all_sports.py  <- imports events from all configured APIs and static calendars
        └── import_f1_calendar.py <- demonstrates the F1 adapter working for real
```

Each data source (paid API, free API, or anything you add later) is an
independent **adapter** with a single `fetch_events()` method. This lets you
add or swap sources without touching the views or templates: you simply feed
the adapter's output into `Event.objects.update_or_create(...)`, exactly as
`import_f1_calendar.py` does.

## Local installation and setup

You need Python 3.11+.

```bash
git clone <your-repository>
cd streamsync

python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # then fill in the keys you want to use (optional at first)

python manage.py migrate
python manage.py seed_demo_data # creates sports, platforms and ~19 demo events

python manage.py runserver
```

Open `http://127.0.0.1:8000/` and you should see the site running with demo
data, without having configured any API yet.

To access the admin panel and add/edit events manually:

```bash
python manage.py createsuperuser
```

then go to `http://127.0.0.1:8000/admin/`.

To verify the system also works with a real API (no key required):

```bash
python manage.py import_f1_calendar
```

## Deployment on Render

This project is configured to run on Render.

- **Live URL**: `https://sports-stream-platform-unififer.onrender.com`
- **WSGI Server**: Uses `gunicorn` to serve the application in production.
- **Static Files**: Serves compressed static assets via `whitenoise`.
- **Dynamic Statuses**: The application dynamically computes event statuses based on the current wall-clock time relative to `start_datetime`, removing the need for a background task worker (like Huey) in serverless or free environments.

### Render Configuration

To deploy this project to Render as a Web Service:

1. **Build Command**:
   ```bash
   pip install -r requirements.txt && python manage.py migrate && python manage.py createcachetable && python manage.py collectstatic --noinput && python manage.py seed_demo_data --no-events && python manage.py import_all_sports
   ```
   *(This ensures that all DB tables, cache tables, and static files are ready, structural/seeding metadata is loaded without demo events, and the actual live data gets populated on every deployment).*

2. **Start Command**:
   ```bash
   gunicorn streamsync.wsgi:application
   ```

3. **Environment Variables**:
   In the Render dashboard, go to the environment settings and add the following keys:

   | Name | Value / Description |
   |---|---|
   | `DJANGO_SECRET_KEY` | Generate a secure key, e.g. with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
   | `DJANGO_DEBUG` | `False` |
   | `DJANGO_ALLOWED_HOSTS` | `sports-stream-platform-unififer.onrender.com` |
   | `THESPORTSDB_KEY` | `3` (Free public API key for sports data) |

## APIs used: which ones you can publish and which ones you cannot

Neither DAZN nor Movistar Plus+ offers a public API for their schedules. The
only way to pull that data directly from their sites would be through
*scraping* (reading their HTML), and that:

- may violate their Terms of Service,
- breaks every time they redesign their site,
- is not something to automate without first reviewing their legal conditions
  yourself.

For those reasons this project does **not** include a ready-to-use
DAZN/Movistar+ scraper. Instead:

- Use the real sports APIs in the table above to find out **what** the event
  is and **when** it takes place.
- You add manually, via `/admin/`, **which platform** it can be watched on
  (information you look up yourself on their websites/apps, as you normally
  would).
- If you ever decide to write your own scraper under your own responsibility,
  the place it would fit into the architecture is `ManualSourceAdapter` in
  `schedule/services/adapters.py`.

| Source | Covers | Key required? | Safe to publish on GitHub? |
|---|---|---|---|
| **Jolpica F1** (successor to Ergast) | F1 calendar | No | ✅ Yes — no key at all, 100% open |
| **TheSportsDB** | NBA | Public test key: `3` | ✅ Yes, that test key is officially public and shared. If you later upgrade to a paid Patreon key (more requests, live data), that one **must not** be published |
| **API-Football** | Champions, Europa League, LaLiga, Premier, Serie A, Bundesliga, Ligue 1 | Personal key (free tier: 100 requests/day) | ❌ No — it identifies your account and quota. Keep it in `.env` only |
| **Static Calendar** | MotoGP, 2026 World Cup | No | ✅ Yes — local Python dictionary to bypass TheSportsDB free tier limitations |
| **Tennis provider** (your choice, e.g. api-tennis.com) | Wimbledon, ATP, WTA | Personal key | ❌ No — `.env` only |
| Winter sports (alpine skiing, ski jumping, cross-country) | — | — | No decent free API exists; events are added manually via `/admin/` (`ManualSourceAdapter`) |

General rule: **any key that identifies your personal account or your request
quota is private** and must go only in your real `.env` file (which is in
`.gitignore` and is never committed). Test keys that the provider itself
publishes as shared (like TheSportsDB's `3`) are safe to keep in the
repository, though we still put them in `.env` for cleanliness and easy
rotation.

## Pushing the project to GitHub

```bash
git init
git add .
git commit -m "First version"
git branch -M main
git remote add origin <your-repository-url>
git push -u origin main
```

Before pushing, check that `.env` (your real file, with your keys) does NOT
appear in `git status`. If it does, make sure `.gitignore` is at the project
root.

## Phase 2: Android app

As requested, this first delivery is the web only. When it is time for the
Android Studio app, the natural path is:

1. Add a small read-only REST API on top of these same models (using Django
   REST Framework), reusing all the `Event.is_visible` logic that already
   exists.
2. Consume that API from the Android app with Retrofit + Kotlin, showing the
   same three sections (live / upcoming / on demand).

There is no need to decide any of this now: the models and business logic are
already decoupled from the templates, so adding that API later should not
require touching anything that already works.
