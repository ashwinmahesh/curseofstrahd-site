#!/bin/zsh
# Points https://downloads.curseofstrahd.app/latest.json at a release, which the update commands read (update.sh on a
# Mac, update.ps1 on Windows). Run it when the site's download buttons switch to that release, after its files are
# checked, so the updaters never get ahead of the site:
#   tools/publish_latest.sh 1.0.4
# The release workflow leaves <version>/release.json beside the downloads: the full download it builds on ("base")
# and its update patch, if it has one (tools/release/patch.py in the game repo). Releases from before that are full.
set -euo pipefail
version="${1:?usage: tools/publish_latest.sh <version>}"
[[ "$version" =~ '^[0-9]+\.[0-9]+\.[0-9]+$' ]] || { echo "publish_latest: not a version: $version" >&2; exit 1; }
downloads="https://downloads.curseofstrahd.app"
base="${downloads}/${version}/CurseOfStrahd-${version}"
for f in "${base}-macos.dmg" "${base}-windows.zip"; do
	curl -fsSI "${f}?check=$(date +%s)" > /dev/null || { echo "publish_latest: missing ${f}" >&2; exit 1; }
done
release="$(curl -fsS "${downloads}/${version}/release.json?check=$(date +%s)" 2>/dev/null || echo '{}')"
tmp="$(mktemp "${TMPDIR:-/tmp}/latest.XXXXXX")"
RELEASE="$release" VERSION="$version" DOWNLOADS="$downloads" /usr/bin/python3 - > "$tmp" <<'PY'
import json, os
release = json.loads(os.environ["RELEASE"] or "{}")
version, downloads = os.environ["VERSION"], os.environ["DOWNLOADS"]
patch = release.get("patch")
if patch:
	# A patch must be on the bucket before anyone is sent to it.
	import urllib.request
	req = urllib.request.Request("%s/%s/%s" % (downloads, version, patch["file"]), method="HEAD",
		headers={"User-Agent": "curseofstrahd-release (+https://curseofstrahd.app)"})
	urllib.request.urlopen(req, timeout=30)
print(json.dumps({
	"version": version,
	"base": release.get("base", version),
	"godot": release.get("godot", "4.7.2"),
	"mac": "%s/%s/CurseOfStrahd-%s-macos.dmg" % (downloads, version, version),
	"windows": "%s/%s/CurseOfStrahd-%s-windows.zip" % (downloads, version, version),
	"patch": patch,
	"notes": "https://curseofstrahd.app/releases/",
}, indent=2))
PY
"$(dirname "$0")/r2.sh" copyto "$tmp" r2:curseofstrahd-downloads/latest.json \
	--header-upload "Content-Type: application/json" --header-upload "Cache-Control: no-cache"
rm -f "$tmp"
curl -fsS "${downloads}/latest.json?check=$(date +%s)"
