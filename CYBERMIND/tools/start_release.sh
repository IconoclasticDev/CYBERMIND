#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RELEASE_NAME=CYBERMIND_DOCKER_DESKTOP_UPLOAD_UI_2026-10-04
ARCHIVE_PATH="$PROJECT_DIR/releases/$RELEASE_NAME.zip"
MANIFEST_PATH="$PROJECT_DIR/releases/$RELEASE_NAME.manifest.json"
EXPECTED_HASH=$(sed -n 's/.*"sha256": "\([a-f0-9]*\)".*/\1/p' "$MANIFEST_PATH")
RUNTIME_DIR="$PROJECT_DIR/.runtime"
TARGET_DIR="$RUNTIME_DIR/$RELEASE_NAME"
case "$EXPECTED_HASH" in ''|*[!a-f0-9]*) echo 'Invalid release manifest.' >&2; exit 1;; esac
if [ ${#EXPECTED_HASH} -ne 64 ]; then echo 'Invalid release hash.' >&2; exit 1; fi
if [ ! -f "$TARGET_DIR/.archive-sha256" ] || [ "$(cat "$TARGET_DIR/.archive-sha256")" != "$EXPECTED_HASH" ] || [ ! -f "$TARGET_DIR/images/cybermind-offline-app.tar" ] || [ ! -f "$TARGET_DIR/launch_linux.sh" ]; then
    command -v sha256sum >/dev/null || { echo 'Install sha256sum first.' >&2; exit 1; }
    command -v unzip >/dev/null || { echo 'Install unzip first.' >&2; exit 1; }
    if [ ! -f "$ARCHIVE_PATH" ] || [ "$(wc -c < "$ARCHIVE_PATH")" -lt 1024 ]; then
        echo 'Downloading the real release archive. Initial preparation needs internet; later launches are local.'
        DOWNLOAD_URL="https://media.githubusercontent.com/media/IconoclasticDev/CYBERMIND/main/CYBERMIND/releases/$RELEASE_NAME.zip"
        if command -v curl >/dev/null; then curl -fL "$DOWNLOAD_URL" -o "$ARCHIVE_PATH.download"
        elif command -v wget >/dev/null; then wget "$DOWNLOAD_URL" -O "$ARCHIVE_PATH.download"
        else echo 'Install curl or wget, or provide the complete release ZIP.' >&2; exit 1; fi
        printf '%s  %s\n' "$EXPECTED_HASH" "$ARCHIVE_PATH.download" | sha256sum -c -
        mv "$ARCHIVE_PATH.download" "$ARCHIVE_PATH"
    fi
    printf '%s  %s\n' "$EXPECTED_HASH" "$ARCHIVE_PATH" | sha256sum -c -
    echo 'Extracting the bundled application...'
    mkdir -p "$RUNTIME_DIR"
    unzip -oq "$ARCHIVE_PATH" -d "$RUNTIME_DIR"
    for REQUIRED_FILE in launch_linux.sh compose.offline.yaml ui/index.html images/cybermind-offline-app.tar; do
        [ -f "$TARGET_DIR/$REQUIRED_FILE" ] || { echo "Missing release file: $REQUIRED_FILE" >&2; exit 1; }
    done
    printf '%s\n' "$EXPECTED_HASH" > "$TARGET_DIR/.archive-sha256"
fi
if [ "${1:-}" = '--prepare-only' ]; then echo "Verified release ready at $TARGET_DIR"; exit 0; fi
exec sh "$TARGET_DIR/launch_linux.sh"
