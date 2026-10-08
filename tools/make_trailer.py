#!/usr/bin/env python3
"""Cuts the trailer from the game's clips and storybook art, on the music, and encodes it with the Mac's own encoder.

  python3 tools/make_trailer.py [--cut v2] [--status "Coming soon"] [--clips build/raw/clips] [--only-frames]

The edit (EDIT below) is a list of segments, each lasting a number of seconds at 30 fps: a recorded clip ("clip",
folder name under --clips, optional start second), a storybook still with a slow push ("still", art path), or the end
card ("card"). Captions fade in over a segment. Segments dissolve into each other unless "cut" is set (the cut on the
music's drop); each segment starts at the sum of the seconds before it, so the cuts land on the music's marks. Writes build/trailer/f00000.jpg ..., then media/trailer.mp4 and media/trailer-poster.jpg (v1), or
media/trailer-v2.mp4 and media/trailer-v2-poster.jpg (v2, with Strahd's narration from build/voice mixed over the music,
which ducks under each line). --status is the end card's last line.
"""
import argparse
import audioop
import math
import shutil
import subprocess
import wave
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

EDIT_V1 = [
	{"clip": "title", "seconds": 6.0},
	{"still": "art/cutscenes/mists_arrival.jpg", "seconds": 4.0, "caption": "The mists have closed behind you."},
	{"clip": "road", "seconds": 3.5, "from": 1.0},
	{"clip": "village", "seconds": 3.5, "from": 1.0, "caption": "86 places in a valley under a vampire's rule"},
	{"clip": "vallaki", "seconds": 3.0, "from": 1.0},
	{"clip": "dialogue", "seconds": 3.5, "from": 1.5, "caption": "Talk your way in. Or out."},
	{"still": "art/cutscenes/strahd_watcher_alone.jpg", "seconds": 2.5, "push": 1.12},
	{"clip": "fight_smite", "seconds": 3.0, "cut": True, "hud": True, "caption": "Turn-based fights on the 2024 rules"},
	{"clip": "fight_fireball", "seconds": 3.5, "from": 0.3},
	{"clip": "fight_odds", "seconds": 2.5, "hud": True, "caption": "See the odds before every roll"},
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

# v2 (owner's asks, 2026-10-08): Strahd narrates over the quiet opening and the coda, an interior walked by candlelight,
# character creation and a level up. Captions only where he isn't speaking.
EDIT_V2 = [
	{"clip": "title", "seconds": 6.0},
	{"still": "art/cutscenes/mists_arrival.jpg", "seconds": 4.0},
	{"clip": "road", "seconds": 2.5, "from": 1.0},
	{"clip": "village", "seconds": 2.5, "from": 1.0},
	{"clip": "interior_death_house", "seconds": 3.5, "from": 1.0},
	{"clip": "vallaki", "seconds": 2.0, "from": 1.5},
	{"clip": "dialogue", "seconds": 3.0, "from": 1.5},
	{"still": "art/cutscenes/strahd_watcher_alone.jpg", "seconds": 2.5, "push": 1.12},
	{"clip": "fight_smite", "seconds": 3.0, "cut": True, "hud": True, "caption": "Turn-based fights on the 2024 rules"},
	{"clip": "fight_fireball", "seconds": 3.5, "from": 0.3},
	{"clip": "fight_odds", "seconds": 2.5, "hud": True, "caption": "See the odds before every roll"},
	{"clip": "fight_blast", "seconds": 2.0, "from": 0.3},
	{"clip": "fight_guardians", "seconds": 2.5, "from": 0.2},
	{"clip": "creation", "seconds": 4.0, "from": 1.5, "caption": "Make a hero of your own"},
	{"clip": "levelup", "seconds": 3.0, "from": 2.0, "caption": "Every 2024 choice at every level"},
	{"still": "art/cutscenes/madam_eva_reading.jpg", "seconds": 4.5, "push": 1.1},
	{"clip": "krezk", "seconds": 3.0, "from": 0.5, "caption": "Six companions. Four at your side."},
	{"clip": "gates", "seconds": 3.0, "from": 0.5},
	{"clip": "boss", "seconds": 4.5, "from": 0.5},
	{"clip": "fight_last", "seconds": 3.5, "from": 0.3},
	{"clip": "castle", "seconds": 7.0},
	{"still": "art/cutscenes/tser_pool_fire.jpg", "seconds": 4.0, "push": 1.08},
	{"card": True, "seconds": 12.0},
]

# Strahd's lines (build/voice/strahd_trailer_NN.mp3) and when each starts, in seconds.
VOICE_V2 = [(1.0, "01"), (6.3, "02"), (11.2, "03"), (18.7, "04"), (23.7, "05"), (46.7, "06"), (58.2, "07"),
	(65.8, "08"), (78.5, "09")]
# v3 (owner's asks, 2026-10-08): the game's own sound under the fights and the boss, a voiced exchange with a bust on each
# side (the Baron and Kip), "Available now" on the end card, and the music left at full under Strahd's last line.
# "sound" lays the clip's own audio (from the Movie Maker run, build/audio/game_movie.wav) under the music; "voices"
# also dips the music under it. The Blinsky clip under Strahd's "speak to my people" gives way to the inn's townsfolk.
EDIT_V3 = [
	{"clip": "title", "seconds": 6.0},
	{"still": "art/cutscenes/mists_arrival.jpg", "seconds": 4.0},
	{"clip": "road", "seconds": 2.5, "from": 1.0},
	{"clip": "village", "seconds": 2.5, "from": 1.0},
	{"clip": "interior_death_house", "seconds": 3.5, "from": 1.0},
	{"clip": "vallaki", "seconds": 2.0, "from": 1.5},
	{"clip": "interior_inn", "seconds": 3.0, "from": 1.0},
	{"still": "art/cutscenes/strahd_watcher_alone.jpg", "seconds": 2.5, "push": 1.12},
	{"clip": "fight_smite", "seconds": 3.0, "cut": True, "hud": True, "sound": True,
		"caption": "Turn-based fights on the 2024 rules"},
	{"clip": "fight_fireball", "seconds": 3.5, "from": 0.3, "sound": True},
	{"clip": "fight_odds", "seconds": 2.5, "hud": True, "caption": "See the odds before every roll"},
	{"clip": "dialogue_voiced", "seconds": 5.7, "from": 1.85, "hud": True, "voices": True,
		"caption": "Every line voiced"},
	{"clip": "dialogue_voiced", "seconds": 4.1, "from": 20.75, "voices": True},
	{"clip": "creation", "seconds": 3.2, "from": 1.5, "caption": "Make a hero of your own"},
	{"still": "art/cutscenes/madam_eva_reading.jpg", "seconds": 4.2, "push": 1.1},
	{"clip": "levelup", "seconds": 2.6, "from": 2.0, "caption": "Every 2024 choice at every level"},
	{"clip": "boss", "seconds": 4.6, "from": 0.5, "sound": True},
	{"clip": "fight_last", "seconds": 3.4, "from": 0.3, "sound": True},
	{"clip": "castle", "seconds": 6.6},
	{"clip": "gates", "seconds": 2.6, "from": 0.5},
	{"still": "art/cutscenes/tser_pool_fire.jpg", "seconds": 4.0, "push": 1.08},
	{"card": True, "seconds": 12.0},
]
# (start, line, dip the music?) The last line keeps the music at full (owner, 2026-10-08).
VOICE_V3 = [(1.0, "01", True), (6.3, "02", True), (11.2, "03", True), (18.7, "04", True), (23.7, "05", True),
	(48.1, "06", True), (56.0, "07", True), (63.6, "08", True), (78.5, "09", False)]
CUTS = {"v1": (EDIT_V1, []), "v2": (EDIT_V2, VOICE_V2), "v3": (EDIT_V3, VOICE_V3)}
# The game's sound from the Movie Maker run, and how its frames line up (each clip's first frame, from the run's log).
GAME_SOUND = "build/audio/game_movie.wav"
GAME_LOG = "build/raw/clips/site_game.log"
SOUND_PEAK = 31000  # the fights' own effects, brought up to this peak (the mix's limiter catches the loudest hits)
SOUND_DUCK = 0.35   # the music dips this far under each blow and comes back between them
SOUND_LAG = 2       # frames: the movie's sound runs this far ahead of the recorded pictures
# The music under a line (about -10 dB), how long it takes to dip and to come back, and the voice's gain.
DUCK = 0.25
DUCK_IN = 0.3
DUCK_OUT = 0.6
VOICE_PEAK = 26000   # each line is brought to this peak (of 32767), loud over the dipped music without clipping
HEADROOM = 0.7   # the music is scaled down before the lines are added, so the sum never clips, then raised back
RATE = 44100


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


def caption(img: Image.Image, text: str, alpha: float, y: float = H - 190) -> Image.Image:
	if alpha <= 0:
		return img
	layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
	d = ImageDraw.Draw(layer)
	f = font(58)
	tw = d.textlength(text, font=f)
	x = (W - tw) / 2
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


def card_frames(game: Path, n: int, status: str, tagline: bool) -> list:
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

		line("Curse of Strahd", 150, 300, RED, 0.3)
		if tagline:
			line("Barovia has no way out. Only through.", 50, 500, GOLD, 1.2)
		line("An unofficial fan game", 46, 590 if tagline else 540, PARCHMENT, 1.8)
		line("A turn-based tactical RPG on the 2024 rules", 36, 660 if tagline else 630, GOLD, 2.4)
		line(status, 48, 780, PARCHMENT, 3.2)
		img = Image.alpha_composite(img, layer).convert("RGB")
		# The last two seconds fade to black.
		fade = max(0.0, min(1.0, (t - (n / FPS - 2.0)) / 2.0))
		if fade > 0:
			img = Image.blend(img, Image.new("RGB", (W, H)), fade)
		out.append(img)
	return out


def to_wav(src: Path, dst: Path, channels: int) -> bytes:
	"""Decodes any audio file to 16-bit 44.1 kHz PCM with the Mac's own converter; returns the frames."""
	subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@%d" % RATE, "-c", str(channels), str(src), str(dst)],
		check=True)
	with wave.open(str(dst)) as w:
		assert w.getsampwidth() == 2 and w.getframerate() == RATE and w.getnchannels() == channels
		return w.readframes(w.getnframes())


