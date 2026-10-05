# Validated catalog import and recommendation boundary

## What's implemented

Revision `0003` adds source access/rights/review metadata, a nullable scientific
name, immutable import audit records, scoped plant profiles, per-field requirement
citations, and a fail-closed `recommendation_profile` view. Original names, inactive
flags, references, timestamps and demo records are preserved. No seed data is
inserted by migrations. See [source research](CATALOG_SOURCES.md) for current gaps.

`/v1/catalog/species` remains the compatibility/preview endpoint and may include
demo or draft records. Its existing `evidence_status=reviewed` describes a **source
evidence check**, not cleared rights, agronomic approval or recommendation eligibility.
Never use that endpoint/list method as the input to advice, care-plan generation
or RAG. No mobile design/source change is made in this catalog task.

`GET /v1/catalog/recommendation-candidates` reads only the filtered view. It returns
at most 100 eligible reference profiles, with scope/variety, limitations, review
dates, import SHA-256 and per-field source/license/attribution evidence. This is
**candidate data**, not a personalized recommendation engine. It does not match
district, container, soil or sunlight conditions. Initially it intentionally returns
`[]`; do not fall back to demo/general catalog data when empty. A missing migration
or malformed direct-DB requirement returns 503, not guessed advice.

## Eligibility requirements

All conditions must hold at query time, not just at import:

- Active non-demo species; `demo-*` and the `starter-samples` source are excluded.
- Profile reviewed for its declared BD locality, growing context and variety, with
  reviewer, date and unexpired approval.
- Primary source **and every requirement source** reviewed, publicly accessible,
  currently within the source review window, and carrying verified `open_license`
  or `permission_granted` evidence. Pending/restricted/unknown reuse fails closed.
- At least one typed requirement. Missing fields are unknown. Eligibility is not
  proof that the profile has enough information to generate a full care plan.

Expiry uses Bangladesh civil dates (UTC+06). Withdraw permission, change review
status, mark a source inaccessible or deactivate a species and the view excludes it
on the next query. No cached recommendation eligibility is stored. Only trusted
operators should have database write access; the importer does not authenticate
reviewers or legally prove assertions inside their JSON. Production roles remain
future work. An operator must verify the evidence rather than blindly trusting an
AI-generated `reviewed` flag.

## Validate first, without database writes

From the root, after building the API image:

```sh
docker compose build api migrate
sh scripts/import-catalog.sh
```

The helper validates the bundled `/app/catalog/bangladesh-starter-v1.json` file;
building copies the current version into the image. Changes to JSON require a
rebuild. Validation is offline, makes no HTTP requests, and does not need the DB
to be running. It does **not** approve licensing or agronomic suitability.

For another file, put it under `services/api/catalog/`, build, then invoke:

```sh
docker compose run --rm -T --no-deps api python -m app.catalog_import \
  /app/catalog/YOUR_VERSIONED_FILE.json
```

Replace the filename with your actual file. This is a trusted local CLI, not an
internet-facing upload API. Do not put secrets or personal photos in bundles.

## Apply only after backup and review

Read [database backup/migration procedures](DATABASE_MIGRATIONS.md). Back up and
rehearse a restore before schema changes/imports; never reset the volume.

```sh
docker compose up --build --wait
sh scripts/db.sh check
sh scripts/import-catalog.sh
sh scripts/import-catalog.sh --apply --confirm
curl -f http://127.0.0.1:8000/v1/catalog/recommendation-candidates
```

This applies the initial research bundle into the quarantined draft catalog, not
into usable planting advice. Current migration head `0009` includes catalog schema
`0003` and is required by the guarded importer. The command holds the same
transaction advisory lock as migrations and demo seeding, with bounded waits.
One transaction covers sources, species, profiles, facts and audit/version hash.
An identity conflict or SQL error rolls everything back; no partial catalog survives.
Repeating the exact same canonical manifest/hash is a no-op. Changing content under
an imported bundle ID is refused. The CLI redacts supplied validation inputs and
unexpected DB errors instead of logging credentials/row contents.

