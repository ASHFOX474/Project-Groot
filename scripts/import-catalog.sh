#!/bin/sh
# Offline validation by default; uses the versioned file bundled in the API image.
set -eu
groot_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$groot_root"
exec docker compose run --rm -T --no-deps api python -m app.catalog_import \
  /app/catalog/bangladesh-starter-v1.json "$@"
