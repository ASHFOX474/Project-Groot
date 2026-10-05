# Builder Reports

Append one dated entry after every task that changes project files. Keep entries factual and easy to audit. Never replace previous reports. Read-only reviews need no entry.

## Template

### YYYY-MM-DD — Short outcome

**Why:** User need or reproduced problem.

| File | Change | Reason |
| --- | --- | --- |
| `path/to/file` | Specific change | Why this file was affected |

**Database impact:** Tables, constraints, migration, and data integrity impact; write “None” if none.

**Checks:** Exact commands or manual checks and their result. Name checks that could not run.

**Risks / next step:** Only material remaining limitations.

---

### 2026-10-01 — Create Groot repository starter

**Why:** Provide a repository-ready starting point for the Groot concept and a repeatable AI development workflow.

| File | Change | Reason |
| --- | --- | --- |
| `README.md` | Added quick start, checks, and Git steps | Let a new maintainer run the starter |
| `.env.example` | Added local service variables | Document configuration without committing secrets |
| `.gitignore` | Excluded secrets and generated files | Keep the initial repository clean |
| `.editorconfig` | Set basic text formatting | Reduce accidental formatting churn |
| `compose.yaml` | Connected local PostgreSQL and API | Provide a repeatable local runtime |
| `.github/workflows/checks.yml` | Added API and Flutter checks | Check future changes in GitHub |
| `services/api/pyproject.toml` | Declared API and test dependencies | Make installation reproducible within version bounds |
| `services/api/Dockerfile` | Added non-root API container | Run the service through Compose |
| `services/api/.dockerignore` | Excluded development files from image | Keep build context focused |
| `services/api/app/__init__.py` | Marked API package | Support module imports |
| `services/api/app/database.py` | Added catalog repository and database access | Keep SQL behind a replaceable boundary |
| `services/api/app/main.py` | Added health and catalog routes | Expose a small working API contract |
| `services/api/tests/test_api.py` | Added success and database-failure checks | Validate route behavior without a live database |
| `db/init/001_schema.sql` | Added source and species tables with constraints | Track catalog provenance and integrity |
| `db/init/002_demo_seed.sql` | Added clearly labelled sample rows | Exercise the API without pretending to give advice |
| `apps/mobile/pubspec.yaml` | Declared Flutter project and packages | Let Flutter resolve the mobile app |
| `apps/mobile/analysis_options.yaml` | Enabled Flutter lint rules | Support code review and CI |
| `apps/mobile/lib/catalog.dart` | Added typed catalog HTTP client | Isolate network and parsing logic |
| `apps/mobile/lib/main.dart` | Added Bangla-led catalog screen and states | Give the Android starter a visible entry point |
| `apps/mobile/test/widget_test.dart` | Added offline widget check | Verify the starter screen without a network call |
| `apps/mobile/android/app/src/main/AndroidManifest.xml` | Added Android app entry and internet permission | Allow catalog requests on Android |
| `apps/mobile/android/app/src/debug/AndroidManifest.xml` | Enabled HTTP only for debug builds | Allow local emulator development |
| `docs/PRODUCT.md` | Defined current scope and trust rules | Keep claims aligned with evidence |
| `docs/ARCHITECTURE.md` | Documented boundaries and data flow | Guide future feature design |
| `docs/ROADMAP.md` | Added staged delivery criteria | Make the next work actionable |
| `AGENTS.md` | Added agent workflow and skill policy | Guide future assistants consistently |
| `MASTER_PROMPT.md` | Added reusable full-project task prompt | Start future coding sessions with the same workflow |
| `builders.md` | Added dated file-level report template and this entry | Record why each file changed |

**Database impact:** New local-only `catalog_source` and `species` tables with a foreign key and status constraints. Demo seed rows are identified as unverified. No existing database is migrated.

**Checks:** `docker compose config --quiet` passed. Python `compileall` passed for API source and tests. Ruby parsed all YAML files, and Python parsed both Android manifests as XML. Required-file and UTF-8 checks passed. API tests could not run: the package install could not reach PyPI. Docker-based execution could not run because the Docker daemon was not available. Flutter analysis, widget tests, and a device build could not run because the Flutter SDK is not installed here.

**Risks / next step:** Replace demo catalog rows with reviewed Bangladeshi sources before recommendation work. Implement authentication and migrations before storing user or photo data.

### 2026-10-03 — Repair setup and enable the Mac Android preview

**Why:** The checkout had a `flutter/` gitlink without `.gitmodules`, an incomplete
Android runner, no Android SDK/AVD, and Docker was not running. The first Compose
start reproduced a 5432 conflict with the existing CourseDekho database. Only
Groot's networking was changed; that unrelated service remains untouched.

| File | Change | Reason |
| --- | --- | --- |
| `.gitignore` | Ignore `/flutter/`, IDE metadata and Python package metadata | Preserve local SDK without tracking tool output |
| `flutter` (Git index only) | Removed gitlink; all SDK files and SDK Git checkout retained | Repair broken submodule tracking |
| `apps/mobile/android/app/src/main/java/io/flutter/plugins/GeneratedPluginRegistrant.java` (Git index only) | Removed generated file from tracking, retained on disk | Flutter regenerates this file from plugins |
| `.env` (ignored, local only) | Created from development example | Configure demo services without committing local settings |
| `compose.yaml` | Remove database host port; add API readiness healthcheck | Avoid CourseDekho conflict and make `up --wait` meaningful |
| `services/api/Dockerfile` | Add non-root test target; keep default runtime separate | Run tests in Python 3.12 without altering host Python |
| `services/api/.dockerignore` | Include tests in build context | Allow the test target to copy tests |
| `.github/workflows/checks.yml` | Pin Flutter 3.47.5/Java 21, build included runner, add live Compose checks | Catch missing runners and database/API wiring failures |
| `.vscode/extensions.json` | Recommend Flutter and Python extensions | Make editor setup discoverable |
| `.vscode/settings.json` | Point Flutter extension at preserved local SDK | Use this checkout's SDK for F5 |
| `.vscode/launch.json` | Add Android debug configuration from repo root | Pass the emulator API URL and correct app working directory |
| `apps/mobile/.metadata` | Generate Flutter project metadata | Record runner's SDK version and platform |
| `apps/mobile/android/.gitignore` | Ignore local/generated Android files but retain wrapper | Make a fresh clone buildable without machine paths |
| `apps/mobile/android/settings.gradle.kts` | Generate plugin/SDK configuration | Load Flutter and Android Gradle plugins |
| `apps/mobile/android/build.gradle.kts` | Generate shared Gradle build configuration | Complete the missing runner |
| `apps/mobile/android/gradle.properties` | Generate Android/Gradle properties | Use SDK-compatible build defaults |
| `apps/mobile/android/app/build.gradle.kts` | Generate application configuration, `bd.groot.groot_app` | Define Android app ID, SDK and build variants |
| `apps/mobile/android/gradlew` | Generate executable Gradle wrapper | Support Mac/Linux builds |
| `apps/mobile/android/gradlew.bat` | Generate Windows Gradle wrapper | Keep platform scaffold complete |
| `apps/mobile/android/gradle/wrapper/gradle-wrapper.jar` | Generate wrapper bootstrap | Build with the selected Gradle version |
| `apps/mobile/android/gradle/wrapper/gradle-wrapper.properties` | Generate Gradle 9.3.1 configuration and add official distribution SHA-256 | Pin and verify downloaded build tooling |
| `apps/mobile/android/app/src/main/kotlin/bd/groot/groot_app/MainActivity.kt` | Generate Flutter activity | Supply the manifest's missing entry point |
| `apps/mobile/android/app/src/profile/AndroidManifest.xml` | Generate profile manifest | Complete the Android build variants |
| `apps/mobile/android/app/src/main/res/drawable/launch_background.xml` | Generate launch background | Supply referenced Android launch resources |
| `apps/mobile/android/app/src/main/res/drawable-v21/launch_background.xml` | Generate API-specific launch background | Supply standard platform resources |
| `apps/mobile/android/app/src/main/res/values/styles.xml` | Generate light launch/normal themes | Resolve manifest theme references |
| `apps/mobile/android/app/src/main/res/values-night/styles.xml` | Generate dark launch/normal themes | Resolve night-mode theme references |
| `apps/mobile/android/app/src/main/res/mipmap-mdpi/ic_launcher.png` | Generate default launcher icon | Complete density-specific runner assets |
| `apps/mobile/android/app/src/main/res/mipmap-hdpi/ic_launcher.png` | Generate default launcher icon | Complete density-specific runner assets |
| `apps/mobile/android/app/src/main/res/mipmap-xhdpi/ic_launcher.png` | Generate default launcher icon | Complete density-specific runner assets |
| `apps/mobile/android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png` | Generate default launcher icon | Complete density-specific runner assets |
| `apps/mobile/android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png` | Generate default launcher icon | Complete density-specific runner assets |
| `apps/mobile/pubspec.yaml` | Add Flutter SDK integration-test dependency | Run the live catalog check on Android |
| `apps/mobile/pubspec.lock` | Resolve integration-test dependencies | Retain repeatable Dart package resolution |
| `apps/mobile/integration_test/catalog_smoke_test.dart` | Add bounded live demo catalog test | Verify Android app → API → PostgreSQL, including Bangla names and Demo chips |
| `scripts/flutterw` | Prefer local SDK, then explicit override/PATH | Preserve user SDK; never auto-upgrade or install it |
| `scripts/start-emulator.sh` | Start named AVD without metrics collection | Provide a repeatable visible preview |
| `scripts/preview-android.sh` | Wait for healthy services, check API, run Flutter | Combine the local demo startup workflow |
| `scripts/check-api.sh` | Build/run isolated test target | Check API without requiring host Python dependencies |
| `scripts/check-mobile.sh` | Resolve packages, analyze, test, build debug APK | Verify both Dart and Android setup |
| `scripts/smoke_api.py` | Read-only health/catalog contract check | Verify real database connectivity and UTF-8 catalog data |
| `README.md` | Replace runner-generation instructions with runnable preview/check commands | Match the completed checkout and correct physical-phone networking |
| `docs/SETUP_MAC.md` | Add Mac toolchain, emulator, F5, troubleshooting and tracking-repair guide | Explain how to reproduce the setup without deleting SDK/data |
| `builders.md` | Append this file-level report | Record scope, reasoning and verified results |

**Preserved:** Existing Dart app source, widget test, both original Android
main/debug manifests, API source, database SQL, Flutter SDK revision
`6a19cca56475dbfba1478ee68d7bd0c2ef891da1`, and unrelated work. Runner files were
generated in a temporary project using the existing SDK and copied only where
missing, not by overwriting the app with a new Flutter template.

**Local tool setup:** Started existing Docker Desktop; installed official Android
command-line tools (ARM64 archive SHA-256 verified), SDK 36, build tools 36.0.0,
emulator 37.2.12, platform-tools, NDK 28.2.13676358, CMake 3.22.1 and Google APIs
ARM64 API 36 system image. Created `Groot_API_36` (Pixel 7). Selected the existing
Microsoft Java 21.0.10 and Android SDK through Flutter's user-level configuration.
System Java 25, shell profiles, and the local Flutter SDK version were not changed.

**Database impact:** No schema or SQL changes. A new local named volume
`project-groot_groot_db` was initialized with the existing schema and two demo rows.
No volume or existing database data was deleted; CourseDekho remains running.

**Checks completed so far:**