def mix_audio(game: Path, voice: list, seconds: float, out: Path, game_sound: list = []) -> Path:
	"""The music for `seconds`, dipping under each of Strahd's lines (and the game's own sound), with them laid over it."""
	tmp = SITE / "build/audio"
	tmp.mkdir(parents=True, exist_ok=True)
	music = bytearray(to_wav(game / MUSIC, tmp / "music.wav", 2))
	total = int(seconds * RATE) * 4
	music = music[:total] + bytearray(max(0, total - len(music)))
	lines = []
	spans = []   # (start, end, how low the music goes)
	for entry in voice:
		at, nn = entry[0], entry[1]
		mono = to_wav(SITE / ("build/voice/strahd_trailer_%s.mp3" % nn), tmp / ("v%s.wav" % nn), 1)
		g = VOICE_PEAK / max(audioop.max(mono, 2), 1)
		data = audioop.tostereo(mono, 2, g, g)
		lines.append((at, data))
		if len(entry) < 3 or entry[2]:
			spans.append((at, at + len(data) / 4 / RATE, DUCK))
	# The dip, 10 ms at a time: down over DUCK_IN before a line, back up over DUCK_OUT after it.
	step = RATE // 100
	side = {}   # 10 ms step -> the music's level under the game's effects there
	for at, data, duck in game_sound:
		lines.append((at, data))
		if duck is not None:
			spans.append((at, at + len(data) / 4 / RATE, duck))
		else:
			first = int(at * RATE) // step
			for k, level in enumerate(follow(data, step)):
				side[first + k] = min(side.get(first + k, 1.0), level)
	out_pcm = bytearray()
	for i in range(0, total // 4, step):
		t = i / RATE
		gain = 1.0
		for a, b, duck in spans:
			if a - DUCK_IN <= t <= b + DUCK_OUT:
				depth = min(1.0, (t - (a - DUCK_IN)) / DUCK_IN, (b + DUCK_OUT - t) / DUCK_OUT)
				gain = min(gain, 1.0 - (1.0 - duck) * depth)
		gain = min(gain, side.get(i // step, 1.0)) * HEADROOM
		out_pcm += audioop.mul(bytes(music[i * 4:(i + step) * 4]), 2, gain)
	# Summed in 32 bits (at a quarter of full scale, so four loud layers can't wrap), then held under full scale.
	wide = bytearray(audioop.mul(audioop.lin2lin(bytes(out_pcm), 2, 4), 4, 0.25))
	for at, data in lines:
		s = int(at * RATE) * 8
		seg = bytes(wide[s:s + len(data) * 2])
		layer = audioop.mul(audioop.lin2lin(data, 2, 4), 4, 0.25)
		wide[s:s + len(seg)] = audioop.add(seg, layer[:len(seg)], 4)
	out_pcm, squeezed = limit(bytes(wide))
	with wave.open(str(out), "wb") as w:
		w.setnchannels(2)
		w.setsampwidth(2)
		w.setframerate(RATE)
		w.writeframes(out_pcm)
	print("make_trailer: mixed %d lines and sounds over the music (limited %.1f s, at most %.1f dB)"
		% (len(lines), squeezed[0], squeezed[1]))
	return out


def follow(data: bytes, step: int) -> list:
	"""The music's level under the game's effects, per `step` samples: nothing below -42 dB, the full SOUND_DUCK from
	-24 dB, down over 20 ms (starting 20 ms early) and back up over 250 ms, so the music swells again between blows."""
	loud = []
	for k in range(0, len(data) // 4, step):
		r = audioop.rms(data[k * 4:(k + step) * 4], 2)
		d = 20 * math.log10(max(r, 1) / 32768)
		loud.append(1.0 - (1.0 - SOUND_DUCK) * min(1.0, max(0.0, (d + 42) / 18)))
	out = []
	level = 1.0
	for k in range(len(loud)):
		target = min(loud[k:k + 3])
		level = max(target, level - 0.5) if target < level else min(target, level + 0.04)
		out.append(level)
	return out


LIMIT = 30000   # 16-bit peak the mix is held under


def limit(wide: bytes) -> tuple:
	"""32-bit stereo at a quarter scale to 16-bit, turning down only the moments that would pass LIMIT: the gain drops
	the 5 ms before a peak and comes back up over about 150 ms. Returns the PCM and (seconds turned down, deepest dB)."""
	step = RATE // 200
	size = step * 8
	n = (len(wide) + size - 1) // size
	# 0.25 of full scale in 32 bits is full scale in 16 bits once lin2lin drops the low half, so 4x for 16-bit units.
	peaks = [audioop.max(wide[i * size:(i + 1) * size], 4) * 4 / 65536 for i in range(n)]
	want = [min(1.0, LIMIT / p) if p > 0 else 1.0 for p in peaks]
	gains = []
	g = 1.0
	for i in range(n):
		target = min(want[i:i + 2])
		g = target if target < g else min(target, g + 1.0 / 30)
		gains.append(g)
	out = bytearray()
	for i in range(n):
		chunk = audioop.mul(wide[i * size:(i + 1) * size], 4, 4 * gains[i])
		out += audioop.lin2lin(chunk, 4, 2)
	low = [x for x in gains if x < 0.999]
	return bytes(out), (len(low) * step / RATE, 20 * math.log10(min(gains)) if gains else 0.0)


def game_sound_for(edit: list) -> list:
	"""(start in the trailer, 44.1 kHz stereo PCM, music level under it, or None to dip only under each blow) for each
	segment with "sound" or "voices"."""
	log = SITE / GAME_LOG
	src = SITE / GAME_SOUND
	if not log.exists() or not src.exists():
		return []
	first = {}
	for line in log.read_text().splitlines():
		if line.startswith("segment "):
			_, name, _, frame, _ = line.split()
			first[name] = int(frame)
	with wave.open(str(src)) as w:
		rate, channels = w.getframerate(), w.getnchannels()
		pcm = w.readframes(w.getnframes())
	out = []
	at = 0.0
	for seg in edit:
		if (seg.get("sound") or seg.get("voices")) and seg.get("clip") in first:
			start = (first[seg["clip"]] + SOUND_LAG) / FPS + float(seg.get("from", 0.0))
			a = int(start * rate) * 2 * channels
			b = a + int(seg["seconds"] * rate) * 2 * channels
			piece = pcm[a:b]
			if channels == 1:
				piece = audioop.tostereo(piece, 2, 1, 1)
			piece, _ = audioop.ratecv(piece, 2, 2, rate, RATE, None)
			if seg.get("voices"):
				g = VOICE_PEAK / max(audioop.max(piece, 2), 1)
				out.append((at, audioop.mul(piece, 2, g), DUCK))
			else:
				g = SOUND_PEAK / max(audioop.max(piece, 2), 1)
				out.append((at, audioop.mul(piece, 2, g), None))
		at += seg["seconds"]
	return out


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--clips", type=Path, default=SITE / "build/raw/clips")
	ap.add_argument("--game", type=Path, default=Path.home() / "Documents/CurseOfStrahdGame")
	ap.add_argument("--only-frames", action="store_true")
	ap.add_argument("--cut", choices=sorted(CUTS), default="v3")
	ap.add_argument("--status", default="Coming soon", help="the end card's last line")
	ap.add_argument("--reuse-frames", action="store_true", help="re-encode (and remix) from build/trailer as it is")
	args = ap.parse_args()
	EDIT, voice = CUTS[args.cut]
	frames_dir = SITE / "build/trailer"
	draw = [] if args.reuse_frames else EDIT   # with --reuse-frames the frames are already there
	if not args.reuse_frames:
		shutil.rmtree(frames_dir, ignore_errors=True)
		frames_dir.mkdir(parents=True)
	written = len(list(frames_dir.glob("f*.jpg"))) if args.reuse_frames else 0
	at = 0.0
	tail: list = []   # the frames past the end of the segment before, dissolved into the start of this one
	for seg_i, seg in enumerate(draw):
		n = round(seg["seconds"] * FPS)
		nxt = draw[seg_i + 1] if seg_i + 1 < len(draw) else None
		# A segment runs on past its end by DISSOLVE frames when the next one dissolves in, so the edit's times hold.
		over = DISSOLVE if nxt is not None and not nxt.get("cut") else 0
		if "clip" in seg:
			frames = clip_frames(args.clips / seg["clip"], n + over, float(seg.get("from", 0.0)))
		elif "still" in seg:
			frames = still_frames(args.game / seg["still"], n + over, float(seg.get("push", 1.06)))
		else:
			frames = card_frames(args.game, n + over, args.status, bool(voice))
		if "caption" in seg:
			for i in range(n + over):
				t = i / FPS
				a = max(0.0, min(1.0, t / 0.5, (seg["seconds"] - t) / 0.5))
				# Over the fight's interface the words sit under the turn order, clear of the hotbar.
				frames[i] = caption(frames[i], seg["caption"], a, 215 if seg.get("hud") else H - 190)
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
	name = "trailer" if args.cut == "v1" else "trailer-" + args.cut
	audio = args.game / MUSIC
	if voice:
		mixed = mix_audio(args.game, voice, written / FPS, SITE / "build/audio/mix.wav", game_sound_for(EDIT))
		# As AAC: the encoder can then pass the video through instead of re-encoding it to fit a WAV.
		audio = mixed.with_suffix(".m4a")
		audio.unlink(missing_ok=True)
		subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "192000", str(mixed), str(audio)], check=True)
	subprocess.run([str(encode), "--frames", str(frames_dir), "--out", str(SITE / ("media/%s.mp4" % name)), "--fps", "30",
		"--bitrate", "6000000", "--audio", str(audio), "--fade", "2.5"], check=True)
	# The poster: the Fireball's frame.
	poster_at = 0
	for seg in EDIT:
		if seg.get("clip") == "fight_fireball":
			poster_at += round(0.55 * FPS)
			break
		poster_at += round(seg["seconds"] * FPS)
	Image.open(frames_dir / ("f%05d.jpg" % min(poster_at, written - 1))).save(SITE / ("media/%s-poster.jpg" % name), quality=86)
	print("make_trailer: media/%s.mp4 and media/%s-poster.jpg" % (name, name))


if __name__ == "__main__":
	main()
