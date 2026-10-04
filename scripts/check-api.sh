#!/bin/sh
set -eu
groot_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$groot_root"
docker compose config --quiet
docker build --build-context legacy_init=./db/init --target test --tag groot-api-tests services/api
docker run --rm --network none --read-only --tmpfs /tmp groot-api-tests