- `git submodule status` now succeeds; SDK and generated registrant are ignored.
- SDK HEAD and tracked files are unchanged. The native build created an untracked
  `packages/flutter_tools/gradle/.kotlin/` tool cache inside the SDK; it is not app
  source and the entire SDK stays ignored by the Groot repository.
- `docker compose config --quiet` and `docker compose up --build --wait` pass;
  Groot API and DB are healthy.
- `sh scripts/check-api.sh`: **3 tests passed** (one upstream TestClient deprecation warning).
- `python3 scripts/smoke_api.py`: live API, database readiness and **2 catalog rows** pass.
- SQL inspection confirms Neem/নিম and Okra/ঢেঁড়স.
- Flutter analysis and existing widget test pass.
- Native `flutter doctor -v`: Flutter and Android toolchain pass; Android emulator
  detected as `emulator-5554`, Android 16/API 36. Xcode/CocoaPods warnings concern
  unconfigured iOS/macOS targets, which are outside this task.
- Shell syntax, VS Code JSON, Compose/workflow/pubspec YAML and `git diff --check` pass.

**Android build/device results:** Native `sh scripts/check-mobile.sh` passes
(analysis, widget test, Android ARM64 debug APK). APK metadata confirms label
`Groot`, package `bd.groot.groot_app`, min SDK 24, compile/target SDK 36. On-device
smoke test `flutter test integration_test/catalog_smoke_test.dart -d emulator-5554
--dart-define=API_BASE_URL=http://10.0.2.2:8000` passes: **1 on-device test**, checking
both Bangla/English demo entries, two Demo chips, and completion of loading. Initial
sandboxed Gradle execution was stopped after native
file-watching access failed and Kotlin daemon discovery stalled; native execution
completed without changing project code. A parallel first-wrapper download also
caused a transient lock timeout before the native rerun.

**Preview handoff:** `sh scripts/preview-android.sh emulator-5554` passed service
startup/readiness, built and installed the normal `lib/main.dart` app, and attached
Flutter successfully. Visually checked the Groot title, readable Bangla heading,
Neem/নিম, Okra/ঢেঁড়স, two Demo chips and the setup-only disclaimer. Captured
`outputs/groot-android-preview.png` in the Codex task workspace (outside this repo).
Detached Flutter with `d`, leaving the app and emulator running. API and database
remain healthy. App source and original main/debug manifests have no diff.

**Risks / next step:** Demo-only catalog, no AI/account/care features yet. Local
HTTP is debug-only. Release signing is still the Flutter template's debug signing
and must be replaced before distribution. GitHub-hosted checks have been updated
but not executed remotely. The two index removals are staged; other changes remain
for review. No Git commit or push was made.

### 2026-10-03 — Establish data-safe versioned migrations and integration checks

**Why:** The starter used first-start `db/init` scripts without version tracking.
Those scripts cannot safely advance an existing volume, and mock-only API tests
did not exercise PostgreSQL constraints or preservation of user edits. The
implementation retains the small repository/SQL architecture and HTTP contract.

| File | Change | Reason |
| --- | --- | --- |
| `services/api/pyproject.toml` | Add Alembic/SQLAlchemy, pytest-cov and strict integration marker configuration | Declare migration tools and distinguish real-DB tests from unit tests |
| `services/api/constraints.txt` | Add verified exact dependency versions | Align local and CI installations without changing host Python |
| `services/api/Dockerfile` | Pin multiarchitecture Python image; include revisions/config; constrain dependency installs; copy historical SQL through a named test build context | Ship migrations with the runtime and test the actual old schema without running init SQL on startup |
| `services/api/alembic.ini` | Add checkout-relative migration configuration without credentials | Locate the version history consistently |
| `services/api/migrations/env.py` | Require the guarded runner's existing connection/transaction | Prevent raw Alembic calls from bypassing adoption and transaction safeguards |
| `services/api/migrations/script.py.mako` | Add revision template with deliberate unimplemented/rollback guards | Require reviewed implementations instead of accidental no-op revisions |
| `services/api/migrations/versions/0001_catalog_baseline.py` | Version the original tables/constraints without seed data; refuse destructive baseline downgrade | Initialize fresh databases and preserve catalog data during recovery |
| `services/api/migrations/versions/0002_species_source_index.py` | Add reversible nonunique `species.source_id` index | Index the existing FK without rewriting rows or changing relationships |
| `services/api/app/legacy_schema.py` | Validate exact known legacy tables, columns, defaults, constraints, indexes, triggers and RLS | Refuse blind adoption of drifted or partial schemas |
| `services/api/app/migrations.py` | Add transactional upgrade/current/check/baseline/downgrade CLI, advisory lock, bounded waits and redacted errors | Make schema/version updates atomic, adoption explicit and concurrent runner behavior predictable |
| `services/api/app/seed_demo.py` | Separate optional idempotent demo seed; preserve conflicting rows and refuse reviewed-source collisions | Keep schema changes independent of data seeding and avoid overwriting user edits |
| `services/api/app/database.py` | Check required migration head in readiness and qualify SQL tables with `public` | Detect pending/missing schema before declaring the service ready |
| `compose.yaml` | Pin the existing PostgreSQL 16 image, remove init mount, add one-shot migration prerequisite | Start API only after successful upgrade while retaining the existing volume |
| `compose.test.yaml` | Add standalone tmpfs PostgreSQL test stack, fixed test-only configuration and coverage gate | Avoid development data, ports and `.env`; run the same checks locally and in CI |
| `services/api/tests/test_migration_config.py` | Add configuration, URL handling and CLI/error tests | Cover tool wiring and avoid leaking credentials |
| `services/api/tests/integration/conftest.py` | Allocate owned random databases on the disposable server; load untouched old SQL as fixtures | Isolate tests and exercise genuine legacy adoption |
| `services/api/tests/integration/test_database.py` | Add real DB/API preservation, drift, constraint, failure, concurrency and rollback tests | Verify data integrity beyond mocks |
| `scripts/check-api.sh` | Supply named historical-SQL context for unit-test image | Keep the unit workflow compatible with the shared test target |
| `scripts/check-db.sh` | Add unique test-project lifecycle with failure logs and scoped cleanup | Make repeated local/CI runs reliable without removing development resources |
| `scripts/db.sh` | Add guarded migration/seed command helper with no dependency startup | Adopt legacy schemas before automatic migrations run |
| `scripts/preview-android.sh` | Explicitly seed after successful service startup | Preserve the demo preview while keeping migrations seed-free |
| `.github/workflows/checks.yml` | Run shared unit/integration scripts and check/seed the fresh demo stack | Validate database changes and startup ordering in CI |
| `.gitignore` | Ignore backups and coverage artifacts | Keep data archives and generated reports out of Git |
| `README.md` | Update schema/start/check commands, existing-volume guidance and Compose prerequisite | Match versioned startup and explicit demo seeding |
| `docs/ARCHITECTURE.md` | Describe migration boundary, locks, readiness and rollback behavior | Keep architecture guidance aligned with implementation |
| `docs/SETUP_MAC.md` | Update seed, legacy-volume and pending-migration troubleshooting | Avoid advising resets when an existing volume needs adoption |
| `docs/ROADMAP.md` | Mark starter migrations/checks as implemented and retain future schema extensions | Avoid planning the completed foundation twice |
| `docs/DATABASE_MIGRATIONS.md` | Document backup/restore rehearsal, adoption, upgrades, guarded rollback, authoring and test isolation | Provide an operator procedure with explicit data-loss boundaries |
| `AGENTS.md` | Add migration locations, guarded commands and integration-test/data-safety rules | Direct future agents to the established workflow |
| `builders.md` | Append this report | Record each file, reason, database impact and verification |

**Database impact:** Existing relationships/check constraints are unchanged.
Adoption creates only `public.alembic_version` at `0001`; upgrade adds only
`species_source_id_idx` and advances to `0002`. No catalog rows are rewritten,
deleted or automatically seeded. `0002 → 0001` removes only the new index;
baseline-to-base rollback is intentionally blocked. Schema DDL and version changes
share one transaction. Original `db/init/*.sql` are untouched historical fixtures.

**Backup and live preservation:** Created private ignored archive
`backups/groot-before-migrations.rmEQqy`; verified it with `pg_restore --list` and
restored it into a new isolated PostgreSQL container before live adoption. Full
source/species row snapshots before migration, after migration, and after backup
restore have identical SHA-256:
`1472a1e9000041ed3ab831549237d12d519cd53548c98c9a33d93e3403f63c47`.
The development volume `project-groot_groot_db` was retained, not reset.
Restore/test containers were temporary and removed; the backup remains.

**Checks:**

- TDD: the new migration-config test first failed against the old implementation
  with missing `app.migrations`. An initial integration fixture path error was
  corrected before the successful final runs.
- `sh scripts/check-api.sh`: **10 passed**, 31 integration cases deselected.
- `sh scripts/check-db.sh`: **41 passed**, **99.11% statement coverage**, exceeding
  the 90% gate. Covers fresh/idempotent upgrades, edited legacy rows, inactive
  flags, extra rows, Bangla/timestamps, 14 schema-drift cases, failed DDL/data
  rollback, concurrent lock rejection, FK/check/unique/null integrity, index
  rollback/re-upgrade, blocked destructive downgrade, real API filtering/sorting,
  limits, readiness and demo-source protection. One upstream TestClient/httpx
  deprecation warning remains; no test failure.
- Python and PostgreSQL image digests were inspected as multiarchitecture indexes
  supporting both ARM64 and AMD64. Tests ran locally on this ARM64 Mac, not on an
  AMD64 GitHub runner.
- `docker compose build api migrate` passed. Live `current` initially reported
  unversioned; `baseline --confirm`, `upgrade`, `check` completed at `0002`.
- `docker compose up --build --wait --wait-timeout 90` passed with migration exit 0,
  healthy API and database. `python3 scripts/smoke_api.py` passed with both Bangla
  catalog rows after adoption.
- A unique fresh Compose project used tmpfs DB storage and no published ports:
  migration completed before API readiness; catalog was initially empty; explicit
  seed produced two Bangla demo rows. The first ad-hoc HTTP probe used an incorrect
  route and returned 404; rerunning with the unchanged `/v1/catalog/species` route
  passed. Cleanup removed only this project's containers, network and local images.
- Normal/test Compose config, shell syntax and `git diff --check` pass. No diff in
  the original init SQL. Existing unrelated changes and local Flutter SDK retained.

**Skill influence:** `postgres-patterns` informed indexing the existing foreign key
without changing schema relationships; `python-testing` informed red-first checks,
isolated fixtures, real database assertions and the coverage gate.

**Risks / next step:** This is a local-development migration foundation for the
known public-schema starter on PostgreSQL 16, not production operations. Design
separate app/migration roles, backup retention and recovery objectives before a
shared deployment; review 5-second lock/60-second statement limits before larger
changes. Autocommit/concurrent-index operations need a separate reviewed workflow.
Runtime/dev versions and base images are pinned, but build bootstrap packages and
artifact hashes are not hermetically locked. GitHub-hosted CI was updated but not
run remotely. Mobile source/SDK and HTTP contract were not changed; Android checks
were not rerun in this database-only task. No Git commit or push was made.

### 2026-10-03 — Document a friend's first Mac setup and preview workflow

**Why:** Explain reopening Android Studio and provide a complete GitHub-clone to
Android-preview workflow rather than relying on this Mac's preinstalled tools.
Read the existing agent rules, product/architecture/README, setup guide and helper
scripts first. The scope is documentation only; existing local changes remain.

