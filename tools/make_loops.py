#!/usr/bin/env python3
"""Short looping clips from captured frames (owner, 2026-10-09: GIFs of the game's motion), in two forms:

  /usr/bin/python3 tools/make_loops.py <clips folder> <name>[:start:seconds[:x0,y0,x1,y1]] ... [--out=media/loops]
      [--gifs=build/gifs] [--as=<name to save one loop under>]

- <gifs>/<name>.gif for the game's README on GitHub (the site doesn't use them): 480 px wide, 10 frames a second, one
  shared palette, looping, kept to a few MB (rain, fog and grain make big GIFs).
- <out>/<name>.mp4 and <name>.jpg for the site, where a muted looping video is a fraction of the GIF's size:
  960 px wide at 30 frames a second (build/encode, the Mac's own encoder), with its last frame as the poster.
Each name is a clip's folder of frames (f0000.jpg on, 30 a second, as tools/capture.py records them); start and seconds
pick part of it, and a box crops it (in the frames' pixels), e.g. the d20's panel. A cropped loop keeps its own width
up to 640 px in the GIF.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

SITE = Path(__file__).resolve().parent.parent


def frames_of(folder: Path, start: float, seconds: float) -> list:
	frames = sorted(folder.glob("f*.jpg"))
	a = int(start * 30)
	b = len(frames) if seconds <= 0 else min(len(frames), a + int(seconds * 30))
	return frames[a:b]


def load(f: Path, box: tuple) -> Image.Image:
	im = Image.open(f).convert("RGB")
	return im.crop(box) if box else im


def gif(frames: list, out: Path, box: tuple = (), width: int = 480, step: int = 3) -> None:
	picked = frames[::step]
	shots = []
	if box:
		width = min(640, box[2] - box[0])
	for f in picked:
		im = load(f, box)
		shots.append(im.resize((width, round(im.height * width / im.width)), Image.LANCZOS))
	# One palette from a few frames across the loop, so colours don't shimmer from frame to frame.
	sample = Image.new("RGB", (width, shots[0].height * 4))
	for k, idx in enumerate(range(0, len(shots), max(1, len(shots) // 4))):
		if k < 4:
			sample.paste(shots[idx], (0, shots[0].height * k))
	palette = sample.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
	quantized = [s.quantize(palette=palette, dither=Image.Dither.NONE) for s in shots]
	quantized[0].save(out, save_all=True, append_images=quantized[1:], duration=int(1000 * step / 30), loop=0,
		optimize=True, disposal=1)


def mp4(frames: list, out: Path, box: tuple = (), width: int = 960) -> None:
	if box:
		width = min(960, (box[2] - box[0]) // 2 * 2)
	with tempfile.TemporaryDirectory() as tmp:
		for i, f in enumerate(frames):
			im = load(f, box)
			im.resize((width, round(im.height * width / im.width) // 2 * 2), Image.LANCZOS).save(
				Path(tmp) / ("f%04d.jpg" % i), quality=92)
		subprocess.run([str(SITE / "build/encode"), "--frames", tmp, "--out", str(out), "--fps", "30",
			"--bitrate", "3000000"], check=True, capture_output=True)
	first = load(frames[-1], box)   # the poster is the loop's settled end (the d20's result, the place arrived at)
	first.resize((width, round(first.height * width / first.width))).save(out.with_suffix(".jpg"), quality=85)


def main() -> None:
	args = [a for a in sys.argv[1:] if not a.startswith("--")]
	opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
	clips, names = Path(args[0]), args[1:]
	out = Path(opts.get("out", str(SITE / "media/loops")))
	gifs = Path(opts.get("gifs", str(SITE / "build/gifs")))
	out.mkdir(parents=True, exist_ok=True)
	gifs.mkdir(parents=True, exist_ok=True)
	for spec in names:
		name, *rest = spec.split(":")
		start = float(rest[0]) if rest else 0.0
		seconds = float(rest[1]) if len(rest) > 1 else 0.0
		box = tuple(int(v) for v in rest[2].split(",")) if len(rest) > 2 else ()
		frames = frames_of(clips / name, start, seconds)
		if not frames:
			print("make_loops: no frames for %s" % name)
			continue
		label = opts.get("as", "") if len(names) == 1 and opts.get("as") else name
		gif(frames, gifs / (label + ".gif"), box)
		mp4(frames, out / (label + ".mp4"), box)
		print("make_loops: %s: %d frames, gif %.1f MB, mp4 %.1f MB" % (label, len(frames),
			(gifs / (label + ".gif")).stat().st_size / 1e6, (out / (label + ".mp4")).stat().st_size / 1e6))


if __name__ == "__main__":
	main()
