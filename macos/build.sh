#!/bin/bash
# Build Relay.app against this checkout's .venv and install it in /Applications.
# Python code runs from the checkout, so only changes in macos/ need a rebuild.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
python="$root/.venv/bin/python"
config="$("$python" -c 'import sys; print(f"{sys.base_prefix}/bin/python{sys.version_info[0]}.{sys.version_info[1]}-config")')"
app="/Applications/Relay.app"

mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
cp "$root/macos/Info.plist" "$app/Contents/Info.plist"
cp "$root/macos/AppIcon.icns" "$app/Contents/Resources/AppIcon.icns"
swiftc -O "$root/macos/audiotap.swift" -o "$app/Contents/MacOS/audiotap"
# shellcheck disable=SC2046  # The config flags must split into separate arguments.
clang -O2 -DVENV_PYTHON="\"$python\"" "$root/macos/launcher.c" \
    $("$config" --includes) $("$config" --embed --ldflags) \
    -o "$app/Contents/MacOS/Relay"
codesign --force --sign - --identifier com.yuxuanyan.relay.audiotap "$app/Contents/MacOS/audiotap"
codesign --force --sign - --identifier com.yuxuanyan.relay "$app"

echo "Installed $app"