| File | Change | Reason |
| --- | --- | --- |
| `docs/SETUP_MAC.md` | Expand into a sequential first-Mac guide: Git, desktop tools, clone completeness, external Flutter SDK, Java/Android components and licenses, AVD creation, VS Code SDK setting, backend/seed verification, terminal and F5 preview, shutdown and troubleshooting | Let a friend reproduce the preview without Ashraf's account paths, ignored SDK or locally created AVD; explain reopening Studio and command-line fallback |
| `README.md` | Add a prominent first-time friend setup link and publication prerequisite | Make onboarding discoverable and avoid implying uncommitted setup files are already on GitHub |
| `builders.md` | Append this file-level report | Record scope, source checks and verification limitations |

**Database impact:** None. Documents existing migration and explicit demo seed
commands, private database networking and volume-preserving shutdown. Did not run
seed, upgrade, service startup, shutdown or database changes in this task.

**Evidence / skill influence:** Read `documentation-lookup`; its Context7 tools
were not available, so used official Flutter, Android, Docker, VS Code, Adoptium
and Python documentation directly. Verified welcome-screen and project Device
Manager entry points; retained repository-specific versions instead of blindly
switching to latest dependencies. Checked script argument behavior: AVD name vs
Flutter device ID, terminal-local SDK override priority, preview helper seeding,
and the VS Code launch configuration's lack of backend startup. Links are beside
the relevant guide instructions.

**Checks:**

- `git remote -v` confirmed the documented GitHub URL. `git status --short` and
  tracking inspection show essential setup files still need publishing; no commit
  or push was made.
- Read-only checks did not find Android Studio in `/Applications` or the user's
  Applications folder. The existing command-line emulator helper remains valid;
  the guide does not assume Studio is installed on this Mac.
- Cached Flutter metadata reports 3.47.6, while earlier Android verification/CI
  reference uses 3.47.5. Preserved this distinction; did not upgrade the SDK.
  A `flutterw --version` attempt was blocked by sandbox access to the SDK telemetry
  file; it was not counted as a successful SDK check and no extra access was sought
  for this documentation-only work.
- Docker Compose version inspected: v5.1.4. `docker compose config --quiet` passed.
- Shell syntax checks passed for all project shell scripts and wrapper. All
  **18 guide** and **6 README** fenced shell blocks pass `sh -n` without execution.
  Markdown fences balance, local file links resolve, and referenced scripts,
  Gradle wrapper and VS Code launch configuration exist. `git diff --check` passed.

**Risks / next step:** Installations and a new clone preview were not executed on
a second Mac or Intel Mac. Prior runtime verification is explicitly historical;
no fresh Android build or test-suite execution was necessary for this docs change.
Publish reviewed starter/setup files before your friend clones; do not commit
personal SDK paths or ignored secrets/backups. No app, API, emulator or database
configuration changed.

### 2026-10-04 — Source-traceable plant catalog and safe import boundary

**Why:** Research Bangladesh crop/tree evidence, separate public access from reuse
rights and agronomic approval, and prevent preview/demo data from becoming advice.
Read the repository rules, current API/schema, migration guard, product/architecture
and setup documentation before implementation. Announced the additive migration,
strict transactional import and fail-closed candidate boundary before changes.
Preserved unrelated local changes; no mobile source, Flutter SDK, dependency lock,
original init SQL or existing migration revision was changed in this task.

| File | Change | Reason |
| --- | --- | --- |
| `services/api/app/catalog_bundle.py` | Strict, size-limited JSON contract; typed units, dates, identifiers, URLs, citations, duplicate-key/reference checks | Reject malformed inputs and reserved demo identities without fetching external URLs |
| `services/api/app/catalog_import.py` | Offline validation by default; confirmed, locked, atomic append-only import with canonical SHA-256 and redacted errors | Preserve existing records, reject identity conflicts and make exact repeat imports a no-op |
| `services/api/migrations/versions/0003_reviewed_catalog.py` | Add source rights/review metadata, scientific names, import audits, profiles, facts, FK indexes and filtered view; block destructive downgrade | Store provenance without rewriting existing data; dynamically exclude unapproved or expired evidence |
| `services/api/app/database.py` | Read eligible profiles with field-level citations; validate requirement values again on read | Separate recommendation inputs from the preview catalog and fail closed on malformed direct-DB data |
| `services/api/app/main.py` | Add read-only `/v1/catalog/recommendation-candidates`; return 503 on unavailable/invalid catalog | Expose scoped reference data without pretending to implement personalized matching |
| `services/api/Dockerfile` | Copy catalog artifacts into the runtime image | Make the documented offline CLI usable from Compose |
| `services/api/catalog/bangladesh-starter-v1.json` | Three source records, three draft plants/profiles and eleven cited facts | Provide a small traceable research fixture, not falsely approved planting guidance |
| `services/api/catalog/treegoer-access-evidence.json` | Record exact-version public API/license evidence and publisher file metadata | Distinguish verified metadata access from an unperformed dataset download/checksum verification |
| `scripts/import-catalog.sh` | Add a root-level container CLI helper | Keep validation and explicit confirmed application reproducible |
| `services/api/tests/__init__.py` | Add test package marker | Reuse a validated fixture across unit and integration tests |
| `services/api/tests/test_catalog_bundle.py` | Add contract, malformed input, CLI confirmation and error-redaction tests | Exercise validation and no-write defaults before database application |
| `services/api/tests/integration/test_reviewed_catalog.py` | Add real PostgreSQL import, audit, conflict rollback, revocation/expiry, demo exclusion and constraint tests | Verify safety against the actual database, not only mocks |
| `services/api/tests/test_api.py` | Extend fakes and candidate route success/unavailable checks | Keep API behavior reliable when candidates are empty or DB access fails |
| `services/api/tests/test_migration_config.py` | Expect head revision `0003` | Match the new migration graph |
| `services/api/tests/integration/test_database.py` | Preserve explicit legacy-column snapshots; test old index rollback at `0002`, new head guard and synthetic `0004` failure | Avoid additive-column false failures while retaining prior data-preservation guarantees |
| `docs/CATALOG_SOURCES.md` | Record primary sources, access/reuse observations, exact locators, gaps and promotion prerequisites | Make evidence and uncertainty independently inspectable |
| `docs/CATALOG_IMPORT.md` | Document validation/application, contract, eligibility, append-only versioning, tests and recovery | Give operators a reproducible workflow that cannot silently turn drafts into advice |
| `docs/DATABASE_MIGRATIONS.md` | Document `0003`, blocked provenance rollback and separate catalog import | Keep schema and data operations distinct and preserve recovery guidance |
| `docs/SETUP_MAC.md` | Update current revision and explain optional draft import/empty candidates | Keep a friend's setup consistent without requiring research data for a demo |
| `README.md` | Link catalog research/import guides and qualify draft/preview scope | Make the new workflow discoverable without overstating completion |
| `docs/ARCHITECTURE.md` | Describe provenance schema and candidate boundary | Explain data flow and prevent general catalog reuse in care plans/RAG |
| `docs/PRODUCT.md` | Clarify mixed preview data versus approved advice | Keep product claims aligned with actual approval state |
| `docs/ROADMAP.md` | Record implemented foundation and outstanding rights/expert review | Do not mark the reviewed-data milestone complete prematurely |
| `AGENTS.md` | Require source, permission and agronomic checks separately; prohibit demo fallback | Preserve the safety boundary in future AI-assisted work |
| `builders.md` | Append this file-by-file report | Record why each file changed and what was actually verified |

**Research / approval status:** Checked primary BARC, AIS/DAE, SRDI, BFRI,
Forest Department/BFIS, ICRAF and TreeGOER resources on 2026-10-04. Several agency
fetches failed; this does not prove permanent unavailability. Exact TreeGOER2024.07
Zenodo API metadata returned HTTP200 and CC BY4, but no environmental data file
was downloaded or used as care advice. BARC/AFACI crop and ICRAF Neem facts have
page citations but unresolved artifact-specific reuse permission. Their three
profiles remain draft; AI evidence checking is not an agronomist's approval.
No accounts were created, protected pages bypassed or agencies contacted. See
the source report for primary links and limitations; no blanket government-content
license or Bangladesh suitability was assumed.

**Database impact / recovery:** Created the private backup
`backups/groot-before-reviewed-catalog.6OT0qb` with restrictive permissions,
validated its archive and successfully restored it into an isolated temporary
PostgreSQL container before applying `0003`. Restore rehearsal and live post-import
snapshots of all original source/species columns match SHA-256
`1472a1e9000041ed3ab831549237d12d519cd53548c98c9a33d93e3403f63c47`.
The existing development volume was retained. Only task-owned temporary test/restore
containers were removed; the backup remains recoverable. The live import hash is
`279f35ae8c8c7041aaf1929a1f39ab200f261fa54e2ec4d95dff348e085bcd06`;
the repeat application reported `already_imported=true`. Live totals are five
species (including the two preserved demo rows), three profiles, eleven requirements,
one import audit, and **zero eligible recommendation profiles**.

**Verification:**

- TDD: initial new test failed with missing `app.catalog_bundle` against the old
  image. An initial unsupported Pydantic negative-lookahead regex was replaced with
  a normal identifier regex plus an explicit reserved-ID validator.
- Final `sh scripts/check-api.sh`: **50 passed**, 56 integration cases deselected.
- Final `sh scripts/check-db.sh`: **106 passed**, **99.37% statement coverage**,
  above the existing 90% gate. Includes all prior migration checks and new real-DB
  catalog coverage. One upstream Starlette/httpx deprecation warning remains.
- Final `docker compose build api migrate` and live migration check passed at
  `0003`. Service startup completed healthy; `python3 scripts/smoke_api.py` passed
  with five Bangla catalog rows. The live candidate endpoint returned the intended
  empty array, with no fallback to demo or pending profiles.
- Normal/test Compose configuration, shell syntax, JSON syntax, documentation
  fences/local links/shell examples and `git diff --check` passed.

**Skill influence:** `research-ops` and `deep-research` informed separate access,
license and domain-review evidence; a read-only delegated tree-source review
supplemented crop research. `exa-search` connectors were unavailable, so official
web pages and direct HTTPS were used. `postgres-patterns` informed additive schema
changes and FK indexes; `python-testing` informed red-first validation, isolated
real-database tests and the existing coverage gate.

**Limitations / next step:** No approved plant profiles are supplied yet. Obtain
verified rights and an appropriate Bangladesh agriculture/forestry review before
importing approved versions. The importer trusts a local operator's assertions,
does not authenticate reviewers, and cannot promote/revise existing IDs in place;
new versions require reviewed new identities. Candidate eligibility is not a
complete care plan or district/container matching engine. Production DB roles,
conflicting-version resolution and personalized matching remain separate work.
GitHub-hosted CI was not run remotely; the existing CI check scripts passed locally
on this ARM64 Mac. Android checks were not rerun because no app source changed.
No Git commit or push was made.

### 2026-10-04 — Accounts, consent choices and private Plant Passports

**Outcome / why:** Added a complete local handle/password account and private
plant-record flow across the API, database and Android app. Inspected the existing
architecture, dependencies, catalog boundaries, migrations and dirty worktree
before coding; announced affected areas, the additive migration and privacy risks.
Optional preferences default off and do not activate GPS, sharing or analytics.
Species identification and care are self-reported, not recommendations or evidence
of verified survival. Existing unrelated work and the user's Flutter SDK were
preserved; no dependency declarations, historical init SQL or old revisions were
changed in this task. No accounts or personal records are automatically seeded.

