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
