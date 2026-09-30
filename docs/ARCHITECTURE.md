# Architecture

## Current data flow

```text
Flutter catalog screen
    ↓ GET /v1/catalog/species
FastAPI route → CatalogRepository → PostgreSQL species + catalog_source
```

The API owns data access. The Flutter app does not connect directly to PostgreSQL. The source and evidence status travel with each catalog item so demo rows cannot be mistaken for reviewed advice.

## Current boundaries

- **Flutter:** presentation and HTTP client; no local personal data yet.
- **FastAPI:** read-only catalog contract and health checks; no authentication or plant-care logic yet.
- **PostgreSQL:** catalog source provenance and species names; no users, photos, or care history yet.
- **Docker Compose:** local development only. Initial SQL runs only for a new database volume.

## Planned boundaries

```text
User goal / consent
    ↓
API validation + authenticated user context
    ↓
Suitability service ── reviewed catalog + local conditions
    ↓
Source-grounded plan generator → plan with citations and review status
    ↓
Task scheduler + forecast adapter → dated care tasks and stale-data fallback
    ↓
Offline mobile queue → authenticated sync → care and photo timeline
    ↓
Milestone evaluator → survival evidence + normalized rewards
```

Keep model providers behind interfaces. Persist prompt and source versions for traceability without storing unnecessary personal data. A vision adapter should return possible conditions, confidence, and safe next steps; it should not directly award survival points.

## Database evolution

The initial schema has two tables. `species.source_id` is a required foreign key, and status/category checks reject unexpected values. A reviewed source requires a URL and review date. The API derives a species' evidence status from its source, avoiding conflicting statuses. There is no cascade delete: removing a source must not silently orphan species. A partial index supports active catalog reads.

Before adding users, plans, tasks, check-ins, and rewards, choose an explicit migration tool and create forward-only migrations. Never edit `db/init/001_schema.sql` to change an already populated database. Add unique identifiers, ownership constraints, and retention rules for personal data before accepting photos or locations.

## API and mobile behavior

The public starter endpoint has a 100-row safety limit; add cursor pagination before catalog growth. The app shows loading, empty, error, and data states. An Android emulator reaches the host API at `10.0.2.2`; release builds must use HTTPS. Debug-only HTTP permission is in `android/app/src/debug/AndroidManifest.xml`.

## Security and privacy before real users

Add server-side authentication, authorization, rate limits, upload size and type checks, private object storage, and data deletion flows before storing accounts, photos, or exact locations. Obtain consent for geotags and avoid exposing home coordinates in aggregate views.