| File | What changed | Why |
| --- | --- | --- |
| `services/api/migrations/versions/0004_accounts_passports.py` | Add accounts, hashed sessions, consent receipts, passports, care rows, rate buckets and indexes; block downgrade | Store owner-bound private data additively without erasing catalog/provenance |
| `services/api/app/accounts.py` | Strict private-data models; salted scrypt, opaque session hashes, transactional ownership/revocation, consent receipts, passport/care operations and shared throttling | Keep authorization and private writes server-side, bounded, validated and atomic |
| `services/api/app/account_routes.py` | Add typed register/login/me/consent/logout/password/delete and private passport/care routes | Expose the new flow without accepting caller-supplied owners or publishing personal data |
| `services/api/app/privacy_middleware.py` | Require TLS outside explicit development, bound even chunked bodies to 16KiB, add no-store/nosniff | Prevent HTTP credential use outside preview, excessive input buffering and private-response caching |
| `services/api/app/main.py` | Mount private routes/middleware, redact validation inputs, handle DB errors generically, update service description | Preserve existing public catalog contracts while protecting the new endpoints |
| `services/api/Dockerfile` | Disable implicit proxy-header trust in the runtime | Prevent callers from spoofing transport/client identity through untrusted forwarded headers |
| `services/api/tests/test_accounts.py` | Add password/schema/body-limit/redaction/resource-bound tests | Verify unsafe inputs and secret-handling behavior before real DB use |
| `services/api/tests/integration/test_accounts_passports.py` | Add real-DB ownership, session, consent, care, pagination, deletion, throttle and TLS checks | Prove two-account isolation and transactional security, including waiting-request expiry/revocation |
| `services/api/tests/test_migration_config.py` | Expect head `0004` | Keep graph checks aligned with the additive revision |
| `services/api/tests/integration/test_database.py` | Update current-head expectations/guard; move synthetic failed revision to `0005` | Retain original data-preservation and rollback tests without colliding with a real revision |
| `services/api/tests/integration/test_reviewed_catalog.py` | Expect new head and account rollback guard | Keep reviewed-catalog safety checks passing under the expanded schema |
| `apps/mobile/lib/private_api.dart` | Add immutable private models and a bounded HTTP client; memory-only bearer, safe errors, Bangladesh date helper and non-debug HTTPS guard | Keep secrets out of ordinary storage/URLs and support the new server contract |
| `apps/mobile/lib/private_garden.dart` | Add sign-in/register, off-by-default choices, garden, passport/conditions editor, dated care, password/logout/delete flows | Provide an accessible scrollable Android workflow with explicit destructive confirmations and async-state guards |
| `apps/mobile/lib/main.dart` | Add an account-icon entry and clarify browsing disclaimer | Make the private feature reachable without changing the catalog into advice |
| `apps/mobile/test/private_api_test.dart` | Check bearer headers, logout/401 clearing and safe errors | Verify token handling without real network requests |
| `apps/mobile/test/private_garden_test.dart` | Exercise register → passport → care → consent grant/withdrawal → sign-out and failure state | Verify private UI behavior and default choices with a fake API |
| `apps/mobile/integration_test/account_passport_smoke_test.dart` | Add live emulator UI test with a unique account and explicit owned-account cleanup | Verify phone → API → PostgreSQL and avoid leaving test personal data |
| `apps/mobile/integration_test/catalog_smoke_test.dart` | Select demo tiles specifically when research records share plant names | Preserve preview verification with the optional imported draft catalog |
| `docs/ACCOUNTS_PASSPORTS.md` | Document privacy notice/choices, API, storage/authorization, abuse controls, recovery limits, deletion and checks | Explain actual security behavior and what is still not production-ready |
| `docs/DATABASE_MIGRATIONS.md` | Add `0004`, blocked private-data rollback and next revision `0005` | Keep migration/recovery procedures truthful |
| `docs/CATALOG_IMPORT.md` | Explain that current head `0004` includes catalog revision `0003` | Match the guarded importer's head requirement |
| `docs/SETUP_MAC.md` | Update expected revision and explain account-icon preview/test credentials | Keep friend onboarding consistent with the new app |
| `docs/ARCHITECTURE.md` | Describe the identity/record data flow and transactional owner boundary | Separate private records from public catalog/model/analytics paths |
| `docs/PRODUCT.md` | Record implemented private/manual slice and limitations | Avoid claims of verified identity, recommendations, sharing or survival |
| `docs/ROADMAP.md` | Mark only the identity/record slice implemented | Keep suitability, reviewed data and production identity work outstanding |
| `README.md` | Add working-feature summary and account/privacy guide | Make the new workflow discoverable without overstating deployment readiness |
| `AGENTS.md` | Update current state and add owner/session/consent instructions | Prevent future AI work from bypassing authorization or activating collection from a saved preference |
| `builders.md` | Append this dated file-by-file report | Record implementation, verification, data effects and remaining risks |

**Security / skill influence:** `security-review` informed private defaults,
password/token handling, server ownership, body bounds, rate limits, safe errors,
HTTPS and explicit deletion. Primary OWASP password/session guidance was checked
and linked beside the choices in the account guide. Passwords use independent
16-byte salts and scrypt N=2^17/r=8/p=1, with two derivations maximum per process.
Session tokens contain 32 random bytes; PostgreSQL stores only their SHA-256 hash.
Tokens expire after 12 hours and are revocable; at most five sessions per account.
`fastapi-patterns` guided typed response models and thin transactional routes;
`postgres-patterns` guided additive schema, composite care ownership FK and query
indexes. `python-testing` guided red-first tests and isolated real PostgreSQL
checks; `dart-flutter-patterns` guided immutable models, async mounted checks,
safe client handling and widget fakes. No external auth/email/analytics provider
or new package dependency was introduced.

**Database preservation / deletion:** Before `0004`, created private backup
`backups/groot-before-accounts.t83mFL` (mode0600), listed its archive and restored
it successfully on an isolated temporary PostgreSQL server. Full source/species/
import/profile/requirement snapshots in the restore, live after migration and
final restarted stack match SHA-256
`0077093527a33588ddd5f198eddf2b7c0fd415cfd82495dad89b87f73f134af1`.
The development volume was not reset. Head is `0004`; catalog still has five
species and zero recommendation candidates. Live smoke tests created uniquely
named test accounts and explicitly deleted only those accounts and their owned
passports/care/consent/session rows. Final private table counts were zero, matching
their pre-test state. Only owned temporary test/restore containers/databases were
removed; the backup is retained. No existing user data was deleted.

**Checks and results:**

- Red-first: new unit test initially failed with missing `app.accounts` before
  implementation. The first DB run had 122 passes and two fixture/assertion issues
  (unset test catalog URL; a supposedly short password actually had 15 characters),
  corrected without weakening validation.
- Final security review reproduced a genuine expiry race: a session expiring
  while waiting on its owner lock was accepted using PostgreSQL's frozen transaction
  `now()`. The regression test first failed with no exception. A statistics-snapshot
  issue in the initial test probe was corrected so it observes the actual blocked
  query. Using `clock_timestamp()` after the lock now rejects the expired token.
- Final `sh scripts/check-api.sh`: **66 passed**, 70 integration cases deselected.
- Final `sh scripts/check-db.sh`: **136 passed**, **99.65% statement coverage**;
  account logic, routes, privacy middleware, new migration and main module each
  have 100% statement coverage. This is not proof against every possible attack.
  One upstream Starlette/httpx deprecation warning remains.
- `sh scripts/check-mobile.sh`: Flutter analysis clean; **6 tests passed**; Android
  ARM64 debug APK built. The original Flutter SDK was used, not upgraded/replaced.
  Upstream Kotlin/SDK XML and sandboxed FSEvents warnings did not fail the build.
- Live `account_passport_smoke_test.dart`: **1 passed**, including Bangla species,
  private care persistence and explicit test-account deletion; repeated successfully
  against the final corrected API. Live `catalog_smoke_test.dart`: **1 passed** with
  five preview rows and the two specifically selected demo tiles.
- Final runtime build/start, schema check and live API/database smoke passed.
  Normal/test Compose config, shell syntax and `git diff --check` pass. Nine updated
  Markdown files have balanced fences/resolvable local links; **38 shell examples**
  pass `sh -n` without executing them.
- Docker/emulator had stopped before the continuation, so those initial reruns
  could not execute. Reopened the installed Docker Desktop app and existing AVD;
  no reinstall, SDK replacement, AVD recreation or volume deletion was used.
  Sandboxed emulator CPU detection falsely reported missing NEON; the approved
  native launch booted the same `Groot_API_36` successfully.

**Remaining limits / handoff:** This is a local prototype, not a reviewed public
deployment. Real use needs TLS/trusted-proxy/perimeter configuration, least-privilege
DB roles, protected backups/retention and deletion-after-restore policy, identity
recovery/MFA and another security review. No email verification/recovery, secure
persistent mobile session, offline deduplication, GPS, photos, public sharing,
analytics, model access or automated care is implemented. Consent preferences
are inactive future-use choices, not blanket permission to collect. Sign-out clears
local state even when the server is unreachable; that server session then remains
until expiry. Records are private from other API accounts, not from privileged DB
operators. GitHub-hosted CI was not run; equivalent check scripts ran locally on
this ARM64 Mac. No Git commit or push was made.

**Preview handoff:** `sh scripts/preview-android.sh emulator-5554` rebuilt/installed
the normal `lib/main.dart` app, checked the healthy API and performed only the
existing idempotent demo seed. Detached Flutter with `d`, leaving the app and
`Groot_API_36` emulator running. The private account screen was visually inspected;
no render overflow was visible. A final standalone Flutter analysis was clean.
Open the app's account icon to create a test account or sign in. The API and DB
remain running; no credentials, passwords or session tokens are recorded here.

### 2026-10-04 — Four-step completion audit and Git handoff repair

**Outcome:** Re-audited the four user-requested slices against source, runtime,
Git index and fresh checks. Starter, safe migrations and local accounts/private
Plant Passports work. Catalog research/provenance/import/filter infrastructure
works, but actual reuse permission and Bangladesh agriculture/forestry approval
remain pending: three drafts, eleven facts, zero recommendation candidates.
No approved advice, production security certification or complete AI app is claimed.

**Root cause / plan:** The broken SDK gitlink had already been removed, but runner,
migration, catalog and private-feature files were still untracked. They worked in
the local worktree but would be omitted from a commit/clone. Announced a read-only
audit followed by a focused tracking/check/documentation fix, with no schema
changes. Existing user changes were retained. Used `verification-loop` for broad
checks, `security-review` for account/privacy inspection, `python-testing` for
red-first regression tests and `git-workflow` for a staged, uncommitted handoff.
The installed `repo-scan` is an installer pointer only; no external skill was
installed and no agents were spawned. Source rights findings were inspected as
recorded evidence, not fabricated approval or a new legal opinion.

