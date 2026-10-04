# Groot: complete Mac setup and Android preview guide

Use this guide when cloning Groot onto a friend's Mac for the first time. The
preview is an Android phone emulator on the Mac, not a website or native macOS
app. VS Code is the editor; Android tooling supplies the virtual phone; Docker
runs the API and database. No AI API key is needed for the current demo catalog.

For a first-time setup, follow [Setup on a fresh Mac](#setup-on-a-fresh-mac) in order.
After that, use [Daily preview](#daily-preview).

## Reopen Android Studio or launch without it

If installed, press `⌘ Space`, search **Android Studio**, and press Return. You can
also open Finder → Applications → Android Studio, or use:

```sh
open -a "Android Studio"
```

If its window was closed but its Dock icon remains, click that icon. Use Window
to select an existing window, or File → Open to open `apps/mobile/android` inside
your Groot checkout if you need a project window. No new Android project is needed.

On the welcome screen choose **More Actions → Virtual Device Manager**. With a
project open, use **View → Tool Windows → Device Manager** (some versions also
provide **Tools → Device Manager**). Click the launch/play button beside
`Groot_API_36` and wait for the Android home screen. See the
[official Device Manager guide](https://developer.android.com/studio/run/managing-avds).

If Spotlight finds nothing or `open` cannot find the app, it may not be installed.
This Mac's earlier setup used command-line Android tools; Studio was not found
in either standard Applications folder when this guide was updated. You can
start the already-created emulator without Studio from the repository root:

```sh
sh scripts/start-emulator.sh
```

Leave that terminal running and use a second terminal for the preview. Do not
launch a second copy of the same virtual device if it is already running.

## Reference toolchain

- Flutter **3.47.5**, Dart **3.13.4**: runner-generation, prior Android verification
  and CI reference. Use this version for a matching fresh-machine baseline; do not
  replace or upgrade an existing SDK without reviewing the change.
- Java **21** for Flutter's Android build tools. The app's compilation target is
  separately set to Java/Kotlin 17.
- Android API 36, build-tools 36.0.0, platform-tools, emulator, NDK
  28.2.13676358, CMake 3.22.1, and a Google APIs ARM64 API 36 system image.
- Docker Desktop with Compose supporting named build contexts (Compose 2.17+).
- Python 3 for the standard-library smoke script; API Python 3.12 and PostgreSQL
  16 run in Docker, so host PostgreSQL and host API packages are unnecessary.

Fresh setup examples use your own `$HOME`, not Ashraf's account. Ashraf's checkout
is `/Users/ashraf/Desktop/Project-Groot`, with a preserved ignored SDK in `flutter/`
and Android SDK at `/Users/ashraf/Library/Android/sdk`. Cached SDK metadata now
reports Flutter **3.47.6 / Dart 3.13.5**. The 2026-10-04 milestone audit rebuilt
the Android APK and reran both live emulator flows with that existing SDK; no
upgrade/replacement was performed. CI retains its previously verified 3.47.5
reference. This is not a second-Mac or remote-CI verification.

Flutter's Android SDK/JDK selections are user-level settings and can affect other
Flutter projects. Xcode/CocoaPods warnings for iOS/macOS targets are not blockers
for Android preview; Xcode command-line tools are still needed for Git/utilities.

## Daily preview

Open Docker Desktop and the repository in VS Code. Recommended extensions are in
`.vscode/extensions.json`; Flutter also installs Dart support. The workspace SDK
setting points to this checkout's existing `flutter/`. On another machine without
that folder, change/remove `dart.flutterSdkPath` and use an installed Flutter SDK.

Start each terminal below in the repository root: `cd "$HOME/Developer/Project-Groot"`
if you used this guide's clone location, or your actual location otherwise.
Skip Terminal 1 if the emulator is already booted.

Terminal 1, repository root:

```sh
sh scripts/start-emulator.sh
```

Terminal 2, repository root:

```sh
./scripts/flutterw devices
sh scripts/preview-android.sh emulator-5554
```

Use the Android device ID shown by `devices` if it differs. Once Flutter connects,
press `r` for hot reload, `R` for hot restart, `d` to detach while leaving the app
running, or `q` to stop the debugging session. For the VS Code F5 alternative,
see the dedicated section below; the launch configuration does not start Docker.

Expected screen: Groot title, Bangla heading, a setup-only disclaimer, Neem and
Okra with Bangla names and Demo chips. This is a catalog demo, not AI plant advice.

## Setup on a fresh Mac

### 1. Check the Mac and install Git tools

Use Apple menu → About This Mac to identify Apple Silicon or Intel. In Terminal:

```sh
uname -m
git --version
xcode-select -p
```

`arm64` normally means Apple Silicon; `x86_64` means Intel (or a translated shell
on Apple Silicon—prefer a native terminal). Use installers for the actual chip.
If Git/command-line tools are missing, run `xcode-select --install`, finish the
dialog, and reopen Terminal. Full Xcode is not required for Android preview.
See [Flutter's Mac prerequisites](https://docs.flutter.dev/install/manual).

Allow ample disk space for SDKs, Docker images and a virtual phone. Consult the
current [Android Studio requirements](https://developer.android.com/studio/install)
and Docker's supported macOS versions before setting up an older Mac.

### 2. Install desktop tools

- [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/):
  choose Apple Silicon or Intel, install into Applications, launch and finish its
  prompts. Wait for the engine to be running.
- [Visual Studio Code](https://code.visualstudio.com/docs/setup/mac): install and
  launch. Optional terminal shortcut: `⌘ Shift P` → **Shell Command: Install
  'code' command in PATH**, then reopen Terminal.
- [Android Studio](https://developer.android.com/studio/install): use the correct
  Mac download, drag it into Applications, launch and complete its setup wizard.
  Recommended for a friend's first setup, though command-line Android tools can
  also run Groot without the Studio app.
- Java 21 JDK: reuse an existing installation or install a macOS JDK such as
  [Eclipse Temurin](https://adoptium.net/installation/macOS). Select **JDK 21**,
  not only a JRE, and the correct architecture. Only use Studio's bundled JDK if
  you have checked its version; it may differ from the reference Java 21.

Check:

```sh
docker version
docker compose version
/usr/libexec/java_home -v 21
python3 --version
```

`docker version` should show client and server. If Python 3 is unavailable,
install it from [Python's official Mac downloads](https://www.python.org/downloads/macos/)
and reopen Terminal. This Docker workflow needs no host API packages, PostgreSQL,
Node.js or Homebrew.

### 3. Clone the complete repository

**Maintainer prerequisite:** commit and push the intended setup files before
sharing the clone instructions. The 2026-10-04 audit staged the reviewed project
files, including the runner, scripts, migrations and account flow. They are still
**uncommitted and unpublished**; staging is not a GitHub upload. Your friend cannot
get them until you review, commit and push. The audit did not commit or push.
Keep `.env` variants, SDKs, backups and build caches out of Git.

Once the complete starter is published, your friend can run:

```sh
mkdir -p "$HOME/Developer"
cd "$HOME/Developer"
git clone https://github.com/ASHFOX474/Project-Groot.git
cd Project-Groot
git status --short
git submodule status
python3 -B scripts/check_repo.py
```

For a private repository, get collaborator access and use normal GitHub
authentication. Do not place access tokens in clone URLs or screenshots. If the
destination already exists, use that checkout or a new directory; do not delete it.

Confirm these files are included:

```sh
ls scripts/flutterw scripts/preview-android.sh scripts/start-emulator.sh
ls compose.yaml services/api/alembic.ini
ls apps/mobile/android/settings.gradle.kts
ls apps/mobile/android/gradle/wrapper/gradle-wrapper.jar
```

If missing, ask the maintainer to publish them. Do not use `flutter create` over
the app to repair an incomplete clone. Flutter is ignored, not a submodule; install
the SDK separately next. These scripts are intended to retain executable file
modes in Git, particularly `scripts/flutterw` and the Android Gradle wrapper.

### 4. Install the reference Flutter SDK separately

Download **Flutter 3.47.5 stable for macOS** from the
[official SDK archive](https://docs.flutter.dev/install/archive): ARM64 for Apple
Silicon, x64 for Intel. Extract into a user-owned location such as
`$HOME/development/flutter`. Do not overwrite an existing SDK; choose a new
location if necessary. Flutter includes Dart.

For that example location, run from the repository root:

```sh
export PATH="$HOME/development/flutter/bin:$PATH"
flutter --version
./scripts/flutterw --version
```

Both should report the intended SDK. The export applies only to this terminal.
For future sessions, add that PATH line once to your existing `~/.zprofile` using
an editor, preserving all other contents. Reopen Terminal and VS Code. See the
[manual Flutter install guide](https://docs.flutter.dev/install/manual).

The wrapper checks, in order: `GROOT_FLUTTER_BIN` if set, executable
`flutter/bin/flutter` in the repo, then Flutter on PATH. To select a particular
existing SDK without moving it:

```sh
export GROOT_FLUTTER_BIN="$HOME/development/flutter/bin/flutter"
./scripts/flutterw --version
```

Use your actual path. This override controls wrapper scripts in that terminal,
not the VS Code Flutter extension. Do not run `flutter upgrade` or add an SDK as
a Git submodule during ordinary setup.

### 5. Install/select Android components and Java

Open Studio → welcome screen **More Actions → SDK Manager**, or with a project
open **Tools → SDK Manager**. Note Android SDK Location; usually
`$HOME/Library/Android/sdk` on macOS, but use the displayed path if different.

Install Android API 36. Under SDK Tools, enable **Show Package Details** and select
the reference components: build-tools **36.0.0**, platform-tools, emulator,
command-line tools (latest), NDK **28.2.13676358**, CMake **3.22.1**. Apply and finish
downloads. Exact versions here come from the previously verified Groot toolchain;
[Flutter's Android setup guide](https://docs.flutter.dev/platform-integration/android/setup)
explains the SDK Manager and license steps.

From the repository root:

```sh
./scripts/flutterw config --jdk-dir="$(/usr/libexec/java_home -v 21)"
./scripts/flutterw config --android-sdk="$HOME/Library/Android/sdk"
./scripts/flutterw doctor --android-licenses
./scripts/flutterw doctor -v
```

Read and accept licenses if you agree. Fix Android-toolchain errors before
continuing. If `java_home -v 21` fails, finish installing/registering Java 21 or
select an explicit existing JDK path. Do not replace system Java.

For a nondefault SDK path, also set `ANDROID_HOME` to that path in each terminal
running `start-emulator.sh`, or add its export once to your existing shell profile.
Keep `ANDROID_HOME` and `ANDROID_SDK_ROOT` consistent if both are set.

### 6. Create the virtual phone once

Open Device Manager as described above. Choose **Create Device** (or **+**), select
a phone such as Pixel 7 and a **Google APIs Android API 36** image. Download it if
necessary: ARM64/`arm64-v8a` for Apple Silicon or x86_64 for Intel. Name the device
**Groot_API_36**, finish, click its launch button, and wait for Android's home screen.

If it already exists, launch it instead of replacing it. The steps follow
[Android's AVD documentation](https://developer.android.com/studio/run/managing-avds).
An AVD is local machine state, not something Git clones.

After initial creation you can launch it in a separate terminal:

```sh
cd "$HOME/Developer/Project-Groot"
sh scripts/start-emulator.sh
```

Leave that terminal running. For another name, use
`sh scripts/start-emulator.sh My_AVD_Name`. List installed AVDs without changing them:

```sh
"$HOME/Library/Android/sdk/emulator/emulator" -list-avds
```

### 7. Open the clone in VS Code

Use File → Open Folder → `Project-Groot`, or `code .` at the repo root. Open the
whole repository, not just `apps/mobile`, so launch paths resolve. Install the
recommended **Flutter** extension (`Dart-Code.flutter`) and **Python** extension
(`ms-python.python`). Flutter includes Dart support. Python is useful for editing
the backend, but the container runs the API without host packages.

**Fresh clone SDK setting:** `.vscode/settings.json` points `dart.flutterSdkPath`
at `flutter` in the repo, which will not exist in your friend's clone. In VS Code
Settings → **Workspace**, search `dart.flutterSdkPath` and select the actual
absolute SDK folder, for example `/Users/YOUR_USERNAME/development/flutter`
(not `bin/flutter`). Alternatively remove the workspace override to allow SDK
discovery from PATH. Do not enter `$HOME` as a literal JSON path. Reload VS Code.
Do not commit a friend's machine-specific absolute path.

### 8. Configure and verify the demo backend

In a new VS Code terminal at the repository root:

```sh
test -f .env || cp .env.example .env
docker compose config --quiet
docker compose up --build --wait
sh scripts/db.sh check
sh scripts/db.sh seed-demo
python3 scripts/smoke_api.py
```

Keep Docker Desktop running. First startup builds/downloads images, initializes
the private PostgreSQL volume and migrates before starting the API. `check`
should report `0005`; seed inserts the two demo entries without overwriting rows.
The smoke script should report PASS. No init SQL needs to be manually executed.

Visit `http://127.0.0.1:8000/docs` for the backend API docs, not the mobile preview.
`http://127.0.0.1:8000/health/ready` should return `{"status":"ready"}`; the catalog
endpoint is `http://127.0.0.1:8000/v1/catalog/species`.

`.env.example` contains development defaults, not production secrets. Keep `.env`
private and ignored. If changing credentials, keep `POSTGRES_*` and `DATABASE_URL`
consistent; editing them does not change passwords in an already-created volume.
An existing unversioned volume needs the
[backup/baseline procedure](DATABASE_MIGRATIONS.md), never a reset.

### 9. Launch the mobile preview

With the virtual phone booted, from the repository root:

```sh
./scripts/flutterw devices
sh scripts/preview-android.sh emulator-5554
```

Replace `emulator-5554` with the Android device ID printed by `devices` if different.
Do not pass the AVD name `Groot_API_36` as a device ID: the name starts a virtual
phone; the ID selects a booted phone for Flutter. The helper checks the backend,
seeds local demo data, resolves packages, builds/installs the app and attaches
Flutter. Keep that terminal open.

Expect Groot's title, Bangla text, Neem/নিম, Okra/ঢেঁড়স, two Demo chips and a
setup-only disclaimer. First build needs internet for Gradle/Android/Flutter
downloads and can take several minutes. This verifies phone → API → PostgreSQL;
AI and generated care quests are not implemented yet. Tap the top-right account
icon for local accounts, optional consent choices, private Plant Passports and
manual care history. Use test credentials only over this debug HTTP connection;
see [accounts/privacy guide](ACCOUNTS_PASSPORTS.md). Optional research imports can
add catalog names beyond the two demos; that is not planting approval.

After signing in, tap **লক্ষ্য ও উপযুক্ত গাছ · Plan a goal**. It starts in Bangla;
English is selectable. Enter a goal, known space/sun/soil details and optionally
only a district (no GPS permission). The live catalog has no approved profiles,
so the correct result explains missing data instead of recommending demo plants.
Voice requires an Android speech provider; the button explains provider privacy
before use, and unavailable voice leaves typing intact. Goals are not saved.
See [goal matching and voice setup limits](GOALS_RECOMMENDATIONS.md).

Care previews are available from reviewed matches. **Saved care plans** opens
private versions and revisions. Explicit saving stores structured conditions and
chosen location, not free goal/soil prose. No approved care guidance is bundled,
so demo/draft catalog rows correctly provide no care advice. See
[care preview, saving and content review](CARE_PLANS.md). Existing database users
must back up/rehearse restore before upgrading to0005; never reset the volume.

## Preview with VS Code F5 instead

After first-time setup, launch the existing emulator and run from the root:

```sh
docker compose up --build --wait
sh scripts/db.sh seed-demo
python3 scripts/smoke_api.py
```

Select the Android device in VS Code's device selector/status bar. Open Run and
Debug, choose **Groot · Android demo**, and press F5 (Fn+F5 if macOS assigns a system
function to the key). The launch configuration sets the mobile working directory
and `API_BASE_URL=http://10.0.2.2:8000`; it does not start Docker or create the AVD.
Stop an existing terminal `flutter run` session before starting another debugger
for the same app.

## Stop and reopen safely

- Stop Flutter with `q` in its run terminal or VS Code's Stop button; `d` detaches
  a terminal session and leaves the app running.
- Stop the emulator in Device Manager or close its window. Stop its terminal
  process if you launched it from a terminal and are finished.
- Run `docker compose down` from this repository's root to stop its backend. The
  database volume survives. Do not use `down -v` or global Docker prune.
- Next time open Docker, start the existing AVD and run the daily preview helper.
  No reinstall, AVD replacement or Android runner regeneration is needed.

## Checks and troubleshooting

```sh
python3 -B -m unittest discover -s scripts/tests -v
python3 -B scripts/check_repo.py
sh scripts/check-api.sh
sh scripts/check-db.sh
sh scripts/check-mobile.sh
docker compose up --build --wait
sh scripts/db.sh seed-demo
python3 scripts/smoke_api.py
cd apps/mobile
../../scripts/flutterw test integration_test/catalog_smoke_test.dart \
  -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

- **Catalog error:** inspect `docker compose ps`, `docker compose logs api`, and
  `curl -f http://127.0.0.1:8000/health/ready`. Readiness now also requires completed
  database migrations; see [database procedures](DATABASE_MIGRATIONS.md).
  The emulator uses `10.0.2.2`, not
  `localhost`. Debug HTTP permission is retained; never enable it for release.
- **Flutter not found or wrong SDK in VS Code:** check `command -v flutter`,
  `./scripts/flutterw --version`, and the workspace `dart.flutterSdkPath`. A fresh
  clone has no ignored `flutter/` folder; set the extension to your external SDK.
  Wrapper overrides are terminal-local and do not set the extension's SDK.
- **Permission denied for a wrapper:** check `ls -l scripts/flutterw
  apps/mobile/android/gradlew`. If the intended executable modes were lost,
  restore only those known scripts with `chmod +x scripts/flutterw
  apps/mobile/android/gradlew`; the maintainer should retain those modes in Git.
- **Cannot connect to Docker daemon:** open Docker Desktop and wait for its engine;
  `docker version` must show a server. Installing only a Docker CLI is not enough.
- **Port 8000 busy:** identify the owner before changing anything. Do not stop an
  unrelated service. Adjust Compose's API host port and `API_BASE_URL` together.
- **No Android device:** wait for boot, check `flutterw devices`, or list AVDs with
  `~/Library/Android/sdk/emulator/emulator -list-avds`. A desktop or Chrome device
  does not verify the Android app.
- **Java/Gradle error:** use Java 21, not the Mac's default Java 25. This runner was
  generated with Flutter 3.47.5 (AGP 9.1.0 / Gradle 9.3.1).
- **First build slow:** Android/Gradle/Flutter artifacts download on first use.
  Keep network access available and allow several minutes.
- **No seed rows:** run `sh scripts/db.sh seed-demo` explicitly after migrations.
  Existing rows are not overwritten. Historical init SQL no longer runs at startup.
  An old unversioned volume needs backed-up, validated baseline adoption; never
  delete the volume to make a check pass.
- **Extra catalog names / empty candidates:** an optional research import can add
  draft catalog names alongside the two Demo rows. These are not approved planting
  advice. `/v1/catalog/recommendation-candidates` intentionally stays empty while
  profiles/rights need review; do not promote flags just to populate the response.
  See [catalog procedures](CATALOG_IMPORT.md).
- **Database access:** use `docker compose exec db psql -U groot_dev -d groot`
  (adjust names if configured); no host database port is needed.
- **Stop services safely:** `docker compose down` preserves the named volume.
  Never run `down -v` or prune unrelated Docker resources for this project.

## Git tracking repair

The original commit tracked `flutter/` as a gitlink without `.gitmodules`, which
broke submodule commands and did not provide a working SDK in a fresh clone. Only
that index entry was removed; the local SDK files and its own Git checkout remain.
The generated plugin registrant was also removed from the index, not from disk.
Both are now ignored. These index removals are staged; other changes remain for
review. The milestone audit additionally staged the intended source/config/docs
and preserved executable wrapper modes. No commit or push was made.

```sh
git submodule status          # should no longer error
git check-ignore flutter/bin/flutter
git status --short
git diff --cached --stat
python3 -B scripts/check_repo.py
```

Keep runner resources, MainActivity, Gradle build files, wrapper scripts/JAR,
`.metadata`, and `pubspec.lock` under version control. Ignore `local.properties`,
SDKs, caches, signing credentials and build outputs.

The read-only handoff check fails if required project files are missing/untracked,
wrapper executable modes are lost, merge conflicts remain, or SDK/private/generated
paths are tracked. It checks the Git **index**, not whether changes were pushed,
and does not scan credential values/history. Review any reported path; never use
`git add -f` to silence the SDK/private-data guard. CI runs this gate and its tests.

## Earlier runtime verification on 2026-10-03

- Native Flutter doctor passes Flutter and the Android toolchain. Only unrelated
  Xcode/iOS/macOS configuration warnings remain.
- Docker API/database healthy; live catalog check returns both seeded demo rows.
- Initial API unit tests: 3 passed. The later migration task verified 10 unit tests
  and 41 total real-DB suite tests at 99.11% coverage; see `builders.md`.
  Flutter analysis: no issues. Widget test: 1 passed.
- Android ARM64 debug APK builds with label Groot and compile/target SDK 36.
- API-backed emulator integration test: 1 passed on `emulator-5554`.
- Normal preview launched and visually checked for Bangla text, both species,
  Demo labels and setup-only disclaimer. Flutter detached; preview/services left running.
- Existing Flutter SDK revision retained. Build tools created only their normal
  caches (including an untracked `.kotlin/` cache under the SDK's Gradle tooling).
- Git submodule check succeeds. No commit/push made; GitHub-hosted jobs not run.

The first build was run natively after the Codex sandbox denied macOS file watching
and Kotlin daemon discovery stalled. If an AI session hits the same restriction,
grant narrowly scoped tool-cache/native runtime access or run the same documented
command in your Mac terminal; do not modify app code or replace the Flutter SDK.

The friend-onboarding guide was reviewed against repository scripts and official
installation documentation. A second Mac/Intel setup was not executed. For the
latest local results and approval blockers, see [milestone status](MILESTONE_STATUS.md)
and `builders.md`; the earlier verification section above is historical evidence.
