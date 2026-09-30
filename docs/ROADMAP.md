# Delivery roadmap

Each stage should end with a working path, updated docs, relevant checks, and a `builders.md` report.

## 0. Starter repository — included

API, local database, demo catalog, Flutter shell, and project instructions. Verify on the recipient's Android SDK because Flutter is unavailable in the authoring environment.

## 1. Reviewed plant catalog

Confirm data source access and licensing. Add reviewed source metadata, crop/tree requirements, locations, seasons, and growing environments. Add migrations, importer validation, source links, and API filters. Remove demo rows from any advice path.

**Done when:** a catalog item can be traced to a reviewed source; missing or contradictory information is surfaced; tests cover bad imports and empty filters.

## 2. Goals and suitable plants

Add accounts and consent, a plant goal form, location precision choices, container/soil/sunlight inputs, suitability rules, and explanation of why each result fits.

**Done when:** unsupported or incomplete conditions return a safe explanation instead of confident advice.

## 3. Care plan and quests

Create versioned plans grounded in reviewed records. Turn plans into dated tasks. Add forecast adapter with timestamp and fallback; keep an audit of weather-driven task changes.

**Done when:** rain and heat scenarios, stale forecast, and no network are covered by tests.

## 4. Offline logs and photo check-ins

Queue local care logs, sync later with idempotency keys, and resolve conflicts. Add private photo upload with consent and retention settings.

**Done when:** retrying sync does not duplicate care logs and private photos are not publicly accessible.

## 5. Plant-health assistance and survival

Validate local images, return confidence-aware possible symptoms, and route serious or uncertain cases to expert help. Define evidence thresholds for 3-, 6-, and 12-month milestones and normalized community scores.

**Done when:** the product never presents a vision guess as certain or a photo as complete proof of care.

## 6. Pilot and impact

Pilot with growers in a defined locality. Measure retention and survival with clear denominators, consent-based follow-up, and comparison against a stated baseline. Only then publish impact claims or partner offers.
