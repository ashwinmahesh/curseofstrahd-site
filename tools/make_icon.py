#!/usr/bin/env python3
"""The site's app icon from the game's title art (art/ui/title_backdrop.png): Castle Ravenloft under the moon in a
rounded, gilt-rimmed square, at every size browsers and phones ask for.

  python3 tools/make_icon.py [--game ~/Documents/CurseOfStrahdGame]
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw

SITE = Path(__file__).resolve().parent.parent


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--game", type=Path, default=Path.home() / "Documents/CurseOfStrahdGame")
	args = ap.parse_args()
	art = Image.open(args.game / "art/ui/title_backdrop.png").convert("RGB")
	side, cx, top = 600, 845, 20   # a square around the castle and the moon
	crop = art.crop((cx - side // 2, top, cx + side // 2, top + side)).resize((1024, 1024), Image.LANCZOS)
	size = 1024
	mask = Image.new("L", (size, size), 0)
	# The art stops at the gilt rim's outer edge, so none shows outside it at the corners.
	ImageDraw.Draw(mask).rounded_rectangle([10, 10, size - 11, size - 11], radius=192, fill=255)
	icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
	icon.paste(crop, (0, 0), mask)
	rim = Image.new("RGBA", (size, size), (0, 0, 0, 0))
	d = ImageDraw.Draw(rim)
	d.rounded_rectangle([10, 10, size - 11, size - 11], radius=192, outline=(176, 138, 62, 255), width=22)
	d.rounded_rectangle([34, 34, size - 35, size - 35], radius=170, outline=(79, 20, 32, 200), width=10)
	icon = Image.alpha_composite(icon, rim)
	media = SITE / "media"
	icon.save(media / "app-icon-1024.png")
	for s, name in [(512, "icon-512.png"), (192, "icon-192.png"), (32, "favicon-32.png")]:
		icon.resize((s, s), Image.LANCZOS).save(media / name)
	# iOS rounds the corners itself, so its icon is the plain square.
	crop.resize((180, 180), Image.LANCZOS).save(media / "apple-touch-icon.png")
	icon.resize((256, 256), Image.LANCZOS).save(media / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
	print("make_icon: media/favicon.ico, favicon-32, apple-touch-icon, icon-192, icon-512, app-icon-1024")


if __name__ == "__main__":
	main()
