#!/bin/sh
set -eu
groot_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$groot_root"
if [ "$#" -eq 0 ]; then
  printf '%s\n' 'Usage: sh scripts/db.sh {upgrade|check|current|baseline --confirm|downgrade REV --confirm|seed-demo}' >&2
  exit 2
fi
if [ "$1" = seed-demo ]; then
  [ "$#" -eq 1 ] || exit 2
  exec docker compose run --rm -T --no-deps api python -m app.seed_demo
fi
exec docker compose run --rm -T --no-deps api python -m app.migrations "$@"
