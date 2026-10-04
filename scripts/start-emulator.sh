#!/bin/sh
set -eu
groot_sdk=${ANDROID_HOME:-${ANDROID_SDK_ROOT:-"$HOME/Library/Android/sdk"}}
if [ ! -x "$groot_sdk/emulator/emulator" ]; then
  printf '%s\n' 'Android Emulator not found. See docs/SETUP_MAC.md.' >&2
  exit 1
fi
exec "$groot_sdk/emulator/emulator" -avd "${1:-Groot_API_36}" -no-snapshot-load -no-metrics
