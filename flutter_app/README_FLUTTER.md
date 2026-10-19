# Sports Stream — Flutter App

Mobile client for the [Sports Stream Platform](https://sports-stream-platform-unififer.onrender.com).

## Stack

| Layer | Technology |
|---|---|
| Framework | Flutter 3.x (Dart) |
| State management | Riverpod 2 |
| HTTP | `package:http` |
| Date formatting | `intl` |
| Open URLs | `url_launcher` |

## Project structure

```
flutter_app/
├── lib/
│   ├── main.dart                      ← Entry point, bootstraps Riverpod
│   ├── theme/
│   │   └── app_theme.dart             ← Shared dark theme & colour palette
│   ├── models/
│   │   └── models.dart                ← Dart mirrors of the Django models
│   ├── services/
│   │   └── api_service.dart           ← HTTP client + Riverpod providers
│   ├── widgets/
│   │   ├── event_card.dart            ← List tile for a single event
│   │   └── platform_badge.dart        ← Coloured badge that opens platform URL
│   └── screens/
│       ├── home_screen.dart           ← Live / Upcoming / On Demand tabs
│       └── event_detail_screen.dart   ← Full event detail
└── pubspec.yaml
```

## Getting started

### Prerequisites

- Flutter 3.19+ (`flutter --version`)
- Android Studio or VS Code with Flutter extension
- An Android emulator or real device

### 1. Install Flutter (if not already installed)

```bash
# Linux — using snap
sudo snap install flutter --classic

# Or via official installer:
# https://docs.flutter.dev/get-started/install/linux
```

### 2. Install dependencies

```bash
cd flutter_app
flutter pub get
```

### 3. Run on Android emulator

```bash
# List available devices
flutter devices

# Run (emulator must be running)
flutter run
```

> **Note:** The Android emulator maps `10.0.2.2` → your host machine's `127.0.0.1`.
> If you want to test against the local Django server, change `_baseUrl` in
> `lib/services/api_service.dart` to `http://10.0.2.2:8000`.

### 4. Build a release APK

```bash
flutter build apk --release
# Output: build/app/outputs/flutter-apk/app-release.apk
```

## Backend API

The app calls:

| Endpoint | Used for |
|---|---|
| `GET /api/v1/events/` | Home screen (live / upcoming / on_demand) |
| `GET /api/v1/events/<id>/` | Event detail screen |
| `GET /api/v1/sports/` | Sport filter picker |

Optional query params for `/api/v1/events/`:
- `?sport=<slug>` — filter by sport (e.g. `football`, `motorsport`)
- `?platform=<slug>` — filter to events on a specific platform

## Switching between local and production

Edit `lib/services/api_service.dart`:

```dart
// Production (Render)
const String _baseUrl = 'https://sports-stream-platform-unififer.onrender.com';

// Local dev (Android emulator → host 127.0.0.1)
// const String _baseUrl = 'http://10.0.2.2:8000';
```

> The Render free tier hibernates after 15 min of inactivity.
> The first request may take ~30 s. The loading screen warns the user of this.
