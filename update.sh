#!/bin/bash
# Updates Curse of Strahd (an unofficial fan game) on this Mac to the newest version.
#
#   curl -fsSL https://curseofstrahd.app/update.sh | bash
#
# It reads the newest version from https://downloads.curseofstrahd.app/latest.json. When the game you have is the
# full download that version builds on, it fetches only a patch (the files that changed) into the game's folder
# beside your saves; otherwise it downloads the whole game and puts it in /Applications in place of the old copy.
# Your saves and settings (~/Library/Application Support/Curse of Strahd Fan Game) aren't touched. For a copy
# somewhere else, set CURSE_OF_STRAHD_APP to its path first.
set -euo pipefail

APP="${CURSE_OF_STRAHD_APP:-/Applications/Curse of Strahd.app}"
case "$APP" in
	*"/Curse of Strahd.app") ;;
	*) echo "CURSE_OF_STRAHD_APP must end in \"/Curse of Strahd.app\"" >&2; exit 1 ;;
esac
PATCHES="$HOME/Library/Application Support/Curse of Strahd Fan Game/patches"
DOWNLOADS="https://downloads.curseofstrahd.app"

latest="$(curl -fsSL "$DOWNLOADS/latest.json?$(date +%s)")"
field() { printf '%s' "$latest" | plutil -extract "$1" raw -o - - 2>/dev/null || true; }
version="$(field version)"
base="$(field base)"
url="$(field mac)"
case "$url" in
	"$DOWNLOADS"/*.dmg) ;;
	*) echo "Unexpected download address in latest.json: $url" >&2; exit 1 ;;
esac

installed="none"
if [ -d "$APP" ]; then
	installed="$(defaults read "$APP/Contents/Info" CFBundleShortVersionString 2>/dev/null || echo unknown)"
fi
current="$installed"
if [ -f "$PATCHES/patch.json" ]; then
	patch_base="$(plutil -extract base raw -o - "$PATCHES/patch.json" 2>/dev/null || true)"
	if [ "$patch_base" = "$installed" ]; then
		current="$(plutil -extract version raw -o - "$PATCHES/patch.json" 2>/dev/null || echo "$installed")"
	fi
fi
if [ "$current" = "$version" ]; then
	echo "Curse of Strahd is already on $version."
	exit 0
fi
if pgrep -f "$APP/Contents/MacOS/" > /dev/null; then
	echo "Curse of Strahd is running. Quit it first, then run this again." >&2
	exit 1
fi

work="$(mktemp -d "${TMPDIR:-/tmp}/curseofstrahd-update.XXXXXX")"
# The disk image mounts under /tmp: hdiutil can't mount it inside another mounted image, where TMPDIR may be.
mnt="$(mktemp -d /tmp/curseofstrahd-mount.XXXXXX)"
cleanup() {
	hdiutil detach -quiet "$mnt" 2>/dev/null || true
	rmdir "$mnt" 2>/dev/null || true
	rm -rf "$work"
}
trap cleanup EXIT

patch_file="$(field patch.file)"
if [ "$installed" = "$base" ] && [ -n "$patch_file" ] && [ "$version" != "$base" ]; then
	size="$(field patch.size)"
	echo "Updating Curse of Strahd from $current to $version with a patch of $((size / 1000000)) MB..."
	curl -fL --progress-bar -o "$work/patch.pck" "$DOWNLOADS/$version/$patch_file"
	if [ "$(shasum -a 256 "$work/patch.pck" | cut -d' ' -f1)" != "$(field patch.sha256)" ]; then
		echo "The patch didn't download intact. Run this again." >&2
		exit 1
	fi
	mkdir -p "$PATCHES"
	mv "$work/patch.pck" "$PATCHES/patch.pck.new"
	printf '{"base": "%s", "version": "%s"}\n' "$base" "$version" > "$PATCHES/patch.json.new"
	mv "$PATCHES/patch.pck.new" "$PATCHES/patch.pck"
	mv "$PATCHES/patch.json.new" "$PATCHES/patch.json"
	echo "Done: Curse of Strahd is on $version. Your saves and settings carry over."
	exit 0
fi

echo "Updating Curse of Strahd from $current to $version (a full download of about 3 GB)..."
curl -fL --progress-bar -o "$work/game.dmg" "$url"
hdiutil attach -nobrowse -readonly -mountpoint "$mnt" "$work/game.dmg" > /dev/null
# Copy the new version beside the old one, then swap, so a failed copy leaves the old game as it was.
next="$(dirname "$APP")/.Curse of Strahd.app.updating"
rm -rf "$next"
ditto "$mnt/Curse of Strahd.app" "$next"
# The disk image's window marks the app with Finder info (its extension hidden), which strict signature checks reject.
xattr -d com.apple.FinderInfo "$next" 2>/dev/null || true
rm -rf "$APP"
mv "$next" "$APP"
# An old patch builds on the old download; the game would ignore it, so it goes.
rm -f "$PATCHES/patch.pck" "$PATCHES/patch.json"
echo "Done: Curse of Strahd $version is in $(dirname "$APP"). Your saves and settings carry over."
