"""Read-only Git handoff gate: source must be tracked; local/private data must not.

This checks filenames and index modes, not file contents or credential history.
It never stages, commits, deletes files, or installs/changes a Flutter SDK.
"""
from pathlib import Path, PurePosixPath
import subprocess
import sys


REQUIRED = (
    ".gitignore", ".gitattributes", ".env.example", ".github/workflows/checks.yml",
    "AGENTS.md", "README.md", "builders.md", "compose.yaml", "compose.test.yaml",
    "apps/mobile/.metadata", "apps/mobile/pubspec.yaml", "apps/mobile/pubspec.lock",
    "apps/mobile/lib/main.dart", "apps/mobile/lib/catalog.dart",
    "apps/mobile/lib/private_api.dart", "apps/mobile/lib/private_garden.dart",
    "apps/mobile/lib/goal_models.dart", "apps/mobile/lib/goal_intake.dart",
    "apps/mobile/lib/goal_voice.dart", "apps/mobile/test/goal_intake_test.dart",
    "apps/mobile/android/.gitignore", "apps/mobile/android/settings.gradle.kts",
    "apps/mobile/android/build.gradle.kts", "apps/mobile/android/gradle.properties",
    "apps/mobile/android/app/build.gradle.kts",
    "apps/mobile/android/app/src/main/AndroidManifest.xml",
    "apps/mobile/android/app/src/debug/AndroidManifest.xml",
    "apps/mobile/android/app/src/profile/AndroidManifest.xml",
    "apps/mobile/android/app/src/main/kotlin/bd/groot/groot_app/MainActivity.kt",
    "apps/mobile/android/gradlew", "apps/mobile/android/gradlew.bat",
    "apps/mobile/android/gradle/wrapper/gradle-wrapper.jar",
    "apps/mobile/android/gradle/wrapper/gradle-wrapper.properties",
    "apps/mobile/integration_test/catalog_smoke_test.dart",
    "apps/mobile/integration_test/account_passport_smoke_test.dart",
    "services/api/Dockerfile", "services/api/pyproject.toml",
    "services/api/constraints.txt", "services/api/alembic.ini",
    "services/api/app/main.py", "services/api/app/accounts.py",
    "services/api/app/account_routes.py", "services/api/app/privacy_middleware.py",
    "services/api/app/goal_models.py", "services/api/app/recommendations.py",
    "services/api/tests/test_recommendations.py",
    "services/api/tests/integration/test_goal_recommendations.py",
    "services/api/tests/fixtures/goal_contract.json", "docs/GOALS_RECOMMENDATIONS.md",
    "apps/mobile/lib/care_models.dart", "apps/mobile/lib/care_plan_view.dart",
    "apps/mobile/lib/saved_care_plans.dart", "apps/mobile/test/care_plans_test.dart",
    "services/api/app/care_models.py", "services/api/app/care_plans.py",
    "services/api/app/care_repository.py", "services/api/tests/test_care_plans.py",
    "services/api/tests/integration/test_care_plans.py",
    "services/api/tests/fixtures/care_contract.json", "docs/CARE_PLANS.md",
    "services/api/app/migrations.py", "services/api/app/catalog_bundle.py",
    "services/api/app/catalog_import.py", "services/api/migrations/env.py",
    "services/api/migrations/script.py.mako",
    "services/api/migrations/versions/0001_catalog_baseline.py",
    "services/api/migrations/versions/0002_species_source_index.py",
    "services/api/migrations/versions/0003_reviewed_catalog.py",
    "services/api/migrations/versions/0004_accounts_passports.py",
    "services/api/migrations/versions/0005_grounded_care_plans.py",
    "services/api/catalog/bangladesh-starter-v1.json",
    "services/api/catalog/treegoer-access-evidence.json",
    "services/api/tests/integration/conftest.py",
    "services/api/tests/integration/test_database.py",
    "services/api/tests/integration/test_reviewed_catalog.py",
    "services/api/tests/integration/test_accounts_passports.py",
    "scripts/flutterw", "scripts/start-emulator.sh", "scripts/preview-android.sh",
    "scripts/check-api.sh", "scripts/check-db.sh", "scripts/check-mobile.sh",
    "scripts/db.sh", "scripts/import-catalog.sh", "scripts/smoke_api.py",
    "scripts/check_repo.py", "scripts/tests/test_check_repo.py",
    "docs/SETUP_MAC.md", "docs/DATABASE_MIGRATIONS.md",
    "docs/CATALOG_SOURCES.md", "docs/CATALOG_IMPORT.md",
    "docs/ACCOUNTS_PASSPORTS.md", "docs/MILESTONE_STATUS.md",
)
EXECUTABLE = {"scripts/flutterw", "apps/mobile/android/gradlew"}
PROJECT_PREFIXES = ("apps/mobile/", "services/api/", "db/init/", "docs/", "scripts/",
                    ".github/", ".vscode/")


def forbidden(name):
    path = PurePosixPath(name)
    return (
        path.parts[0] in {"flutter", "backups", "photos"}
        or any(part in {".dart_tool", ".gradle", ".venv", "__pycache__", ".pytest_cache"}
               for part in path.parts)
        or name.startswith("apps/mobile/build/")
        or (path.name.startswith(".env") and path.name != ".env.example")
        or path.name in {"local.properties", "key.properties", "GeneratedPluginRegistrant.java"}
        or path.suffix in {".jks", ".keystore", ".p12"}
    )


def audit(root, entries, untracked):
    errors = []
    for name in REQUIRED:
        if name not in entries:
            errors.append("Required file not tracked: " + name)
        elif entries[name] not in {"100644", "100755"}:
            errors.append("Required file must be a regular tracked file: " + name)
        if not (root / name).is_file():
            errors.append("Required file missing from disk: " + name)
    for name, mode in entries.items():
        if forbidden(name):
            errors.append("Forbidden tracked path: " + name)
        if name in EXECUTABLE and mode != "100755":
            errors.append("Executable Git mode required: " + name)
    for name in untracked:
        if name in REQUIRED or name.startswith(PROJECT_PREFIXES):
            errors.append("Untracked project file: " + name)
    return errors


def main():
    root = Path(__file__).resolve().parents[1]
    try:
        raw = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=root)
        entries = {}
        for item in raw.decode("utf-8").split("\0"):
            if not item:
                continue
            metadata, name = item.split("\t", 1)
            mode, _, stage = metadata.split()
            if stage != "0":
                print("FAIL: unresolved Git merge entry", file=sys.stderr)
                return 1
            entries[name] = mode
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root
        ).decode("utf-8").split("\0")
    except (OSError, subprocess.CalledProcessError, UnicodeError, ValueError):
        print("FAIL: cannot inspect the repository Git index", file=sys.stderr)
        return 1
    errors = audit(root, entries, untracked)
    for error in errors:
        print("FAIL: " + error, file=sys.stderr)
    if errors:
        print("Review/stage intended source files; never force-add SDKs or private data.",
              file=sys.stderr)
        return 1
    print("PASS: required project files tracked; SDK/private/generated paths excluded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
