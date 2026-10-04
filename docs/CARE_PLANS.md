# Grounded, private care plans

## Use and current limits

Sign in → **Plan a goal** → reviewed match → **Preview care plan**. Select 1–12
follow-up weeks and inspect dated instructions, source locators/rights and review
dates. Save only after the disclosure. **Saved care plans** in the garden opens
live evidence checks, immutable version history, condition revision and explicit
whole-plan deletion. Revising returns to the populated goal form; reassess,
preview and explicitly save a version. Different species require separate plans.

The generator is deterministic: it extracts **explicit human-reviewed bilingual
instructions and timing**, not LLM prose or invented watering/fertilizer doses.
Live approved content is still pending. Demo/draft content never becomes advice;
synthetic approved fixtures belong only in disposable test databases. No weather
quests, reminders, offline storage, passport linkage, disease treatment or survival
verification is built here.

## Grounding and gaps

The selected profile must pass the existing recommendation eligibility boundary
and condition matcher. It is filtered before the query's 100-row cap. Known
mismatches block generation; unknown conditions and container limits remain
visible. Free goal/soil prose is not parsed into actions; spacing/pH cannot become
watering rates or pot dimensions. Each directive additionally requires its own
reviewer/date/validity and currently reviewed, public, rights-cleared source.
Bangla/English is selected from reviewed text, not runtime translation.

Week 0 is seed-sowing day; week 1 is days1–7, week2 days8–14. Transplant timing
is not substituted. The earliest profile, condition-source, care-source and
directive validity bounds each instruction. Ranges extending past expiry are
withheld entirely; planting before directive/source review is unsupported. Dates
use Bangladesh civil time. Soil preparation requires day0 coverage; watering,
nutrition and monitoring each require every requested follow-up week.

- `ready`: matching conditions and all required topic/week coverage exist.
- `partial`: some instructions exist, but conditions or coverage have gaps.
- `blocked`: unsupported conditions or no usable instructions; cannot save.

Missing topics/weeks are explicitly listed, never guessed. Partial is not complete
care or planting approval; ready is not a yield/survival guarantee. Overlapping
directives within a topic that differ in either language are **all withheld**,
with citations, pending expert review. This is conservative text/interval conflict
detection, not semantic agronomic contradiction detection. Complementary wording
may be held; identical bad advice cannot be detected by schema checks.
Comparison is limited to the selected profile; reviewers must also resolve
overlapping/conflicting approved profiles during catalog review.

## Reviewed content format

Read [sources](CATALOG_SOURCES.md) and [append-only import](CATALOG_IMPORT.md).
Schema-v1 profiles accept optional `care_guidance` (max32 globally unique entries):

```json
{
  "id": "your-versioned-guidance-id",
  "topic": "monitoring",
  "week_start": 1,
  "week_end": 4,
  "instruction_bn": "HUMAN-REVIEWED BANGLA TEXT",
  "instruction_en": "HUMAN-REVIEWED ENGLISH TEXT",
  "source_id": "your-bundle-source-id",
  "source_locator": "EXACT PAGE/SECTION/RECORD",
  "interpretation_note": "WHY TEXT/TIMING FITS THIS PROFILE",
  "review_status": "draft",
  "reviewed_by": null,
  "reviewed_at": null,
  "valid_until": null
}
```

This is a placeholder template, not approved agricultural guidance. Topics are
`soil_preparation`, `watering`, `nutrition`, `monitoring`. Preparation is exactly
week0/0; other topics start at week1 and end by week12. Each language is required,
max800 characters, without null/invalid UTF-8. Reviewed entries require reviewer,
nonfuture review date and later expiry. IDs/source references use existing rules.

A local agronomic reviewer must check species/variety, exact locality/context,
seed-stage timing, safety, both translations and source fidelity. Operators
separately verify exact-artifact rights/attribution. An AI-produced `reviewed` flag
is not proof. Do not import pesticide/chemical treatment instructions or invented
doses; there is no treatment safety validator. Nutrition must stay appropriate,
explicitly reviewed non-treatment care. Unsupported information remains draft or
missing. New identities are append-only; changing/promoting old records requires
a separately reviewed forward workflow. Empty care arrays are omitted from
canonical manifests, preserving legacy schema-v1 import hashes.

## HTTP and version contracts

Pydantic `services/api/app/care_models.py` and `/openapi.json` are authoritative.
Every route requires a bearer and owner transaction/session rechecks, no-store
responses and private request limits. Unknown fields, caller owners and snapshots
are rejected. Errors do not echo private input.

| Route | Behavior |
| --- | --- |
| `POST /v1/plans/preview` | Transient `{profile_id, goal, weeks}`; existing full goal contract, weeks default4 |
| `POST /v1/plans` | Same plus UUID `request_id` and `save_notice_version: care-plan-2026-10-04`; regenerate server-side |
| `GET /v1/plans?after=UUID&limit=20` | Owner-only saved summaries, max100; saved status is not current advice |
| `GET /v1/plans/{id}` | Latest snapshot, rechecked against live evidence |
| `POST /v1/plans/{id}/versions` | Preview input plus `expected_version` and save notice; compare-and-swap |
| `GET /v1/plans/{id}/versions?before=N&limit=20` | Descending immutable version summaries, max100 |
| `GET /v1/plans/{id}/versions/{N}` | Specific snapshot, with live evidence recheck |
| `DELETE /v1/plans/{id}` | Explicit owner deletion, including all versions |

Same owner/request UUID and normalized conditions retry returns original version1;
different conditions under that UUID return409. Revision appends only if its
conditions/evidence fingerprint changes. Stale edits return409; retrying the
immediately preceding successful identical edit returns latest. Owner locks
serialize writes. No client-selected version numbers or duplicate lost-response
records. A different species needs a separate plan.

Snapshots include structured conditions, generator version, evidence hash,
fingerprint and reviewed citations. A DB trigger rejects UPDATE. Evidence changes,
expiry or rights withdrawal never rewrite snapshots: reads mark `stale` or
`unavailable`, **clear instructions and return blocked**. Original private audit
snapshots remain until explicit deletion; old versions cannot bypass withdrawn
advice. Site/condition changes require explicit user revision, not auto-detection.

## Privacy, migration and verification

Recommendations/previews are transient. Explicit save retains chosen location
precision (and selected district), structured conditions and cited versions. Free
goal prose becomes the literal `Care plan`; soil-description prose is removed.
No audio/GPS/chat transcript/provider access is added. Save notice does not enable
analytics/photos elsewhere. Versions persist until owner plan/account deletion;
there is no timed retention worker. Deleting a plan does not delete passports.

Revision0005 adds guidance/plans/versions/indexes/immutability trigger without
seeding or changing old rows. Downgrade is blocked to preserve private/evidence
data. Back up and rehearse restore into a new isolated DB before applying; use a
forward fix, not a stamp/reset. See [migration procedures](DATABASE_MIGRATIONS.md).

```sh
sh scripts/check-api.sh
sh scripts/check-db.sh
sh scripts/check-mobile.sh
python3 scripts/check_repo.py
```

Python/Flutter share `services/api/tests/fixtures/care_contract.json`. Isolated
tests cover missing/conflicting/expired/withdrawn guidance, independent care-source
rights, ownership, immutable history, retries/stale updates, malformed evidence,
session expiry during writes, old rows/import hashes and explicit mobile saving.
Production roles, approved content, TLS/identity hardening and remote CI execution
remain separate prerequisites.
