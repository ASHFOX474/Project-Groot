#!/bin/sh
# Never shares the development volume/network/configuration; cleans only its own project.
set -eu
groot_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$groot_root"
groot_test_project="groot-tests-$(date +%s)-$$"
dc() {
  docker compose --env-file /dev/null -p "$groot_test_project" -f compose.test.yaml "$@"
}
cleanup() {
  groot_test_status=$?
  trap - EXIT
  if [ "$groot_test_status" -ne 0 ]; then dc logs --no-color --tail=100 || true; fi
  if ! dc down --remove-orphans --rmi local; then
    [ "$groot_test_status" -ne 0 ] || groot_test_status=1
  fi
  exit "$groot_test_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' HUP TERM
dc config --quiet
dc build tests
dc up --wait --wait-timeout 90 db
dc run --rm --no-deps tests "$@"
