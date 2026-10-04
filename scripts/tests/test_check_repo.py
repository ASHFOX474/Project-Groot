"""Repository handoff checks use temporary files, never the user's Git index."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "check_repo", Path(__file__).resolve().parents[1] / "check_repo.py"
)
check_repo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_repo)


class RepositoryChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.entries = {}
        for name in check_repo.REQUIRED:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
            self.entries[name] = "100755" if name in check_repo.EXECUTABLE else "100644"

    def test_complete_index_passes(self):
        self.assertEqual(check_repo.audit(self.root, self.entries, []), [])

    def test_missing_runner_and_untracked_file_fail(self):
        name = "apps/mobile/android/settings.gradle.kts"
        del self.entries[name]
        errors = check_repo.audit(self.root, self.entries, [name])
        self.assertTrue(any("Required file not tracked: " + name == x for x in errors))
        self.assertTrue(any("Untracked project file: " + name == x for x in errors))

    def test_tracked_but_missing_file_fails(self):
        name = "compose.test.yaml"
        (self.root / name).unlink()
        self.assertIn("Required file missing from disk: " + name,
                      check_repo.audit(self.root, self.entries, []))

    def test_sdk_gitlink_and_generated_private_files_fail(self):
        forbidden = ["flutter", "flutter/bin/flutter", ".env", ".env.production",
                     "backups/private.dump", "photos/private.jpg",
                     "apps/mobile/build/app.apk", "services/api/.venv/bin/python",
                     "apps/mobile/android/local.properties",
                     "apps/mobile/android/key.properties", "signing/private.jks",
                     "apps/mobile/android/app/src/main/java/GeneratedPluginRegistrant.java"]
        for name in forbidden:
            with self.subTest(name=name):
                entries = {**self.entries, name: "160000" if name == "flutter" else "100644"}
                self.assertIn("Forbidden tracked path: " + name,
                              check_repo.audit(self.root, entries, []))

    def test_dev_defaults_and_gradle_wrapper_are_allowed(self):
        entries = {**self.entries, ".env.example": "100644"}
        self.assertEqual(check_repo.audit(self.root, entries, []), [])

    def test_executable_mode_is_required_for_clone(self):
        self.entries["scripts/flutterw"] = "100644"
        self.assertIn("Executable Git mode required: scripts/flutterw",
                      check_repo.audit(self.root, self.entries, []))

    def test_unrelated_untracked_file_is_not_staged_or_rejected(self):
        self.assertEqual(check_repo.audit(self.root, self.entries, ["personal-notes.txt"]), [])


if __name__ == "__main__":
    unittest.main()
