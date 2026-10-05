# Safe database changes

## Source of truth and scope

Alembic revisions under `services/api/migrations/versions/` are the schema history.
`db/init/*.sql` are unchanged historical fixtures and are no longer mounted into
PostgreSQL at startup. Schema revisions do not insert demo records.

| Revision | Upgrade | Rollback |
| --- | --- | --- |
| `0001` | Original source/species schema and constraints | Blocked: dropping catalog tables would lose data |
| `0002` | Add `species_source_id_idx` on the FK | Drop only that index; catalog rows remain |
| `0003` | Add source rights/review metadata, scoped profiles, requirements, import audit and filtered view | Blocked: dropping provenance could lose review/import evidence |
| `0004` | Add accounts, hashed sessions, consent receipts, private passports/care and throttle buckets | Blocked: dropping tables would erase private records |
| `0005` | Add reviewed care directives, private plans and immutable versions | Blocked: dropping tables would erase reviewed/private data |
| `0006` | Add owner/version task completions, weather preference and bounded public regional forecast cache | Blocked: dropping tables would erase private records |
| `0007` | Add nullable care retry UUID and partial unique owner/UUID index; existing values unchanged | Blocked: removing retry identities could duplicate synchronized care |
| `0008` | Add separately consented private photo metadata, bytes and assistance | Blocked: dropping tables would erase private photos/consent |
| `0009` | Add rewards inputs and consented community profiles, posts, reports and moderation | Blocked: dropping tables would erase posts/reports/moderation state |

The guarded CLI uses a single transaction per command, including Alembic's version
update. PostgreSQL's advisory transaction lock prevents overlapping migration or
seed commands. Lock waits are bounded to 5 seconds and statements to 60 seconds;
errors roll back the whole command. Review these limits before larger migrations.
No URL/password is stored in Alembic config or printed by the CLI.

Only the `public` schema and PostgreSQL 16 are currently supported. This is a local
development workflow, not a production deployment system. Separate application
and migration roles, backup retention, maintenance windows and recovery objectives
must be designed before shared/production use.

## Before every real schema change

1. Confirm the target database/environment; inspect current revision and row counts.
2. Back up; verify the archive and rehearse restoration into a **new isolated database**.
3. Review constraints, relationships, locks, app compatibility and rollback data loss.
4. Run `sh scripts/check-api.sh` and `sh scripts/check-db.sh` before applying.
5. Apply once, check revision/readiness/data, then deploy compatible app code.
6. Append the exact changes/results to `builders.md`. Never rewrite an applied revision.

## Back up without overwriting an existing file

From the repository root, with the DB running:

```sh
umask 077
mkdir -p backups
groot_backup_file=$(mktemp "$PWD/backups/groot-before-migration.XXXXXX")
docker compose exec -T db sh -c \
  'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' \
  > "$groot_backup_file"
test -s "$groot_backup_file"
docker compose exec -T db pg_restore --list < "$groot_backup_file"
printf '%s\n' "$groot_backup_file"
```

Check command exit codes. If dump fails, the partial file is not a backup. Archive
listing verifies readability, not a complete restore; rehearse as below. Keep backups
private and off the repository; `backups/` is ignored. `pg_dump` is a consistent
logical snapshot of one DB, not a backup of cluster roles or unrelated databases.

## Adopt an existing unversioned starter volume (once)

Do **not** reset the volume, rerun init SQL, or use raw `alembic stamp head`.
The old API may remain running while you back up and build the migration image.

```sh
docker compose up --wait db
docker compose build api
sh scripts/db.sh current             # reports unversioned
# Perform and verify the backup above before continuing.
sh scripts/db.sh baseline --confirm  # validate actual schema, then stamp ONLY 0001
  sh scripts/db.sh upgrade             # apply through 0009; preserve catalog/private rows
sh scripts/db.sh check
docker compose up --build --wait
python3 scripts/smoke_api.py
```

Baseline validates exact columns/types/nullability/defaults, primary/foreign keys,
check definitions and validation flags, indexes, absence of unexpected public
tables/views, custom triggers and row-security flags. It does not compare or rewrite
row values: extra rows, edits, inactive flags, Bangla names and timestamps survive.
It refuses partial schemas, drift and databases already carrying migration history.

If validation refuses: inspect the discrepancy and plan an explicit migration on
a restored copy. Do not weaken the validator or stamp to silence errors. Schema
names/constraint definitions different from this known starter require review.

## Fresh database and normal upgrades

```sh
docker compose up --build --wait  # DB healthy → migrate upgrade → API starts
sh scripts/db.sh check
sh scripts/db.sh seed-demo       # optional LOCAL demo records; never overwrites rows
python3 scripts/smoke_api.py      # expects a non-empty demo catalog
```

For an existing versioned database, back up then use `sh scripts/db.sh upgrade`.
`current` reports the version; `check` exits nonzero if it differs from the single
migration head. Repeated upgrades at head are no-ops. API readiness is 503 for an
unversioned/pending/missing schema. Liveness can remain 200 during maintenance.
The preview helper seeds explicitly because it is a demo workflow. Do not run demo
seeding against an advice/production catalog. A reviewed source collision is refused.

