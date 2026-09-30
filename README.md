# Groot

Groot is a Bangla-first plant-care companion for Bangladesh. This repository is a **starter**, not a completed AI product. It provides an Android-first Flutter shell, a FastAPI catalog API, a PostgreSQL database, and a documented path to care plans, check-ins, weather-aware tasks, and survival milestones.

## What works in this starter

- `GET /health/live` and `GET /health/ready` for service checks.
- `GET /v1/catalog/species` for a small, explicitly labelled **demo** catalog.
- A Flutter screen that fetches the catalog and shows connection errors.
- A local PostgreSQL service with an initial schema and demo rows.

AI recommendations, disease detection, weather adaptation, accounts, rewards, offline sync, and photo uploads are **planned work**. No screen or endpoint should claim those are active yet.

## Repository map

| Path | Purpose |
| --- | --- |
| `apps/mobile/` | Flutter Android app source |
| `services/api/` | FastAPI service and API tests |
| `db/init/` | Schema and demo seed for a fresh local database |
| `docs/` | Product, architecture, and delivery plan |
| `AGENTS.md` | Instructions for coding agents and skill selection |
| `builders.md` | Change reports: which files changed, why, and verification |
| `MASTER_PROMPT.md` | Reusable project workflow prompt |

## Requirements

- Docker with Docker Compose for the API and database.
- Flutter SDK and Android toolchain for the mobile app.
- Python 3.12 or newer if running the API without Docker.

## Start the API and database

From the repository root:

```sh
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8000/docs`, or check:

```sh
curl http://localhost:8000/health/ready
curl http://localhost:8000/v1/catalog/species
```

The Compose database starts with local demo rows only. Its credentials in `.env.example` are development defaults. Change them before exposing any service outside your machine.

## Start the Flutter app

The ZIP includes hand-written Flutter source. Flutter generates Android platform files for the SDK version installed on your computer. Run this once:

```sh
cd apps/mobile
flutter create --platforms=android --project-name=groot_app .
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

`10.0.2.2` reaches the host from the Android emulator. For a physical phone, use your computer's reachable local IP address instead. The starter permits cleartext HTTP in **debug Android builds only**; use HTTPS before distributing an app.

## Checks

```sh
docker compose config --quiet
cd services/api
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
cd ../../apps/mobile
flutter analyze
flutter test
```

The API tests use a substitute catalog repository and do not need PostgreSQL. See `docs/ROADMAP.md` for the next implementation slices.

## Make your Git repository

Unzip the package, then from the `groot-starter` directory:

```sh
git init
git add .
git commit -m "Initialize Groot starter"
```

Do not commit `.env`, generated build files, or personal photos. The provided `.gitignore` excludes them.