| Changed file | What / why |
| --- | --- |
| `scripts/check_repo.py` | Add a read-only index gate for required handoff files, forbidden SDK/private/generated paths, executable wrapper modes and unresolved index stages; catch local-only files before sharing |
| `scripts/tests/test_check_repo.py` | Add seven isolated temporary-fixture regressions covering complete/missing/untracked source, missing disk files, SDK gitlinks/private paths, allowed defaults/JAR, executable modes and unrelated untracked notes |
| `.github/workflows/checks.yml` | Add a Python3.12 repository job running the gate/tests; retain existing API/DB/mobile/demo jobs |
| `.gitignore` | Ignore `.env.*` variants while explicitly allowing `.env.example`; reduce accidental credential-file tracking |
| `.gitattributes` | Add only the Windows launcher `text eol=crlf` rule; normalize its index representation without changing launcher logic or Windows checkout format |
| `apps/mobile/android/gradlew.bat` (index only) | Renormalize line endings under that attribute; resolve staged CRLF whitespace reports without editing generated launcher contents |
| `README.md` | Link the current four-step status and add repository checks |
| `docs/SETUP_MAC.md` | Clarify staged versus published files, add the handoff gate, and record actual verification with the unchanged local Flutter3.47.6/Dart3.13.5 SDK while retaining CI's earlier3.47.5 reference |
| `docs/MILESTONE_STATUS.md` | Add exact milestone status/evidence, remaining rights/expert approval procedure, and deployment/publication boundaries |
| `builders.md` | Record this audit, focused changes, verification, preservation and blockers |

**Git effects:** Staged the inspected project changes under `.github`, `.vscode`,
`apps/mobile`, `services/api`, `docs`, `scripts`, root agent/readme/builder/Compose
files and ignore/attribute rules. Prior feature implementation/file-by-file reasons
are in the earlier entries above; this audit did not rewrite those features.
The previously staged SDK-gitlink/registrant removals were retained. The local SDK,
`.env`, backups, generated registrant, caches and APKs remain ignored/untracked.
Git modes for `scripts/flutterw` and Android `gradlew` are100755. No Git history,
branch, remote, commit or push was changed. Staging is reversible and **is not
publication**; a GitHub clone remains old until the maintainer commits/pushes.

**Checks and results:**

- Red-first: the new handoff test initially failed because `check_repo.py` did not
  exist. After implementation, seven regressions pass. The real gate reproduced
  the untracked-file failure, then passed after reviewed files were staged.
- `sh scripts/check-api.sh`: **66 passed**,70 integration tests deselected.
- `sh scripts/check-db.sh`: **136 passed**, **99.65% statement coverage**;
  temporary owned project/database resources cleaned by the existing script.
- `sh scripts/check-mobile.sh`: analysis clean, **6 passed**, ARM64 debug APK built.
- Both live emulator integration files: **1 passed each** on `emulator-5554`;
  catalog loads and account → passport → dated care → explicit test-account deletion
  work through the actual API/PostgreSQL stack.
- DB `current`/`check`: **0004**. API/DB healthy; live smoke returns five Bangla
  catalog rows. Draft importer validates three sources/plants without DB writes.
- Staged-source export `/private/tmp/groot-handoff.B3S6S9` contains no SDK, `.env`
  or backups. Its full DB suite again passed136/99.65%; seven handoff regressions,
  six mobile tests, analysis and APK build also pass using the original external
  SDK. This is an exported-index rehearsal, not a GitHub clone or second Mac.
- Shell syntax, CI YAML parse, `git submodule status`, ignore checks, executable
  index modes and final `git diff --cached --check` pass. First staged diff check
  found CRLF-only Windows launcher whitespace; narrow attributes/renormalization
  fixed it without changing app logic. No generic whitespace suppression was used.
- Upstream Starlette/httpx deprecation and non-failing Flutter FSEvents warnings
  remain. The exported build reported a Kotlin daemon cache permission error but
  successfully completed using its fallback; no SDK replacement or toolchain
  configuration workaround was made. Remote GitHub Actions was not executed.

**Data / SDK preservation:** No schema migration, catalog import, bulk delete,
volume reset or existing-record edit was performed. Live aggregate counts before
and after the emulator test match: species5, profiles3, requirements11, candidates0,
accounts0, passports0, care0. The test deleted only its uniquely created account
and owned rows; throttle counters can change as normal test traffic. Existing
catalog and data-preserving migrations remain unchanged. SDK Git revision remains
`5fc346839b5d0eef006ed8404392afb4dfae428d` (Flutter3.47.6), identical before/after.
Started the existing stopped `Groot_API_36`; did not recreate it. The normal app
was relaunched after tests; Docker and Android preview are left available.

**Remaining limits / next authorization:** To complete the reviewed-content
milestone, supply verified artifact-specific reuse evidence and an appropriate
Bangladesh agriculture/forestry review, then prepare new immutable approved bundle
identities and apply using the backed-up confirmed workflow. No publishers or
reviewers were contacted. Do not promote draft flags simply to populate candidates.
The gate checks filenames/modes, not secret contents/history. Production TLS,
least-privilege roles, retention/recovery/MFA remain separate from the local
prototype. Review the staged diff before any separately requested commit/push.

## 2026-10-04 — Goal intake and reviewed suitability

**Outcome:** Added an authenticated Bangla-first/English goal form with optional
Android speech-to-editable-text, user-selected location precision, space/sun/soil
inputs and conservative deterministic suitability results. Matches include cited
reasons, uncertainty and review validity. Unsupported/incomplete/empty conditions
never fall back to demo/draft advice. The live catalog still has no approved
profiles; code completion is not agricultural approval or a deployed AI claim.

**Architecture / plan / skills:** Inspected existing catalog eligibility, account
transactions, middleware, mobile client and repository status before editing.
Announced a typed private transient endpoint, pure matcher, bilingual form and
small native voice channel, followed by API/DB/mobile/emulator checks and docs.
No schema change, saved goal/audio, external model or automatic GPS collection was
planned or added. Used `contract-first` to make OpenAPI/Pydantic authoritative and
share a Python/Dart fixture; `fastapi-patterns` and `dart-flutter-patterns` to keep
existing routing/client/state conventions; `security-review` to preserve private
transactions, chosen precision, redacted errors and disclosure; `python-testing`
for red-first rules/integration regressions; `verification-loop` for the final
gates. No sub-agents or new skills/dependencies were installed.

| Changed file | Change and reason |
| --- | --- |
| `services/api/app/goal_models.py` | Strict request/result/source contracts; chosen precision, bounded finite inputs and credential-free HTTPS citations |
| `services/api/app/recommendations.py` | Pure bilingual matching of exact reviewed scope/category/context, condition/season checks, explicit unknowns, earliest evidence expiry and bounded-search warning; no prose inference |
| `services/api/app/database.py` | Share the existing eligibility query within private transactions; include primary-source expiry without changing the view/schema or approval rules |
| `services/api/app/accounts.py` | Authenticate/recheck the session around transient matching and fail closed on malformed evidence |
| `services/api/app/account_routes.py` | Add typed private `POST /v1/goals/recommendations` under the existing throttle/dependencies |
| `services/api/app/privacy_middleware.py` | Extend no-store, TLS and16KiB private-body safeguards to goal routes |
| `services/api/tests/test_recommendations.py` | Synthetic rule/contract tests for matches, unknowns, conflicts, locale, unsupported scope, dates, precision, numeric limits, source expiry and bounded deterministic output |
| `services/api/tests/integration/test_goal_recommendations.py` | Real isolated DB/API tests: auth, no saved goals, demo exclusion, approved fixture/withdrawn rights, redaction/TLS/body limits, unavailable/invalid evidence and session expiry |
| `services/api/tests/fixtures/goal_contract.json` | Shared versioned request/empty-response example; prevent API/Flutter drift without importing fixtures into live data |
| `apps/mobile/lib/goal_models.dart` | Immutable consumer types, chosen-precision serialization and Bangla-number parsing |
| `apps/mobile/lib/goal_voice.dart` | Small optional Android platform-channel adapter; no audio capture/storage dependency |
| `apps/mobile/lib/goal_intake.dart` | Bilingual transient validated form, voice disclosure/edit/fallback, explicit selection inputs and cited result/uncertainty cards |
| `apps/mobile/lib/private_api.dart` | Authenticated recommendation POST and goal-specific safe validation errors; retain memory-only bearer/TLS behavior |
| `apps/mobile/lib/private_garden.dart` | Signed-in goal entry and clear garden state when the goal session expires |
| `apps/mobile/android/app/src/main/kotlin/bd/groot/groot_app/MainActivity.kt` | Device speech-activity bridge forbn-BD/en-US; cancel/unavailable/busy handling and offline preference without promising offline processing |
| `apps/mobile/test/goal_intake_test.dart` | Contract/client/channel/widget regressions for language, precision downgrade, validation, voice consent/edit/cancel/failure, citations and expired-session navigation |
| `apps/mobile/integration_test/account_passport_smoke_test.dart` | Add real native-channel invalid-language check (no microphone activation) and live Bangla goal/district/empty-approved-data flow before existing passport/care/deletion checks |
| `scripts/check_repo.py` | Require new goal source, tests, shared fixture and guide in the clone/handoff gate |
| `docs/GOALS_RECOMMENDATIONS.md` | Detailed preview, authoritative contract, deterministic rules, scope/expiry/privacy/voice limits, approval boundary and checks |
| `README.md` | Describe implemented goal entry and shared eligibility, link guide; keep AI/care generation explicitly planned |
| `docs/ARCHITECTURE.md` | Document transient authenticated matching and lack of new storage/providers |
| `docs/PRODUCT.md` | Update implemented product slice without claiming approved live content |
| `docs/ROADMAP.md` | Mark goal/rules slice implemented while separating approval, care generation and production identity work |
| `docs/SETUP_MAC.md` | Explain signed-in goal preview, expected empty approved result and device voice fallback |
| `docs/ACCOUNTS_PASSPORTS.md` | Clarify goals are not saved passports/consent receipts and do not start GPS collection |
| `docs/MILESTONE_STATUS.md` | Record subsequent goal slice without changing the earlier catalog-approval status |
| `AGENTS.md` | Update truthful current state and future-agent precision/evidence/voice boundaries |
| `builders.md` | Record exact changes, checks, preservation and remaining limits |

**Findings / fixes during verification:** Initial Python rule tests failed before
the matcher existed (red-first). New mobile tests then exposed that lazily
disposed off-screen form fields were omitted from `Form.validate()`. Replaced
that new form's lazy list with a mounted, scrollable column; blank goals and
invalid off-screen measurements now block submission. Test scrolling also needed
to dismiss field focus before navigating; missed taps are fatal in the new suite.
Analysis found missing multiline-if braces, which were fixed. Final inspection
added the earliest primary/requirement/profile expiry check, not just profile
expiry, with regressions. The repository gate initially failed on new untracked
goal files, as intended; source staging resolves the clone omission.

**Final checks:**

- `sh scripts/check-api.sh`: **105 passed**,75 integration cases deselected.
- `sh scripts/check-db.sh`: **180 passed**, **99.70% statement coverage**;
  goal models/rules/routes/account/query/middleware have100% statement coverage.
  The script cleaned its separate owned temporary PostgreSQL project.
- `sh scripts/check-mobile.sh`: analysis clean, **14 passed**, ARM64 debug APK
  built with the native Kotlin bridge and the existing local Flutter SDK.
- `flutterw test integration_test -d emulator-5554 ...`: **2 passed** through the
  actual local API/DB, including native-channel guard, catalog, Bangla goal form,
  private passport/care and explicit deletion of only a unique test account.
- Repository-check regressions: **7 passed**. Live API smoke: healthy, five Bangla
  catalog rows. Final repository tracking gate and staged/working whitespace checks
  pass; no unstaged changes or untracked project files remain.
