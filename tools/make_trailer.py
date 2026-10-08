#!/usr/bin/env python3
"""Cuts the trailer from the game's clips and storybook art, on the music, and encodes it with the Mac's own encoder.

  python3 tools/make_trailer.py [--clips build/raw/clips] [--game ~/Documents/CurseOfStrahdGame] [--only-frames]

The edit (EDIT below) is a list of segments, each lasting a number of seconds at 30 fps: a recorded clip ("clip",
folder name under --clips, optional start second), a storybook still with a slow push ("still", art path), or the end
card ("card"). Captions fade in over a segment. Segments dissolve into each other unless "cut" is set (the cut on the
music's drop); each segment starts at the sum of the seconds before it, so the cuts land on the music's marks. Writes build/trailer/f00000.jpg ..., then media/trailer.mp4 and media/trailer-poster.jpg.
"""
import argparse
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

SITE = Path(__file__).resolve().parent.parent
W, H, FPS = 1920, 1080, 30
DISSOLVE = 8
FONT = "/System/Library/Fonts/Supplemental/Luminari.ttf"   # the game's own display face (UiKit.display_font)
GOLD = (226, 196, 117)
PARCHMENT = (240, 226, 192)
RED = (179, 40, 60)
# ISAo, "Dark Gothic Haunted Masquerade" (OGA-BY 3.0): a quiet opening, the full band coming in at 26.0 s, a lower
# coda from 76 s and the fade at 88 s. The edit is laid on those marks.
MUSIC = "art/sourced/oga_isao/short_The Enchanting Haunted Ballroom_0.mp3"

EDIT = [
	{"clip": "title", "seconds": 6.0},
	{"still": "art/cutscenes/mists_arrival.jpg", "seconds": 4.0, "caption": "The mists have closed behind you."},
	{"clip": "road", "seconds": 3.5, "from": 1.0},
	{"clip": "village", "seconds": 3.5, "from": 1.0, "caption": "86 places in a valley under a vampire's rule"},
	{"clip": "vallaki", "seconds": 3.0, "from": 1.0},
	{"clip": "dialogue", "seconds": 3.5, "from": 1.5, "caption": "Talk your way in. Or out."},
	{"still": "art/cutscenes/strahd_watcher_alone.jpg", "seconds": 2.5, "push": 1.12},
	{"clip": "fight_smite", "seconds": 3.0, "cut": True, "caption": "Turn-based fights on the 2024 rules"},
	{"clip": "fight_fireball", "seconds": 3.5, "from": 0.3},
	{"clip": "fight_odds", "seconds": 2.5, "caption": "See the odds before every roll"},
	{"clip": "fight_blast", "seconds": 2.5, "from": 0.3},
	{"clip": "fight_guardians", "seconds": 2.5, "from": 0.2},
	{"clip": "krezk", "seconds": 3.5, "from": 0.5, "caption": "Six companions. Four at your side."},
	{"clip": "tser", "seconds": 3.0, "from": 0.5},
	{"still": "art/cutscenes/madam_eva_reading.jpg", "seconds": 3.0, "push": 1.1,
		"caption": "The cards change every playthrough"},
	{"clip": "gates", "seconds": 3.5, "from": 0.5},
	{"clip": "boss", "seconds": 5.0, "from": 0.5},
	{"clip": "fight_last", "seconds": 3.5, "from": 0.3},
	{"clip": "castle", "seconds": 7.0, "caption": "Barovia has no way out. Only through."},
	{"still": "art/cutscenes/village_rain.jpg", "seconds": 3.5, "push": 1.08},
	{"still": "art/cutscenes/tser_pool_fire.jpg", "seconds": 4.0, "push": 1.08},
	{"card": True, "seconds": 12.0},
]


def font(size: int) -> ImageFont.FreeTypeFont:
	try:
		return ImageFont.truetype(FONT, size)
	except OSError:
		return ImageFont.truetype("/System/Library/Fonts/Supplemental/Baskerville.ttc", size)


def cover(img: Image.Image) -> Image.Image:
	"""Fills the frame, cropping what's over."""
	img = img.convert("RGB")
	k = max(W / img.width, H / img.height)
	img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
	x, y = (img.width - W) // 2, (img.height - H) // 2
	return img.crop((x, y, x + W, y + H))


def still_frames(path: Path, n: int, push: float) -> list:
	src = Image.open(path).convert("RGB")
	base = cover(src) if push <= 1.0 else None
	out = []
	for i in range(n):
		if base is not None:
			out.append(base)
			continue
		# A slow push in toward the middle, a little up.
		k = 1.0 + (push - 1.0) * (i / max(n - 1, 1))
		cw, ch = src.width / k, src.height / k
		cx = src.width / 2
		cy = min(max(src.height * 0.47, ch / 2), src.height - ch / 2)
		box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
		out.append(cover(src.crop(tuple(round(v) for v in box))))
	return out


def clip_frames(folder: Path, n: int, start: float) -> list:
	files = sorted(folder.glob("f*.jpg"))
	if not files:
		raise SystemExit("make_trailer: no frames in %s" % folder)
	first = int(start * FPS)
	picked = [files[min(first + i, len(files) - 1)] for i in range(n)]
	return [Image.open(f).convert("RGB").resize((W, H), Image.LANCZOS) if Image.open(f).size != (W, H)
		else Image.open(f).convert("RGB") for f in picked]