## Rollback and recovery

Prefer a reviewed forward fix. Stop incompatible application traffic and take a
backup before an approved schema rollback. The following index-only rollback
applies **only to a database still at `0002`**, not after `0003`:

```sh
# Only after backup, review and explicit operator approval:
sh scripts/db.sh downgrade 0001 --confirm
sh scripts/db.sh current
# Current app readiness will be 503 until you restore the required head:
sh scripts/db.sh upgrade
sh scripts/db.sh check
docker compose up --wait
```

`0002 → 0001` removes only the added index. `0003` rollback is always blocked to
retain provenance; `0004`, `0005` and `0006` rollback is blocked to retain private records.
`0007`, `0008` and `0009` rollback is blocked to preserve care deduplication,
private photo, consent and community records. Do not
bypass these guards with a stamp. `downgrade base` is blocked; even
from an older head, earlier steps roll back if the baseline guard raises. Failed migrations leave
the previous version/schema/rows intact. Never use a stamp to pretend rollback ran.

For backup recovery, create a **new**, uniquely named restoration database with
`createdb` on an isolated PostgreSQL server, then restore (adjust user/target to that
server; never point this at the current database):

```sh
pg_restore --no-owner --no-privileges --exit-on-error \
  --dbname="$GROOT_RESTORE_DATABASE_URL" "$groot_backup_file"
```

Do not use `--clean`, drop/recreate the current DB, or remove its Docker volume.
Inspect restored row counts, Bangla text, source references, timestamps and revision.
An unversioned historical backup must pass baseline adoption there before upgrade.
Only switch the app's `DATABASE_URL` after migration/health checks and explicit
approval; preserve the old DB until recovery is verified. Restoration to a new DB
also avoids silently overwriting rows written after the backup.

## Add the next revision

```sh
# In services/api with the dev dependencies installed:
alembic -c alembic.ini revision --rev-id 0010 -m "describe the change"
```

The template deliberately raises until both directions have been reviewed.
Fill in `down_revision` correctly. Do not add a second head, edit old revisions,
autogenerate without models/review, or run raw Alembic upgrade/downgrade/stamp:
`env.py` requires the guarded CLI's transaction/connection. Offline SQL rendering is
not implemented. Add tests for existing rows, failure/rollback, constraints and API
compatibility, then use `scripts/db.sh` for execution. For additive changes prefer
expand/backfill/contract across deployments, not immediate column drops/renames.
This runner intentionally does not support autocommit/concurrent-index operations;
design a separate reviewed procedure if larger indexes require that strategy.

## Local and CI checks

```sh
sh scripts/check-api.sh  # unit/config/error checks, no database/network at runtime
sh scripts/check-db.sh   # same command used by GitHub CI, with coverage >=90%
```

The DB suite uses a standalone `compose.test.yaml`, ignores development `.env`,
publishes no ports, uses tmpfs instead of the development volume, and allocates a
unique Docker project each time. Each fixture creates a random `groot_test_*` DB
and drops only that owned DB. Cleanup removes only the temporary project's
containers/network/image. Missing test configuration fails rather than skipping.
Unit-only host command: `python -m pytest -m 'not integration'` from `services/api`.
Install with `python -m pip install -c constraints.txt -e '.[dev]'` there to use the
verified dependency snapshot. Python/PostgreSQL container image digests are pinned
for matching local/CI behavior; update the constraints and digests deliberately,
review release/security notes, and rerun both suites. Build-tool bootstrap packages
and package artifact hashes are not yet locked; this is not a hermetic supply-chain build.

Coverage includes migrations and DB code: fresh installs, repeated upgrades,
legacy user rows/edits, drift rejection, additive downgrade/re-upgrade, blocked
destructive downgrade, transaction rollback after DDL/data failure, concurrent
runner rejection, actual database constraints, UTF-8 API results, sorting/limits,
empty catalog and migration-aware readiness. The development stack smoke job also
checks migration-before-API ordering and explicit demo seed on a fresh database.

References: [Alembic migration environment](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
and [PostgreSQL transaction/advisory locks](https://www.postgresql.org/docs/16/explicit-locking.html).

Catalog data imports are separate from schema migrations and never automatic.
Use the backup/review and explicit validation/apply flow in
[catalog import procedures](CATALOG_IMPORT.md). Source rights default to pending
for legacy rows; no demo or previously untracked source is silently approved.

## Verified starter adoption — 2026-10-03

The existing local catalog was backed up, restored on an isolated PostgreSQL 16
server, validated at baseline `0001`, then upgraded to `0002`. Full catalog row
snapshots (including Bangla names and timestamps) matched before/after adoption
and in the restored backup. The live API readiness and catalog smoke check pass.

Local checks: 10 unit tests; 41 total tests in the PostgreSQL suite; 99.11%
statement coverage. A separate fresh Compose stack verified migration-before-API
startup, an initially empty catalog, and explicit demo seeding. Only disposable
test resources were removed. GitHub-hosted CI was configured but not run remotely.
See `builders.md` for the exact backup location and file-level change report.
