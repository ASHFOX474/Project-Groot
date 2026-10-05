# Delivery roadmap

Each stage should end with a working path, updated docs, relevant checks, and a `builders.md` report.

## 0. Starter repository — included

API, local database, demo catalog, Flutter Android runner and project instructions.
Android preview was verified on the recipient's Mac. Versioned Alembic migrations,
guarded legacy adoption and isolated PostgreSQL/API checks are now included.

## 1. Reviewed plant catalog

Confirm data source access and licensing. Add reviewed source metadata, crop/tree requirements, locations, seasons, and growing environments. Extend the versioned migrations, importer validation, source links, and API filters. Remove demo rows from any advice path.

**Foundation implemented:** revision0003, strict versioned import/audit, field-level
citations, explicit locality/context, source access/rights checks and a fail-closed
candidate API. Three cited research profiles are draft; actual permission and
Bangladesh agronomic approval remain pending. This stage is not complete merely
because import validation passes. See `CATALOG_SOURCES.md` / `CATALOG_IMPORT.md`.

**Done when:** a catalog item can be traced to a reviewed source; missing or contradictory information is surfaced; tests cover bad imports and empty filters.

## 2. Goals and suitable plants

Add accounts and consent, a plant goal form, location precision choices, container/soil/sunlight inputs, suitability rules, and explanation of why each result fits.

**Identity/record slice implemented:** local handle/password accounts, optional
preferences/withdrawal receipts, revocable sessions, private Plant Passports and
manual care history, plus server ownership tests and mobile flow.

**Goal/rules slice implemented:** bilingual transient form, chosen location
precision, optional device speech, cited deterministic matches and explicit
uncertainty/empty/unsupported states. Structured selections—not inferred goal
prose—drive rules. Real catalog approval and production identity operations remain
pending; LLM generation is unbuilt. See `GOALS_RECOMMENDATIONS.md`.

**Done when:** unsupported or incomplete conditions return a safe explanation instead of confident advice.

## 3. Care plan and quests

Create versioned plans grounded in reviewed records. Turn plans into dated tasks. Add forecast adapter with timestamp and fallback; keep an audit of weather-driven task changes.

**Plan slice implemented:** reviewed bilingual directives, dated source-cited
previews, review dates, explicit gaps/conflicts, private immutable versions and
live evidence rechecks. Real approved guidance is pending. Tasks/weather/LLM
generation are not built. See `CARE_PLANS.md`.

**Done when:** rain and heat scenarios, stale forecast, and no network are covered by tests.

## 4. Offline logs and photo check-ins

Queue local care logs, sync later with idempotency keys, and resolve conflicts. Add private photo upload with consent and retention settings.

**Care notebook implemented locally:** explicit Android opt-in, device lock and
encrypted atomic storage, downloaded latest plans/passports, durable UUID care
queue, live owner-bound deduplication and needs-review conflicts. Cached advice
expires after24h/known evidence expiry. No offline passport edits/quest completion
or weather generation. **Private photo check-ins implemented locally:** separate
storage/health consent, bounded canonical JPEG/PNG uploads, owner-scoped timeline,
metadata stripping, retry identities and explicit deletion. Native successful
credential/encryption still requires a secure-device test. See `OFFLINE_CARE.md`.

**Done when:** retrying sync does not duplicate care logs and private photos are not publicly accessible.

## 5. Plant-health assistance and survival

**Photo observation assistance implemented locally:** image quality and possible
colour/user-reported symptom flags are clearly marked as unvalidated and
low-confidence, with no diagnosis, probability or chemical/dose advice. Serious
or uncertain cases route to the 16123 agricultural help path. A validated vision
model remains future work. Self-reported care streaks, 3-, 6-, and 12-month
milestone cards, capped average per-plant scoring, moderated text posts, reports,
and k-anonymous district trends are implemented in revision0009. They do not
verify survival, expose exact locations, publish photos, or reward raw plant
counts.

**Done when:** the product never presents a vision guess as certain or a photo as complete proof of care; community content is approved before it is visible.

## 6. Pilot and impact

Pilot with growers in a defined locality. Measure retention and survival with clear denominators, consent-based follow-up, and comparison against a stated baseline. Only then publish impact claims or partner offers.
