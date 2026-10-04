#!/bin/sh
set -eu
groot_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$groot_root/apps/mobile"
"$groot_root/scripts/flutterw" pub get
"$groot_root/scripts/flutterw" analyze
"$groot_root/scripts/flutterw" test
"$groot_root/scripts/flutterw" build apk --debug --target-platform android-arm64 \
  --dart-define=API_BASE_URL=http://10.0.2.2:8000
