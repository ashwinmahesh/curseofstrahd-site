#!/usr/bin/env python3
"""Switch the site's download buttons, llms.txt and release notes from one release to the next (used for 1.0.5):

  /usr/bin/python3 tools/switch_release.py 1.0.4 1.0.5 "October 12, 2026" build/release_1.0.5_entry.html

The entry is the new <article class="release"> block for releases/index.html, with RELEASE_DATE where the date goes.

Reads the new files' sizes from the bucket, so run it only after the release's downloads are up and checked.
"""
import re
import sys
import time
import urllib.request
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
DOWNLOADS = "https://downloads.curseofstrahd.app"


def size_gb(url: str) -> str:
	req = urllib.request.Request("%s?check=%d" % (url, time.time()), method="HEAD",
		headers={"User-Agent": "curseofstrahd-release (+https://curseofstrahd.app)"})
	n = int(urllib.request.urlopen(req, timeout=30).headers["Content-Length"])
	return "%.1f GB" % (n / 1e9)


def main() -> None:
	old, new, date, entry_path = sys.argv[1:5]
	mac = "%s/%s/CurseOfStrahd-%s-macos.dmg" % (DOWNLOADS, new, new)
	win = "%s/%s/CurseOfStrahd-%s-windows.zip" % (DOWNLOADS, new, new)
	mac_gb, win_gb = size_gb(mac), size_gb(win)

	def swap(text: str) -> str:
		text = text.replace("/%s/CurseOfStrahd-%s-" % (old, old), "/%s/CurseOfStrahd-%s-" % (new, new))
		text = text.replace('"softwareVersion": "%s"' % old, '"softwareVersion": "%s"' % new)
		text = text.replace("Free, version %s." % old, "Free, version %s." % new)
		text = text.replace("Version %s." % old, "Version %s." % new)
		text = text.replace("version %s]" % old, "version %s]" % new)
		return text

	page = SITE / "index.html"
	t = swap(page.read_text())
	t = re.sub(r"(For Macs with Apple silicon · )[0-9.]+ GB", r"\g<1>" + mac_gb, t)
	t = re.sub(r"(For Windows 10 and 11, 64-bit · )[0-9.]+ GB", r"\g<1>" + win_gb, t)
	t = re.sub(r"\(a [0-9.]+ GB download\)", "(a %s download)" % max(mac_gb, win_gb), t)
	page.write_text(t)
	llms = SITE / "llms.txt"
	llms.write_text(swap(llms.read_text()))

	notes = SITE / "releases/index.html"
	n = notes.read_text()
	if 'id="v%s"' % new not in n:
		entry = Path(entry_path).read_text()
		entry = re.sub(r"<!--.*?-->\s*", "", entry, flags=re.S).rstrip() + "\n\n"
		entry = entry.replace("RELEASE_DATE", date)
		anchor = '    <article class="release" id="v%s">' % old
		assert anchor in n, "no %s entry to insert above" % old
		n = n.replace(anchor, entry + anchor, 1)
		notes.write_text(n)
	for f in (page, llms):
		left = [l for l in f.read_text().splitlines() if old in l]
		print(f.name, "still mentions", old, ":", len(left))
	print("sizes:", mac_gb, win_gb)


if __name__ == "__main__":
	main()
