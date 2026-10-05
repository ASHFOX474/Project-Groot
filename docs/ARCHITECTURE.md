# Architecture

## Current data flow

```text
Flutter catalog screen
    ↓ GET /v1/catalog/species
FastAPI route → CatalogRepository → PostgreSQL species + catalog_source
```

The API owns data access. The Flutter app does not connect directly to PostgreSQL. The source and evidence status travel with each catalog item so demo rows cannot be mistaken for reviewed advice.

## Current boundaries

- **Flutter:** catalog plus private account/garden presentation and HTTP clients;
  bearer tokens live only in memory. Explicit offline opt-in adds a bounded,
  device-unlocked Keystore-encrypted notebook, never persistent login tokens.
  Separate per-plant photo consent adds a private timeline and local observation
  assistance; community uses a separate moderated text feed and never publishes
  private photos.
- **FastAPI:** public catalog/health plus authenticated account, consent, passport
  and manual-care routes plus transient goal suitability; server-side owner checks,
  reviewed directive-based care plans with immutable private versions, transparent
  rewards calculations and moderated community endpoints.
- **PostgreSQL:** source provenance plus accounts, hashed sessions, consent receipts,
  private passports/care history, plan versions, consented photo metadata/bytes,
  rewards inputs and community moderation records; composite ownership constraints
  prevent private or cross-account access.
- **Reviewed-reference boundary:** scoped plant profiles and per-field citations
  imported atomically with an immutable manifest hash. A separate SQL view/API
  excludes demo, drafts, expired/inaccessible or rights-uncleared sources. The
  bundled research profiles are not approved advice; general catalog browsing
  must never become a fallback input for recommendation/RAG work.
- **Docker Compose:** local development only. A one-shot migration service runs
  after PostgreSQL is healthy and must succeed before the API starts. Demo seeding
  is a separate explicit command, not an automatic data migration.

## Planned boundaries

Current goal flow: signed-in Flutter form → private goal contract → transactional
session recheck → shared eligibility query → pure deterministic condition matcher
→ cited reasons/uncertainty. Location precision is user-selected; no GPS or prose
inference. No goal/audio storage, schema change, LLM or forecast integration.
See [implemented goal boundary](GOALS_RECOMMENDATIONS.md) for exact scope rules.

Current care flow: reviewed goal match → selected-profile eligibility and condition
checks → independently reviewed/source-cleared directives → explicit gaps/conflicts
and cited dated preview → explicit save → immutable owner-only versions. Reads
recompute evidence and withhold stale instructions. Revision `0005` adds only new
tables/indexes and an UPDATE guard; no old rows/seeds change. Free goal/soil prose
is redacted before saving structured conditions; account/plan deletion intentionally
cascades versions. See [care contracts and safeguards](CARE_PLANS.md).

Current quest flow: latest owner-scoped plan → live evidence recheck → daily
observations/weekly directive reviews → owner/version-scoped completion. Opt-in
district forecasts use a bounded public regional cache and short transactions
before/after provider I/O, never holding account locks through the fetch. New
revision0006 is additive and preserves old snapshots. Retrieval age/coverage
gates weather check notes; no inferred irrigation/dose changes. Flutter displays
pending tasks and optionally schedules a generic inexact Android reminder, without
  private content or background forecasts. Vision remains planned; rewards consume
  only dated, self-reported care rows. See [contracts/privacy](QUESTS_WEATHER_REMINDERS.md).

Current offline flow: explicit opt-in + live owner/evidence reads → atomic encrypted
Android snapshot → device-unlocked cached plan view/local manual care outbox → live
reauthentication to the original UUID/server → owner transaction + stable operation
UUID → same care ID on retry. Revision0007 adds a nullable UUID and partial unique
index; legacy data/clients remain compatible. No last-write-wins edits, cached
weather or queued quest completions. See [conflicts/privacy](OFFLINE_CARE.md).

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

Alembic revisions in `services/api/migrations/versions/` now own schema changes.
Revision `0001` reproduces the original schema; `0002` adds a non-unique source FK
index without changing rows. The old init SQL is immutable historical evidence,
used by integration tests only. Legacy databases must pass a strict schema check
before an explicit baseline stamp; normal upgrades never stamp existing tables.
Each command holds a PostgreSQL transaction-scoped advisory lock, uses bounded
lock/statement timeouts, and commits schema plus version together. API readiness
checks the migration head and catalog table availability, not merely `SELECT 1`.

Rollbacks are revision-specific and require confirmation. `0002` can roll back to
`0001` by removing only its index; rolling back `0001` is prohibited to preserve
catalog rows. Prefer forward fixes for deployed changes. See
[migration operations](DATABASE_MIGRATIONS.md) for backup, restore and adoption.
Before adding another private workflow, add a reviewed immutable revision with
upgrade/rollback tests, ownership constraints, and retention rules. Revision `0009`
adds rewards/community moderation state without changing existing plant or care rows.

Revision `0003` adds source publisher/access/reuse/reviewer/expiry/attribution,
scientific names, import audit, profiles and requirement facts without changing
legacy values. Existing source rights default to unverified/permission-pending.
The `recommendation_profile` view rechecks every fact's source as well as the
species' primary source. Queries use Bangladesh civil dates for expiry. Typed
values are validated offline at import and again when candidate data is read;
no importer network calls or HTTP import endpoint exist. Rollback of `0003` is
blocked to avoid deleting provenance; use a forward fix. See
[catalog workflow](CATALOG_IMPORT.md) and [source decisions](CATALOG_SOURCES.md).

## API and mobile behavior

The public starter endpoint has a 100-row safety limit; add cursor pagination before catalog growth. The app shows loading, empty, error, and data states. An Android emulator reaches the host API at `10.0.2.2`; release builds must use HTTPS. Debug-only HTTP permission is in `android/app/src/debug/AndroidManifest.xml`.

## Security and privacy before real users

Revision `0004` adds only account/passport tables and indexes. AccountRepository
keeps credential/session validation and every owner-scoped read/write within a
transaction; account row locks serialize password/logout/deletion with protected
operations. Sessions are rechecked after locking. Care ownership also has a
composite FK. Consent snapshots and dated receipts commit together. Record/account
deletion cascades are intentional owner operations; schema downgrade is blocked.
Private API errors redact inputs, responses are non-cacheable, and only explicit
development accepts HTTP. No cookie sessions or trusted arbitrary proxy headers.

Authentication, owner authorization, throttling and explicit deletion now exist.
Least-privilege production roles, TLS/proxy setup, retention/recovery, MFA/recovery,
secure persistent login storage and per-feature collection permissions still need
review before real/shared deployment. No GPS, model-provider access or aggregate
analytics is enabled by the general consent preferences. Community participation
requires the existing community choice plus a district-level profile notice;
withdrawal hides posts and removes district metadata. Photo storage and health
assistance have their own explicit per-passport choices and remain off by default.
See [account data flow and limits](ACCOUNTS_PASSPORTS.md).