Imports are **append-only**. There is no update/delete/upsert mode: they never
overwrite user edits or silently reactivate a plant. All existing source, species
and profile identity collisions are refused. For a changed dataset, review new
versioned identities for the bundle **and its records**; this tool cannot promote
or revise an existing draft in place. Deactivation/rights withdrawal or merging
canonical species requires a separately reviewed forward change. Do not create
multiple conflicting active approved versions for the same plant/scope.

## Bundle format

The checked-in JSON is the example; strict Pydantic models in
`services/api/app/catalog_bundle.py` define the contract. `schema_version` is 1.
Unknown fields, duplicate JSON keys/record IDs, dangling source references,
reserved demo IDs, missing citations, credential-bearing/non-HTTPS URLs, invalid
review date ordering and unsupported values are refused. File limit is 2MiB;
maximum 100 sources/200 plants/10 profiles per plant/16 facts per profile.

Profiles also accept optional `care_guidance` (max32 source-cited reviewed
directives). See [care schema, bilingual/timing review and limits](CARE_PLANS.md).
Care directives import atomically with facts; missing source references or duplicate
IDs fail validation. An empty array is omitted from the canonical manifest to
preserve older schema-v1 hashes. Nonempty directives are included in the hash.
No care guidance or approval is added to the shipped research draft.

| Requirement key | Value / units | Interpretation rule |
| --- | --- | --- |
| `soil_ph` | `{min,max}` in pH, 0–14 | Label optimum vs tolerated source range in the interpretation note |
| `soil_texture` | Unique array of `sand`, `sandy_loam`, `loam`, `clay_loam`, `clay` | Not a potting recipe |
| `drainage` | `well_drained` or `moist_not_waterlogged` | Do not infer irrigation volume |
| `sunlight` | `full_sun`, `partial_shade`, `shade` | No invented daily hours |
| `spacing_cm` | `{row,plant}` positive centimetres | Declare field/nursery/variety context; not container depth |
| `temperature_c` | `{min,max}` Celsius | State growth/germination/observation meaning; don't mix them |
| `sowing_windows` | Array of explicit start/end month/day objects | State seed vs transplant and approximations; may cross year boundary |

Each fact requires `source_id`, `source_locator` (page/section/record locator) and
`interpretation_note`. Each profile requires locality, country `BD`, growing context
(`open_ground`, `container`, `forestry`), variety/context label and limitations.
Reviewed profiles require a reviewer and ordered review/expiry dates. Sources
require publisher, reference URL, inspection/recheck dates, access/reuse state,
rights note and attribution. Cleared reuse additionally needs license/permission
name and an exact-artifact evidence URL. `permission_pending` is valid research
metadata, but never eligible for advice. Source text is not downloaded automatically.

The importer enforces field shape/units, not truth of a citation or legal permission.
Database constraints enforce identities, relationships, status values and review
metadata; typed requirements are also checked when reading candidate data. Direct
SQL is not the normal import workflow. Do not import pesticides, medical claims,
fertilizer doses, inferred location suitability or opaque free-text LLM instructions
through these limited requirement keys.

## Tests and recovery

```sh
sh scripts/check-api.sh
sh scripts/check-db.sh
python3 scripts/smoke_api.py
```

DB tests use only isolated temporary databases and cover original-data preservation,
idempotency, conflict rollback, demo exclusion, each source's rights, revocation,
expiry, draft/inactive profiles, typed values, actual constraints and empty output.
No live URLs are fetched in CI. No extra dependencies were added for the importer.

`0003` downgrade is blocked even when its new tables are empty: dropping source
metadata might erase an operator's provenance. Use a reviewed forward fix or restore
into a new isolated DB. Before `0003`, `0002 → 0001` can still remove only its FK
index as tested, but this is not a way to bypass the catalog's data-preservation guard.