- Existing Starlette/httpx deprecation and non-failing Flutter FSEvents warnings
  remain. One Android build reported a Kotlin daemon cache permission error and
  completed using fallback; later final builds completed normally. No SDK/cache
  workaround or toolchain upgrade was applied. Remote GitHub Actions was not run.

**Data / SDK / Git:** Schema remains`0004`; before/after live aggregates match:
species5, profiles3, requirements11, eligible candidates0, accounts0, passports0,
care0. No catalog import/promotion, applied-migration edit, volume reset or existing
record mutation. Test accounts were explicitly deleted with their owned test rows;
normal throttle counters may update. SDK revision remains
`5fc346839b5d0eef006ed8404392afb4dfae428d`. Rebuilt only local API/runtime images,
retained the existing emulator and stopped only the prior task-owned Flutter debug
attachment to run tests. Reopened and detached the normal preview afterward. Staged only the
28 feature/report files listed above, preserving earlier staged work. No commit,
push, branch/remote or Git history changes; SDK/secrets/caches/APKs remain ignored.

**Remaining limits:** Actual spoken Bangla/English recognition accuracy still
needs testing on a supported physical device/provider. The Android provider may
process online despite the offline preference; typing remains available. Goals
are not semantically parsed by an LLM; confirmed structured selections drive
rules. Exact `district:<name>` coverage is required, with a limited explicit
Bangla district-alias map; there is no geocoder or soil inference. Container
depth/root/substrate validation and full plot geometry remain uncertain. Reads
are capped at100 eligible profiles (with a non-exhaustive warning), results10;
add scoped pagination before large catalog expansion. Rights-cleared local
agronomic review must populate approved profiles before real planting advice.
Offline goals, care generation, weather, production TLS/recovery/MFA and provider
retention guarantees are not added by this slice.

## 2026-10-04 — Reviewed care plans and private immutable versions

**Outcome:** Added bilingual, personalized 1–12-week care previews using explicit
reviewed source text/timing, citations and review dates. Missing/conflicting
guidance stays visible and withheld; nothing is inferred from pH/spacing or demo
data. Explicit private save retains structured conditions, not free goal/soil
prose. Owner-only versions, optimistic revision/retry handling and live evidence
rechecks prevent historical instructions bypassing source changes/expiry.

**Skills:** `contract-first` shaped strict provider/consumer contracts and the
shared fixture; `fastapi-patterns`, `postgres-patterns` and `dart-flutter-patterns`
kept existing transaction/service/UI conventions; `security-review` preserved
owner checks, no-store/errors and explicit storage disclosure; `python-testing`
and `verification-loop` drove red-first regressions and migration/data checks.
No subagents, providers, dependencies or SDK upgrades were introduced.

| Changed file | What and why |
| --- | --- |
| `services/api/app/care_models.py` | Authoritative preview/save/revision/version/issue/citation contracts; callers cannot submit owners or plan snapshots |
| `services/api/app/care_plans.py` | Pure selected-profile matching, scoped reviewed directives, future validity, conservative overlap conflicts, dated ordered instructions, coverage gaps and reproducible evidence/content hashes |
| `services/api/app/care_repository.py` | Owner-locked transactional preview/save/history/revise/delete, independent care-source gates, bounded evidence, idempotent creation/CAS revision and withheld stale snapshots |
| `services/api/migrations/versions/0005_grounded_care_plans.py` | Add guidance/plans/versions/FKs/indexes/UPDATE trigger, no existing data changes or seed; destructive downgrade blocked |
| `services/api/app/catalog_bundle.py` | Validate optional bilingual reviewed guidance, week/topic/review rules, UTF-8, global IDs and source references |
| `services/api/app/catalog_import.py` | Atomic append-only care import; omit empty care arrays to preserve old schema-v1 canonical hashes |
| `services/api/app/database.py` | Optional selected-profile filter before the100-candidate cap; retain the exact eligibility boundary |
| `services/api/app/account_routes.py` | Eight private typed care endpoints under existing authentication/throttle/error handling |
| `services/api/app/privacy_middleware.py` | Extend private no-store/TLS/body safeguards to plans |
| `services/api/tests/test_care_plans.py` | Synthetic generation/validation/contract/localization/coverage/conflict/expiry/prose-redaction/order regressions |
| `services/api/tests/integration/test_care_plans.py` | Disposable DB tests for ownership, independent source withdrawal, immutable/stale versions, retries/CAS, corruption/row bounds, transaction expiry, old rows/hash preservation and blocked downgrade |
| `services/api/tests/fixtures/care_contract.json` | Shared synthetic provider/Flutter contract; never imported as live agricultural guidance |
| `services/api/tests/test_migration_config.py` | Assert new single head0005 |
| `services/api/tests/integration/test_database.py` | New head expectations; intentional failing test revision now0006, preserving failure/rollback tests |
| `services/api/tests/integration/test_reviewed_catalog.py` | Expect0005 after full catalog upgrade |
| `services/api/tests/integration/test_accounts_passports.py` | Expect0005 while preserving existing identity/record assertions |
| `apps/mobile/lib/care_models.dart` | Immutable preview/instruction/issues/version/history consumer types and current save notice |
| `apps/mobile/lib/care_plan_view.dart` | Preview horizon, explicit save disclosure/retry identity, citations/review dates, structured conditions, history/revision/deletion, hidden stale/blocked advice and visible save/error feedback |
| `apps/mobile/lib/saved_care_plans.dart` | Paginated private saved list, current-evidence recheck navigation and revision back into goal form |
| `apps/mobile/lib/goal_models.dart` | Reconstruct saved structured conditions without adding persistence to ordinary goals |
| `apps/mobile/lib/goal_intake.dart` | Preview from the submitted result conditions, populate explicit revision form and clarify separate care-saving privacy |
| `apps/mobile/lib/private_api.dart` | Private care API methods, required notices and safe care-specific409/422 errors |
| `apps/mobile/lib/private_garden.dart` | Signed-in saved-plan entry; clear garden session after nested expiry |
| `apps/mobile/test/care_plans_test.dart` | Shared contract/private client and widget checks: explicit partial saving, stable retry UUID, blocked/stale withholding, revision and saved-condition intake |
| `apps/mobile/integration_test/account_passport_smoke_test.dart` | Live empty-plan/blocked-preview checks without approving demo; dismiss keyboard before existing save taps for reliable emulator scrolling |
| `scripts/check_repo.py` | Require care source/tests/migration/fixture/guide in clone/handoff checks |
| `docs/CARE_PLANS.md` | Full usage, source-authoring/timing review, conflict limitations, API/version/privacy/migration/check procedures |
| `docs/DATABASE_MIGRATIONS.md` | Document additive0005 and blocked rollback; next revision example0006 |
| `docs/CATALOG_IMPORT.md` | Optional guidance/atomic import and backward-compatible manifest rules; current head |
| `docs/GOALS_RECOMMENDATIONS.md` | Separate transient matching from explicit care-condition storage and care workflow |
| `docs/ACCOUNTS_PASSPORTS.md` | Explicit plan storage/deletion boundary without GPS/audio/consent expansion |
| `docs/ARCHITECTURE.md` | Current care data flow, independent gates, snapshots and evidence withholding |
| `docs/PRODUCT.md` | Truthful implemented slice and approved-content/weather/LLM limits |
| `docs/ROADMAP.md` | Mark plan slice implemented without claiming quests/weather complete |
| `docs/SETUP_MAC.md` | Head0005, app care navigation, explicit storage and expected unavailable approved guidance |
| `docs/MILESTONE_STATUS.md` | Subsequent care slice, distinct from prior four-milestone audit/content approval |
| `README.md` | Feature entry/navigation/privacy/guide and current migration head |
| `AGENTS.md` | Current care status and future-agent immutable/evidence/privacy boundaries |
| `builders.md` | This exact-file report, checks, preservation and remaining limits |

**Verification findings:** Initial unit test failed before the care module existed.
Strict source models caught extra fixture-only fact fields; corrected fixtures,
not contracts. Flutter mocks required UTF-8 JSON; lazy-list tests needed scoped
scrolling. Save failures/success now scroll feedback/version into view. Emulator
save taps needed keyboard dismissal before scrolling. Independent source tests
initially used unsupported source states; corrected them to existing constrained
states (`login_required`/`demo`) and ordered expiry dates, without weakening DB
constraints. No applied migration was edited.

**Checks:** Unit API125 passed (89 integration deselected); full isolated DB/API
214 passed,99.71% statement coverage. New care models/generator/repository,
catalog validators, routes and0005 have100% statement coverage. Mobile analysis
clean,20 tests passed and ARM64 debug APK built. Two actual emulator/live API
tests passed (catalog, accounts/goals, saved empty list, blocked preview,
passport/care and explicit deletion of only the unique smoke account). Seven
repository-check regressions passed. Live API smoke reports healthy with5 Bangla
catalog rows; guarded current/check report0005. Final handoff gates are recorded
below after source staging. Remote GitHub Actions was not run. Existing non-failing
Starlette/httpx and Android SDK XML-version warnings remain.

**Data preservation:** Created mode600 ignored backup
`backups/groot-before-care-plans.ZbuZPr`; pg_restore archive inspection passed.
Restored into new isolated tmpfs project `groot-care-restore-1791136000` using
`--no-owner --no-privileges --exit-on-error`; restored0004 counts matched catalog5,
accounts1, passports1, care1. Removed only that owned temporary restore project.
Applied additive0005 and rebuilt compatible API. Existing account/passport/care
table fingerprints before/after migration matched exactly. No current volume
reset, catalog approval/import, user record deletion, secrets output or old
migration changes. Tests approve synthetic content only inside isolated databases.
Local Flutter SDK revision remains `5fc346839b5d0eef006ed8404392afb4dfae428d`.

**Limits:** Live approved candidates/care guidance remain0. Rights-cleared local
expert review must supply real directives before useful planting/care advice.
Schema/text comparison cannot validate agronomic truth or semantic contradiction;
both translations, timing, context and safe non-treatment content require human
review. No LLM/weather/tasks/offline/provider integration, chemical-treatment
safety validation or new consent collection. Snapshots retain chosen conditions
until owner plan/account deletion; timed retention/production roles/TLS/recovery
remain future work. Saved status is not current advice; evidence is rechecked
when opened, and users must explicitly revise changed site conditions.

**Final handoff:** Required-source tracking gate and working/staged whitespace
checks passed after staging only the feature/report files listed above, preserving
earlier staged work. No commit, push, branch/remote or history changes. Final local
aggregates: schema0005, catalog5, existing accounts1/passports1/care1,
eligible profiles0, care directives0, plans0/versions0. The local API is healthy;
the existing SDK, private backup and current Docker volume are preserved.
Reopened the normal Android preview on `Groot_API_36`/`emulator-5554`, detached
Flutter without stopping the app and confirmed its process remained running.
Existing private table fingerprints still matched after the final live tests.

## 2026-10-05 — Main-branch publication preparation

**Request and plan:** Preserve the full current project change set and publish
exactly10 logical commits directly to `origin/main`, using only the owner's
author/committer identity. No new branch, pull request, force push, amendment,
reset or existing-history rewrite. Groups: repository/toolchain hygiene, Android
runner, safe database infrastructure, reviewed catalog, private backend workflows,
mobile workflows, local checks, continuous integration, Mac setup, product and
engineering documentation. Commit messages contain only normal developer subjects
and no attribution trailers.

