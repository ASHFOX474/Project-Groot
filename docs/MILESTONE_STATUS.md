# Four-milestone audit — 2026-10-04

This reports the requested local prototype scope, not production readiness or a
complete AI product. Passing tests cannot grant content rights or expert approval.

| Requested step | Status | Evidence / remaining work |
| --- | --- | --- |
| Make the starter runnable | Complete locally; GitHub publication is pending | Preserved ignored Flutter SDK, removed broken SDK gitlink, Android runner and wrappers staged, healthy demo API/DB, debug APK and live catalog/account emulator flows verified |
| Establish safe database changes | Complete for the local/CI workflow | Revisions 0001–0004, guarded transactional upgrades/adoption, explicit demo seed, backup/restore/rollback procedures, isolated real-PostgreSQL tests and coverage gate |
| Build a reviewed plant catalog | Infrastructure/research complete; approved content pending | Three cited draft profiles / eleven requirements, offline validated atomic append-only import, source access/reuse evidence, demo/draft exclusion; **zero approved recommendation candidates** |
| Add accounts and Plant Passports | Complete for the local prototype | Password hashes, revocable hashed sessions, editable off-by-default optional choices, owner-only species/date/conditions records and dated manual care, Android flow and isolation tests |

## What this audit finished

Required setup/feature files existed locally but were untracked, so they would not
be included in a commit/clone. Staged only reviewed project source, tests, config,
runner resources and documentation. The ignored SDK, backups, `.env`, generated
registrant and build output remain outside the index. No commit/push was made.

Added `scripts/check_repo.py` and seven regression tests, plus a CI repository job.
It detects missing/untracked project files, forbidden tracked local/private paths,
missing executable Git modes and unresolved index entries. It never changes Git
or files. Expanded `.env` variant ignore rules while retaining `.env.example`.
Added a narrow `.gitattributes` rule and normalized only the Windows Gradle
launcher's index representation to LF; Windows checkouts retain CRLF. This resolved
the staged-diff CRLF whitespace reports without rewriting the generated launcher.
Updated the Mac guide to distinguish its reference SDK from the user's actually
verified, preserved Flutter 3.47.6 / Dart 3.13.5 SDK.

## Current checks

- Repository gate and seven regression tests: pass after staging reviewed files.
- API unit/config/security checks: **66 passed**.
- Combined API/PostgreSQL/migration suite: **136 passed**, **99.65% statement coverage**.
- Flutter analysis: clean; **6 unit/widget tests passed**; ARM64 debug APK built.
- Live Android catalog and account/passport/care/deletion flows: **one passed each**
  on `Groot_API_36` / `emulator-5554`.
- Development DB head: **0004**. API/DB healthy; live catalog smoke passes.
- Draft bundle validates without DB writes: three sources, three plants.
- Exported staged-source rehearsal (without SDK, `.env` or backups): all 136 DB
  tests, seven handoff tests, six mobile tests, analysis and Android APK build pass.

The API-only 66 tests are a subset of the 136, not an additional 66 cases.
Tests run against isolated temporary DBs; the emulator account test deletes only
its own unique test account. No existing user records or catalog data are reset.
Remote GitHub Actions and a second/Intel Mac have not been run. An upstream
Starlette/httpx deprecation warning and a non-failing Flutter FSEvents warning
remain; neither failed these checks. The exported APK build also reported a
Kotlin daemon cache permission error and completed using its compilation fallback.
Path checks are not a secret-history scan.

## Catalog approval needed to finish step 3

The source report records unresolved reuse permission for the exact BARC/AFACI
handbook and ICRAF Neem factsheet used by the bundled requirements. TreeGOER's
metadata is a separately reusable dataset candidate; it does not clear those two
artifacts or provide imported Bangladesh care instructions.

1. Supply verified artifact-specific reuse evidence (license or written permission
   covering the intended app use), or choose replacement rights-cleared sources.
2. Arrange an appropriate Bangladesh agriculture/forestry reviewer to assess the
   cited values, variety, locality, growing context, seasons, unknowns and conflicts.
3. Provide the reviewer's decision, identity, review/expiry dates, attribution and
   evidence. Keep unapproved plants/fields draft; approval is not an AI flag toggle.
4. Prepare new immutable versioned bundle **and record identities**; the importer
   intentionally cannot overwrite/promote the current drafts in place.
5. Back up/rehearse restore, validate offline, apply with explicit confirmation,
   and rerun real-DB eligibility/exclusion tests. Check candidates only from
   `/v1/catalog/recommendation-candidates`; never fall back to preview/demo data.

Read [source findings](CATALOG_SOURCES.md) and [import procedures](CATALOG_IMPORT.md).
No publishers or reviewers were contacted in this audit. External permission
requests/contact require user direction; expert approval cannot be fabricated.

## Remaining boundaries

- Review the staged diff and then authorize/create the commit and push if desired.
  Staging solves index omissions but does not make a friend's GitHub clone current.
- This preview is verified in Android Studio's emulator, not BlueStacks. Use
  [Mac setup](SETUP_MAC.md); BlueStacks backend/debug networking is not established.
- Before real/public use: TLS/proxy configuration, least-privilege DB roles,
  protected backups/retention, recovery/MFA and further security review. See
  [accounts and privacy](ACCOUNTS_PASSPORTS.md).
- AI care plans, weather quests, offline sync, photos,
  disease analysis, rewards and impact dashboards are outside these four slices.

## Subsequent slice: goal intake (2026-10-04)

Bilingual transient goal intake and deterministic, source-traceable suitability
rules are now implemented separately from the original four-step audit above.
Optional Android speech returns editable text with provider disclosure/fallback.
Reviewed live content is still pending; this does not change the catalog approval
status. See [goal workflow and checks](GOALS_RECOMMENDATIONS.md) and `builders.md`.

## Subsequent slice: grounded care plans (2026-10-04)

Reviewed directive-based bilingual plans, explicit source/review citations,
gap/conflict handling, private immutable versions and live evidence rechecks are
implemented. Migration head is0005. Approved care content remains pending; no
demo fallback or live fixture approval was introduced. This is not LLM/weather
quest generation. See [care scope and review workflow](CARE_PLANS.md) and `builders.md`.
