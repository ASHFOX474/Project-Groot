# Goal intake and reviewed suitability

## Try it

Start the normal [Mac Android preview](SETUP_MAC.md). Tap the account icon,
register/sign in with local test credentials, then **লক্ষ্য ও উপযুক্ত গাছ · Plan a goal**.
The form starts in Bangla; select English at the top. Enter or dictate a goal,
confirm Crops/Trees/Any, select growing space and enter known measurements.
Bangla and English digits are accepted. Unknown sunlight/soil and blank numeric
fields remain unknown; never invent a pH measurement.

Location defaults to **No location**. You may choose Bangladesh only or district
only; no address, GPS, geocoder or automatic location lookup exists. Downgrading
precision clears the district. Sharing more is optional. The current matcher
cannot establish local suitability without an explicitly covered district.

Choose a planned **seed-sowing** date, not a transplant/harvest date. Submit to
see reviewed-condition matches, possible matches needing confirmation, or a safe
explanation of missing/unsupported data. Changing an input clears old results.
Results expose reasons, uncertainty, review/expiry dates and field-level sources,
locators, interpretation notes, licenses and attribution.

**Current content limit:** the local catalog has five species, three draft profiles
and zero eligible recommendation profiles. With district supplied, the expected
live result is “No approved plant profiles…”; with less location it requests
optional details. This is not a broken connection. Rights and local agronomic
review must be resolved through [the existing import workflow](CATALOG_IMPORT.md).
Synthetic approved fixtures exist only inside isolated tests. Never promote live
drafts or use the demo catalog to make the screen look populated.

## Voice and privacy

The Android button shows a separate disclosure/confirmation before launching the
device's speech activity with `bn-BD` or `en-US`. Groot receives editable text,
never submits it automatically, and does not capture/store audio. Cancellation
preserves the existing text. Missing/disabled providers or failures leave typing
available; a keyboard microphone is another device-managed option.

The offline preference is **not a guarantee**: the selected speech provider may
ignore it and process audio online. Provider language support, network behavior
and retention are outside Groot. Do not speak personal details. See the official
[Android RecognizerIntent contract](https://developer.android.com/reference/android/speech/RecognizerIntent)
and [Flutter platform channel guidance](https://docs.flutter.dev/platform-integration/platform-channels).
No location or `RECORD_AUDIO` permission was added to Groot.

Goals, selected location and conditions are sent only on explicit submission to
the authenticated API, processed transiently and not saved as goals/passports.
Separately saving a care plan explicitly retains structured conditions/chosen
location, not free goal/soil prose; previews remain transient. See [care plans](CARE_PLANS.md).
The draft/results stay in screen memory and disappear on closing it. There is no
offline queue, request-body logging or model/geocoding/forecast provider call.
Free-text can still contain personal data if a user types it: the warning is not
an automatic redaction guarantee. Operational hosts/proxies must also avoid body
logging. Normal private-request throttle counters still update.

The existing future GPS/community/impact preferences do not enable collection.
Voice confirmation is not a new stored account consent choice. API responses are
private/no-store; session expiry clears the client bearer and exits the form.
Use test data on debug HTTP; real use needs the existing production TLS/privacy
hardening described in [Accounts and Passports](ACCOUNTS_PASSPORTS.md).

## API contract and rule boundary

`POST /v1/goals/recommendations`, bearer required. Pydantic models in
`services/api/app/goal_models.py` and generated `/openapi.json` are authoritative;
the shared JSON fixture is tested by both Python and Dart. No schema migration is
needed for the matcher; care-plan persistence separately advances head to `0005`.

The request includes `language` (`bn`/`en`), nonblank `goal` (max500), confirmed
`category`, `location`, `growing_context`, optional positive `area_m2`, sunlight,
soil description/pH/texture/drainage, `planting_date` and optional temperature.
See `services/api/tests/fixtures/goal_contract.json` for a complete example.
Numeric strings, booleans, nonfinite/out-of-range numbers and extra fields are
rejected. Location is `{precision: none}`, `{precision: country, country_code: BD}`
or `{precision: district, country_code: BD, district: Dhaka}`. Coordinates and
district values beyond the chosen precision are rejected rather than stored.

Responses use `matches_found`, `needs_details`, `no_reviewed_data`, `no_match` or
`unsupported_region`, a localized message/next steps, bounded recommendations
(max10) and `rules_version`. Each match is `matching_conditions` or
`needs_confirmation`. These are evidence/condition labels, **not probability
scores or promises of survival/yield**. Errors are redacted:401 session,422 invalid
input,413 body over16KiB,429 private-request throttle,403 production HTTP,
503 unavailable or invalid catalog evidence. Transport/auth checks use the same
private middleware and transactional session recheck as passports.

The existing catalog query caps reads at the first100 eligible profiles ordered
by ID. At that boundary, results warn that the search is not exhaustive. Add
scoped query pagination before expanding beyond this prototype-sized catalog;
an empty result must not be presented as proof no suitable plant exists anywhere.

The matcher is deterministic, not an LLM/RAG agent. Free goal/soil prose is not
parsed into categories, pH or growing conditions; the structured selections drive
the match. It reads only the existing eligibility view inside the authenticated
transaction; demo/draft, expired, inaccessible and rights-uncleared sources remain
excluded. Browse `/v1/catalog/species` must never feed recommendations.

Profiles must explicitly use `country_code=BD` and canonical locality
`district:<lowercase district>` (e.g. `district:dhaka`). Country-level prose is not
silently extrapolated to a district. Bangla aliases for the eight division-named
districts and Chittagong/Barisal spelling aliases are supported; other Bangla
district names need an explicit reviewed mapping before matches will appear.
This does not claim those districts already have approved profiles.

Growing context/category must match. Known sunlight, pH, texture, drainage,
temperature, seed-sowing season or minimum field-spacing area conflicts exclude
the profile. Unknown user facts or missing source requirements produce explicit
confirmation warnings. Cross-year sowing windows are handled. A review expiring
before the selected date also needs renewal; the earliest profile, primary-source
or requirement-source expiry controls the returned validity. Container profiles always need
confirmation: field spacing is not converted into pot size; depth, rooting space
and substrate requirements are not yet modeled. Spacing area covers only one cell,
not plot shape, access paths or a suggested plant count. Temperature is user-reported,
not a forecast. No ranking optimization or automatic passport creation is
implemented. Reviewed directive-based plans are a separate [care workflow](CARE_PLANS.md).

## Checks

```sh
sh scripts/check-api.sh
sh scripts/check-db.sh
sh scripts/check-mobile.sh
cd apps/mobile
../../scripts/flutterw test integration_test/account_passport_smoke_test.dart \
  -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

The live test creates/deletes only its unique test account and checks the Bangla
district form against the actual API without approving any catalog data. Isolated
DB fixtures cover approved matches, withdrawn rights, transient processing,
redacted validation, session expiry and broken evidence. Dart tests cover contract
drift, bearer handling, bilingual/precision controls, validation, result citations,
voice disclosure/edit/cancel/unavailability and the mocked platform channel.
The Android build verifies the native bridge compiles. Actual spoken Bangla/English
recognition accuracy still needs a supported physical-device/provider check; a
mocked transcription is not evidence of real speech quality.
