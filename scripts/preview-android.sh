#!/bin/sh
# Start local services and attach Flutter to an already booted Android emulator.
set -eu
groot_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$groot_root"
docker compose up --build --wait
sh scripts/db.sh seed-demo
python3 scripts/smoke_api.py
cd apps/mobile
"$groot_root/scripts/flutterw" pub get
# Pass a device ID (for example emulator-5554) if more than one device is available.
if [ "$#" -gt 0 ]; then
  exec "$groot_root/scripts/flutterw" run -d "$1" \
    --dart-define=API_BASE_URL=http://10.0.2.2:8000
fi
exec "$groot_root/scripts/flutterw" run \
  --dart-define=API_BASE_URL=http://10.0.2.2:8000