**Identity verification:** Existing authenticated account is `ASHFOX474`
(account ID203048828), with push permission for `ASHFOX474/Project-Groot`.
The previous globally configured university email links existing commits to
`Ashraf-HC`, not the requested account. Kept name `Ashraf` and set this repository's
email to `203048828+ASHFOX474@users.noreply.github.com`; global config is untouched.
Author/committer identities were checked before committing. Existing GitHub
credentials were used in memory only, without output or new credentials.

**Inspection and preservation:** Inspected117 staged paths, additions/modifications,
both intended tracking removals and all available untracked project paths
(none). Staged content/JSON and secret-pattern inspection passed. The SDK gitlink
tracking removal preserves the physical local Flutter SDK. Generated registrant
tracking removal preserves normal generated build output. `.env`, private backups,
SDK/build caches, local.properties, temporary files and credentials are excluded.
The three existing staged `.vscode` editor configurations remain local, preserved
without deletion/reset. No application/source redesign or database migration is
performed in this publication task. Temporary per-commit indexes use the reviewed
staged blobs so grouping cannot overwrite working files or lose staged content.

**Files changed in this task:** `builders.md` adds this preparation/check record.
Repository-local `.git/config` changes only author email/name attribution. All
other committed files are preserved existing work; no unrelated edits are added.

**Checks before publication:** `scripts/check-db.sh` passed214 tests with99.71%
statement coverage in its own disposable database project; it cleaned only owned
temporary resources. `scripts/check-mobile.sh` passed analysis,20 tests and ARM64
debug APK build using the existing SDK. Repository tracking gate, seven gate
regressions and staged/working whitespace checks passed. Existing non-failing
Starlette/httpx warning remains. Live API/data are not reset. Local/remote `main`
matched at the start. Final count, both identities, messages, tree preservation
and remote fast-forward compatibility are rechecked before the normal push;
remote commit attribution will be checked after publication and reported in chat.

## 2026-10-05 — Care quests, district weather and generic reminders

**Outcome:** Implemented daily observation check-ins and weekly reviews of cited
care instructions, owner/version-scoped retry-safe completion/undo, explicit
per-version district-weather opt-in, bounded forecast cache and stale/unavailable
fallback, in-app pending counts and optional generic Android reminders. The source
format lacks exact care frequency: weekly reviews do not invent weekly watering
or fertilizer schedules. Rain/heat only add monitoring checks; no irrigation
suppression/increase, doses, offline queue, rewards or fake approvals.

**Files changed and why:**

- `services/api/app/quests.py`: strict task/preference/completion contracts and pure
  Bangladesh-date scheduler, unchanged cited text, partial-plan disclosure and
  weather check notes gated by retrieval freshness/coverage.
- `services/api/app/weather.py`: fixed-host HTTPS Open-Meteo adapter, supported
  chosen district aliases/reference points, validated bounded payload, retrieval
  timestamp and explicit unknown model age; operator mode defaults off.
- `services/api/app/quest_repository.py`: short transactional owner/session and
  evidence gates around provider I/O, shared eight-key15-minute cache claims,
  retry-safe completion and latest-version preference/retention isolation.
- `services/api/app/account_routes.py`: three authenticated, limited quest routes
  under existing no-store/body/TLS/privacy protections.
- `services/api/migrations/versions/0006_quests_weather.py`: new completion,
  per-version weather preference and public regional cache tables/indexes only;
  composite ownership/version FKs and blocked destructive downgrade.
- `services/api/tests/test_quests.py`, `services/api/tests/test_weather.py`,
  `services/api/tests/integration/test_quests.py`: scheduling, immutable advice,
  partial gaps, weather transport/failure/freshness, opt-in, isolation, retries/undo,
  cache corruption, post-fetch revocation, migration preservation/cascade tests.
- `services/api/tests/test_migration_config.py` and integration
  `test_database.py`, `test_accounts_passports.py`, `test_care_plans.py`,
  `test_reviewed_catalog.py`: update expected head to0006; simulated failing next
  migration becomes0007. Existing historical migrations are unchanged.
- `apps/mobile/lib/quest_models.dart`, `quest_board.dart`: immutable parsing,
  task/check-off UI, clear weather freshness/provenance/notice, pending reminders,
  safe online failure and foreground/resume refresh. Device reminder is separate.
- `apps/mobile/lib/care_reminders.dart`: minimal native channel and safe fallback.
- `apps/mobile/lib/care_plan_view.dart`: latest-plan navigation to quests; historical
  versions cannot open an old task board.
- `apps/mobile/lib/private_api.dart`: private task client and injectable session-
  clear callback; keeps plain HTTP tests independent of platform services.
- `apps/mobile/lib/private_garden.dart`: wires reminder cancellation to actual
  logout/401/password/deletion/disposal lifecycle.
- Android `app/src/main/kotlin/bd/groot/groot_app/CareReminder.kt`, `MainActivity.kt`
  and `app/src/main/AndroidManifest.xml`: optional POST_NOTIFICATIONS request,
  private receiver and generic inexact daily alarm; cancel on new engine/session
  clear, including pending permission callbacks. No exact-alarm/location permission,
  private notification content or extra package dependency.
- `apps/mobile/test/quests_test.dart`, `care_reminders_test.dart` and
  `integration_test/quests_smoke_test.dart`: stale UI/check-off/fallback regressions
  and actual emulator reminder bridge enable/status/cancellation smoke.
- `.env.example`, `compose.yaml`: documented off-by-default provider mode; existing
  private `.env` is untouched and live mode remains disabled.
- `docs/QUESTS_WEATHER_REMINDERS.md`: detailed scheduling, conservative adaptation,
  provider terms/privacy/attribution, unknown model age, native reminder limitations,
  API, retention and migration/setup procedures. Primary sources checked2026-10-05.
- `docs/testing/quests-weather-reminders.tdd.md`: RED/GREEN journeys, test mapping,
  actual commands/results, preservation and unverified platform/provider gaps.
- `README.md`, `AGENTS.md`, `docs/PRODUCT.md`, `ARCHITECTURE.md`, `CARE_PLANS.md`,
  `ACCOUNTS_PASSPORTS.md`, `DATABASE_MIGRATIONS.md`, `SETUP_MAC.md`,
  `MILESTONE_STATUS.md`: current scope, new privacy boundary,0006 operations and
  preview path; no planned features represented as deployed capabilities.
- `scripts/check_repo.py`: require new source/migration/test/guide paths at handoff.
- `builders.md`: this file-level outcome/check/risk report.

**Skills:** Read FastAPI, Dart/Flutter, PostgreSQL and TDD skills before work.
They guided thin typed routes, owner-scoped transactions, immutable client models,
safe async lifecycle and test-first work. Repo/user instructions override TDD's
checkpoint-commit recommendation: no unrequested commit or staging was made.

**Checks:** API unit136 passed (subset of total); isolated PostgreSQL suite231
passed,99.64% statement coverage/90% gate; Flutter analysis clean,23 tests passed,
normal ARM64 debug APK built. One API36 emulator smoke passed with synthetic HTTP
fixtures and real reminder enable/status/cancel. Seven handoff regressions and
working diff whitespace checks passed. Real-index handoff intentionally fails on
new untracked files pending user staging/commit approval; not represented as PASS.
No remote CI run/push. Existing upstream Starlette/httpx warning remains.

**Data and preview:** Backed up to private ignored
`backups/groot-before-0006.2D5scr`; restored in isolated no-network tmpfs PostgreSQL
and matched data-only hashes. Applied guarded0006 upgrade and restarted API.
All14 original tables' counts/exact hashes unchanged; five-species live smoke,
three OpenAPI quest routes and disabled provider mode verified. Preserved existing
account/passport/care and draft catalog; no seeds/import promotion/reset. Temporary
test/restore servers cleaned only their owned resources; backup retained. Existing
Flutter SDK and its untracked DevTools file unchanged; three staged `.vscode`
files, Git branch/history/identity and credentials untouched. Emulator test package
was removed by Flutter; normal app reinstalled, notification permission returned
to its original denied state. Actual preview remains on the existing emulator.

**Limits:** Approved content remains pending, so real plan/task lists may be empty.
Non-commercial weather needs operator terms review plus user notice; no actual
provider availability/plot accuracy claimed. Provider socket timeout isn't a hard
DNS/total deadline. Model issue time unknown. Generic device reminders do not
promise tasks are due, exact delivery, forecast refresh or reboot/timezone recovery.
Native scheduling/cancellation tested, not notification presentation/Doze delivery.
Production security/TLS/roles, offline queue, automatic irrigation changes and
passport linkage remain separate. Existing remote SDK `tools` CI failure unchanged.

## 2026-10-05 — Opt-in offline care notebook and retry-safe sync

**Outcome:** Added Android-only, explicitly enabled downloaded plan/passport
viewing and manual care recording without network access. The encrypted durable
outbox reuses its original UUID on retry; the backend appends once instead of
overwriting history. Conflicts stay visible for review. No offline login, fresh
weather/recommendations, passport edits, photos or queued quest completion.

**Files changed and why (this task; prior quest work preserved):**

- `apps/mobile/lib/offline_care.dart`: bounded, serialized, durable notebook/outbox,
  owner UUID/server binding, atomic inventory replacement, retry/conflict rules,
  pending-removal protection, immediate lifecycle invalidation against late sync
  overwrites and conservative cached-instruction withholding.
- `apps/mobile/lib/offline_care_view.dart`: separate opt-in/download/unlock UI,
  cited plan snapshots, offline care form, pending/synced/review states, explicit
  local erase, foreground retry and background/five-minute/exit locking.
- `apps/mobile/lib/private_api.dart`: remember account UUID only in memory;
  verify live owner, fetch raw version snapshots, submit stable care UUIDs and
  retain HTTP status for conflict handling. Bearers remain memory-only.
- `apps/mobile/lib/private_garden.dart`: expose the notebook from the account
  screen even when signed out; reuse the existing care form as public `CareForm`.
  A formatter/lint brace correction preserves the existing sign-out behavior.
- `apps/mobile/android/app/src/main/kotlin/bd/groot/groot_app/OfflineCareVault.kt`:
  bounded AES-256-GCM blob using an authenticated Android Keystore key, no-backup
  private storage and AtomicFile; no plaintext/corruption-erasure fallback.
- `apps/mobile/android/app/src/main/kotlin/bd/groot/groot_app/MainActivity.kt`:
  device-credential confirmation, serial vault bridge, lifecycle/generation gates
  and screenshot/recents protection. Existing voice/reminder bridges preserved.
- `apps/mobile/android/app/src/main/AndroidManifest.xml`: disable app backups
  because the opted-in notebook contains private plant conditions/care notes.
- `apps/mobile/test/offline_care_test.dart`:25 unit/widget tests for durability,
  retries, storage/transport failures, limits, conflicts, owner isolation,
  opt-in/citations/manual entry/erase, timeout, bridge arguments and reopened-
  notebook protection from a late sync acknowledgment.
- `apps/mobile/integration_test/offline_care_smoke_test.dart`: synthetic
  offline entry/reopen/sync-once plus real native locked/no-screen-lock refusal;
  no live account creation, care writes or agricultural approval.
- `services/api/app/accounts.py`: optional strict UUID care input, unchanged public
  response, owner-transaction replay lookup/content comparison and UUID insert.
- `services/api/migrations/versions/0007_offline_care.py`: new nullable retry column
  and partial owner-scoped unique index only; downgrade refuses deduplication loss.
- `services/api/tests/integration/test_offline_care.py`: five PostgreSQL tests for
  concurrent/repeated submission, changed-content conflicts, ownership/deletion,
  date/legacy compatibility and additive migration/blocked rollback.