def caption(img: Image.Image, text: str, alpha: float) -> Image.Image:
	if alpha <= 0:
		return img
	layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
	d = ImageDraw.Draw(layer)
	f = font(58)
	tw = d.textlength(text, font=f)
	x, y = (W - tw) / 2, H - 190
	# A soft dark band behind the words, then the words with a shadow.
	band = Image.new("L", (W, H), 0)
	ImageDraw.Draw(band).rectangle([0, y - 40, W, y + 110], fill=int(150 * alpha))
	band = band.filter(ImageFilter.GaussianBlur(30))
	layer = Image.composite(Image.new("RGBA", (W, H), (8, 3, 4, 255)), layer, band)
	d = ImageDraw.Draw(layer)
	a = int(255 * alpha)
	d.text((x + 3, y + 3), text, font=f, fill=(0, 0, 0, a))
	d.text((x, y), text, font=f, fill=GOLD + (a,))
	return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def card_frames(game: Path, n: int) -> list:
	art = ImageEnhance.Brightness(cover(Image.open(game / "art/ui/title_backdrop.png"))).enhance(0.45)
	out = []
	for i in range(n):
		t = i / FPS
		img = art.copy().convert("RGBA")
		layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
		d = ImageDraw.Draw(layer)

		def line(text: str, size: int, y: float, colour: tuple, appear: float) -> None:
			a = max(0.0, min(1.0, (t - appear) / 0.8))
			if a <= 0:
				return
			f = font(size)
			tw = d.textlength(text, font=f)
			d.text(((W - tw) / 2 + 4, y + 4), text, font=f, fill=(0, 0, 0, int(220 * a)))
			d.text(((W - tw) / 2, y), text, font=f, fill=colour + (int(255 * a),))

		line("Curse of Strahd", 150, 330, RED, 0.3)
		line("An unofficial fan game", 54, 540, PARCHMENT, 1.4)
		line("A turn-based tactical RPG on the 2024 rules", 40, 630, GOLD, 2.2)
		line("Coming soon", 48, 760, PARCHMENT, 3.2)
		img = Image.alpha_composite(img, layer).convert("RGB")
		# The last two seconds fade to black.
		fade = max(0.0, min(1.0, (t - (n / FPS - 2.0)) / 2.0))
		if fade > 0:
			img = Image.blend(img, Image.new("RGB", (W, H)), fade)
		out.append(img)
	return out


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--clips", type=Path, default=SITE / "build/raw/clips")
	ap.add_argument("--game", type=Path, default=Path.home() / "Documents/CurseOfStrahdGame")
	ap.add_argument("--only-frames", action="store_true")
	args = ap.parse_args()
	frames_dir = SITE / "build/trailer"
	shutil.rmtree(frames_dir, ignore_errors=True)
	frames_dir.mkdir(parents=True)
	written = 0
	at = 0.0
	tail: list = []   # the frames past the end of the segment before, dissolved into the start of this one
	for seg_i, seg in enumerate(EDIT):
		n = round(seg["seconds"] * FPS)
		nxt = EDIT[seg_i + 1] if seg_i + 1 < len(EDIT) else None
		# A segment runs on past its end by DISSOLVE frames when the next one dissolves in, so the edit's times hold.
		over = DISSOLVE if nxt is not None and not nxt.get("cut") else 0
		if "clip" in seg:
			frames = clip_frames(args.clips / seg["clip"], n + over, float(seg.get("from", 0.0)))
		elif "still" in seg:
			frames = still_frames(args.game / seg["still"], n + over, float(seg.get("push", 1.06)))
		else:
			frames = card_frames(args.game, n + over)
		if "caption" in seg:
			for i in range(n + over):
				t = i / FPS
				a = max(0.0, min(1.0, t / 0.5, (seg["seconds"] - t) / 0.5))
				frames[i] = caption(frames[i], seg["caption"], a)
		if seg_i == 0:
			# Up from black.
			for i in range(min(20, n)):
				frames[i] = Image.blend(Image.new("RGB", (W, H)), frames[i], i / 20)
		for i, prev in enumerate(tail):
			frames[i] = Image.blend(prev, frames[i], (i + 1) / (len(tail) + 1))
		tail = frames[n:]
		for img in frames[:n]:
			img.save(frames_dir / ("f%05d.jpg" % written), quality=92)
			written += 1
		print("make_trailer: %6.2f s  %s" % (at, seg.get("clip") or Path(seg.get("still", "card")).stem))
		at += seg["seconds"]
	print("make_trailer: %d frames, %.1f s" % (written, written / FPS))
	if args.only_frames:
		return
	encode = SITE / "build/encode"
	if not encode.exists():
		subprocess.run(["swiftc", "-O", str(SITE / "tools/encode.swift"), "-o", str(encode)], check=True)
	subprocess.run([str(encode), "--frames", str(frames_dir), "--out", str(SITE / "media/trailer.mp4"), "--fps", "30",
		"--bitrate", "6000000", "--audio", str(args.game / MUSIC), "--fade", "2.5"], check=True)
	# The poster: the Fireball's frame.
	poster_at = 0
	for seg in EDIT:
		if seg.get("clip") == "fight_fireball":
			poster_at += round(1.2 * FPS)
			break
		poster_at += round(seg["seconds"] * FPS)
	Image.open(frames_dir / ("f%05d.jpg" % min(poster_at, written - 1))).save(SITE / "media/trailer-poster.jpg", quality=86)
	print("make_trailer: media/trailer.mp4 and media/trailer-poster.jpg")


if __name__ == "__main__":
	main()
