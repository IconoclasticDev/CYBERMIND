#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")"
if [ "$(uname -s)" != "Linux" ] || [ "$(uname -m)" != "x86_64" ]; then
  echo 'This offline Docker image supports Linux x86-64.' >&2
  exit 1
fi
command -v docker >/dev/null 2>&1 || { echo 'Docker Engine and Compose are required.' >&2; exit 1; }
docker info >/dev/null || { echo 'Docker Engine is not running or this user lacks Docker access.' >&2; exit 1; }
docker compose version >/dev/null || { echo 'Docker Compose is required.' >&2; exit 1; }

expected=$(awk '$2 == "cybermind-offline-app.tar" {print $1}' images/SHA256SUMS)
[ -n "$expected" ] || { echo 'Image SHA-256 manifest is missing.' >&2; exit 1; }
actual=$(sha256sum images/cybermind-offline-app.tar | awk '{print $1}')
[ "$actual" = "$expected" ] || { echo 'Bundled Docker image failed SHA-256 verification.' >&2; exit 1; }

# Load the pinned image each time so an older image with the same tag is replaced.
docker load -i images/cybermind-offline-app.tar >/dev/null
docker compose -p cybermind-offline -f compose.offline.yaml up -d --no-build --pull never

ready=0
count=0
while [ "$count" -lt 90 ]; do
  if docker compose -p cybermind-offline -f compose.offline.yaml exec -T cybermind \
      python -c "import json,urllib.request; h=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=2)); assert h.get('status')=='ok' and h.get('model',{}).get('available') is True" \
      >/dev/null 2>&1; then
    ready=1
    break
  fi
  count=$((count + 1))
  sleep 2
done
[ "$ready" -eq 1 ] || { echo 'CYBERMIND did not become ready. Inspect docker compose logs.' >&2; exit 1; }

published=$(docker compose -p cybermind-offline -f compose.offline.yaml port cybermind 8000)
case "$published" in
  127.0.0.1:*) url="http://$published/" ;;
  *) echo "Unexpected Docker port mapping: $published" >&2; exit 1 ;;
esac
for browser in chromium chromium-browser google-chrome google-chrome-stable; do
  if command -v "$browser" >/dev/null 2>&1; then
    "$browser" --app="$url" --user-data-dir="${XDG_DATA_HOME:-$HOME/.local/share}/cybermind-webview" >/dev/null 2>&1 &
    echo 'CYBERMIND opened in an application window.'
    exit 0
  fi
done
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$url" >/dev/null 2>&1 &
  echo 'CYBERMIND opened in your default browser.'
  exit 0
fi
echo "CYBERMIND is running. Open $url"