- `services/api/tests/test_migration_config.py`: expect new head0007.
- `services/api/tests/integration/test_database.py`: expect head0007 and move the
  simulated failing future migration to0008/down0007.
- `services/api/tests/integration/test_accounts_passports.py`,
  `services/api/tests/integration/test_care_plans.py`,
  `services/api/tests/integration/test_reviewed_catalog.py`,
  `services/api/tests/integration/test_quests.py`: update current-head assertions
  and downgrade safety-message expectations; preserve existing behavior tests.
- `.gitignore`: keep generated mobile coverage out of the repository.
- `scripts/check_repo.py`: require offline source/migration/tests/docs at handoff
  and reject tracked coverage artifacts, without staging anything.
- `docs/OFFLINE_CARE.md`: setup, privacy/shared-device tradeoffs, precise persistence
  and conflict rules, capacities, stale evidence, migrations and secure-device
  verification limits; primary Android documentation checked2026-10-05.
- `docs/testing/offline-care.tdd.md`: reproducible RED/GREEN evidence, measured
  checks/coverage, native fixture boundaries and live-data preservation record.
- `README.md`: current offline capability and setup-guide entry point.
- `AGENTS.md`: current capability and safeguards for future offline changes.
- `docs/PRODUCT.md`: separate notebook opt-in and implemented versus planned scope.
- `docs/ARCHITECTURE.md`: encrypted local boundary, owner/server retry flow and
  exclusions from offline operations.
- `docs/CARE_PLANS.md`: offline version/citation retention and stale withholding.
- `docs/ACCOUNTS_PASSPORTS.md`: optional care retry contract, memory-only auth and
  explicit sign-out/notebook retention tradeoffs.
- `docs/QUESTS_WEATHER_REMINDERS.md`: distinguish manual offline care from online
  version-bound quest completion/weather.
- `docs/DATABASE_MIGRATIONS.md`: latest revision0007, nullable additive impact,
  next revision0008 and forward-fix rollback guidance.
- `docs/SETUP_MAC.md`: device-lock requirement, download/record/reconnect preview
  instructions and current migration expectation.
- `docs/ROADMAP.md`: mark the bounded offline-care slice separately from unbuilt
  photos, passport edits and background/production work.
- `docs/MILESTONE_STATUS.md`: actual offline scope/checks and remaining native
  credential/crypto verification gap.
- `builders.md`: this exact file-level outcome, verification and risk report.

**Skills:** Read Dart/Flutter, FastAPI, PostgreSQL, security-review and TDD skills.
They informed serialized immutable state, owner-scoped transaction/idempotency,
additive migration, opt-in/Keystore/no-token storage and test-first safeguards.
The project prohibition on unrequested commits overrides checkpoint-commit
examples; RED/GREEN is recorded in the test evidence instead.

**Checks:** Initial Flutter RED referenced unimplemented notebook contracts;
the first targeted DB run executed five tests with four failing/one passing.
The pending-removal regression also failed before its guard. Final security review
reproduced a late acknowledgment overwriting a reopened notebook; immediate store
invalidation and pre/post-write gates fixed it, with a passing regression.
Final isolated
PostgreSQL suite236 passed,99.58% statement coverage (90% gate); network-isolated
API unit/config suite136 passed with100 integration tests deselected. Flutter
analysis clean,48 tests passed, including25 offline tests; normal ARM64 debug
APK built. Offline queue core174/187 executable lines covered (93.05%, not a
whole-app coverage claim). Emulator fixture/native-refusal smoke passed; native
credential/encryption success is not claimed. Seven handoff regressions and
working whitespace checks passed. Actual Git-index handoff fails because prior
quest/new offline source remains untracked; no staging/commit/push/remote CI.
Existing Starlette/httpx warning and historical remote mobile SDK failure remain.

**Data and preservation:** Private ignored backup
`backups/groot-before-0007.v7Aq6S` restored in an isolated no-network tmpfs
PostgreSQL container; all17 existing tables' counts/canonical hashes matched.
Applied guarded0007 and restarted the compatible API. All17 old tables' values
unchanged (comparison excludes only new nullable `request_id`); API healthy and
five-species Bangla live smoke passed. No reset, seed, catalog promotion or old
migration edit. Removed only the owned temporary restore container; backup and
live database retained. Existing Flutter SDK/DevTools file, three staged VS Code
configs, Git main/history/identity and credentials preserved.
Final read-only comparison again matched all17 tables. The final emulator smoke
passed after the lifecycle fix; its test package was replaced by the rebuilt
normal APK, installed and launched for preview. Emulator lock settings unchanged.

**Limits:** Emulator has no screen-lock credential; no authorization was received
to change it. Native successful unlock/encrypt/decrypt, key invalidation and
process-kill recovery need secure-device manual checks. Fixtures are not native
crypto proof. Local data deliberately survives logout until explicit erase;
anyone knowing the device credential can unlock it. Remote deletion/revocation
cannot erase a disconnected device and clock tampering cannot be solved offline.
No persisted bearer/password or silent pending eviction. Foreground retries only;
one account/server notebook,50 plants/50 plans/500 local care records/2MiB cap.
Approved live care content is still pending, so real plan lists may be empty.
Production security/TLS/roles/recovery and broader offline workflows remain separate.

### 2026-10-05 — Align private photo check-in disclosures

**Why:** Private photo check-ins and bounded observation assistance were already
implemented, but product, architecture, roadmap, milestone, account/privacy and
in-app notices still described photos as entirely unimplemented.

| File | Change | Reason |
| --- | --- | --- |
| `README.md` | Document opt-in private photo check-ins and clarify validated disease AI remains pending | Keep the top-level feature inventory accurate |
| `AGENTS.md` | Describe the private photo observation prototype and its non-diagnostic boundary | Keep agent context aligned with the current repository |
| `apps/mobile/lib/private_garden.dart` | Clarify that photo storage is a separate opt-in | Prevent the in-app privacy notice from contradicting the feature |
| `docs/PRODUCT.md` | Add the implemented private timeline and heuristic-assistance limits | Document consent, uncertainty and expert-help behavior |
| `docs/ROADMAP.md` | Mark local photo check-ins and observation assistance implemented | Remove stale roadmap claims while retaining future model work |
| `docs/ARCHITECTURE.md` | Add private photo storage/assistance to current boundaries | Reflect the actual API, mobile and database flow |
| `docs/ACCOUNTS_PASSPORTS.md` | Replace the obsolete “no uploads” row with the separate photo-consent boundary | Keep privacy choices accurate |
| `docs/MILESTONE_STATUS.md` | Record the subsequent private-photo prototype slice and test evidence | Preserve delivery history and limitations |
| `builders.md` | Record this documentation/privacy alignment | Satisfy the project change-report requirement |

**Database impact:** None. Existing migration `0008_private_photos` and photo
tables were unchanged.

**Checks:** `sh scripts/check-db.sh python -m pytest -q tests/test_photos.py tests/integration/test_photos.py` passed 29 tests with two non-failing warnings. `../../scripts/flutterw test --suppress-analytics test/photo_checkins_test.dart` passed 7 tests. `git diff --check` passed.

**Risks / next step:** The local heuristic remains unvalidated and cannot diagnose
disease or recommend chemical/dose changes. Successful Keystore/device-credential
behavior still needs a secure-device manual check; public sharing and external model
providers remain unimplemented.

### 2026-10-06 — Add survival rewards and moderated community

**Outcome:** Added transparent, self-reported care streaks and 3-, 6- and
12-month milestone cards. Garden scores average capped per-plant scores, so raw
plant count adds no points. Added a consented district profile, pending/approved
community posts, reporting with three-report auto-hide, moderator review routes,
pseudonymous feed output and five-grower k-anonymous neighborhood aggregates.
Withdrawal hides posts and clears retained district metadata. No private photo,
exact address or verified survival claim is exposed.

| File | Change | Reason |
| --- | --- | --- |
| `services/api/migrations/versions/0009_rewards_community.py` | Add moderator flag, profiles, posts, reports and indexes | Keep the new state additive and owner-bound |
| `services/api/app/rewards.py` | Add calendar-safe milestone, streak and capped-score calculations | Make reward rules deterministic and reviewable |
| `services/api/app/community.py` | Add strict profile, post, report, moderation, leaderboard and neighborhood contracts | Validate all public inputs and outputs at the API boundary |
| `services/api/app/community_repository.py` | Add owner rechecks, moderation, reports, feed, leaderboard and k-anonymous aggregation | Enforce consent, privacy and transaction boundaries server-side |
| `services/api/app/accounts.py`, `services/api/app/account_routes.py` | Hide community data on withdrawal and expose private rewards/community routes | Keep consent withdrawal effective and wire the API surface |
| `apps/mobile/lib/private_api.dart`, `apps/mobile/lib/rewards_community.dart`, `apps/mobile/lib/private_garden.dart` | Add API clients, reward/community models, screen and garden entry point | Make the feature usable in the Android flow |
| `services/api/tests/test_rewards.py`, `services/api/tests/integration/test_rewards_community.py` | Cover reward rules, migration-backed endpoints, moderation, withdrawal and k-anonymity | Verify deterministic behavior and database constraints |
| `apps/mobile/test/rewards_community_test.dart` | Cover bounded Flutter contract parsing | Prevent mobile response-shape regressions |
| `docs/testing/rewards-community.tdd.md`, `README.md`, `AGENTS.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/ACCOUNTS_PASSPORTS.md`, `docs/DATABASE_MIGRATIONS.md`, `docs/SETUP_MAC.md`, `docs/MILESTONE_STATUS.md`, `scripts/check_repo.py` | Document the new scope, safeguards, migration head and handoff files | Keep product, operations and agent guidance aligned |
| `builders.md` | Record this implementation and verification | Preserve the required dated change report |

**Database impact:** Existing passport/care/account rows are preserved. Migration
`0009` adds `grower_account.is_moderator` with a false default and new community
tables; its downgrade is intentionally blocked because it would delete posts,
reports and moderation state.

**Checks:** `sh scripts/check-db.sh` passed all 271 isolated PostgreSQL/API tests
with 98.37% statement coverage. Focused community integration passed 3 tests.
`sh scripts/check-mobile.sh` passed Flutter analysis, 56 tests and the Android
debug APK build. The pure/API reward tests passed 36 targeted tests before the full
DB run. `git diff --check` was run after the final edits.

**Risks / limits:** Care and survival remain self-reported; the score is not a
biological survival measurement. Moderator accounts require operator provisioning
through the database, and there is no moderator UI. District trends stay hidden
below five participating growers. The existing local catalog/care content still
needs agronomic approval before real advice or impact claims.

### 2026-10-06 — Add collaborator requirements

**Outcome:** Added a clone-to-run requirements guide covering the verified Docker,
Python, Flutter, Java, Android SDK, emulator, backend, mobile preview, testing,
privacy, and contribution workflow requirements.

| File | Change | Reason |
| --- | --- | --- |
| `requirements.md` | Add collaborator setup and project rules | Give a new clone owner one reliable starting point |
| `builders.md` | Record the requirements guide | Preserve the required dated change report |

**Database impact:** None.

**Checks:** `git diff --check` passed. Full API/database/mobile checks were run
before this documentation-only addition and remain recorded above.

**Risks / limits:** The guide assumes the checked reference toolchain; Android
SDK paths and emulator IDs vary by machine. A collaborator still needs normal
GitHub access for a private repository.
