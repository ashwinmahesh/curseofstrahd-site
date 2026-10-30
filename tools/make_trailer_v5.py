#!/usr/bin/env python3
"""Trailer v5 (owner, 2026-10-28): about 90 seconds on ISAo's "Dark Gothic Haunted Masquerade", cut on its marks, with
the party of Godrick, Ratatouille, Kip and Liriel in every shot, Strahd's narration over the quiet passages, and the
music at its full level from first note to last: nothing dips under a line or a blow. The plan is the vault note
"Trailer v5 Plan - 2026-10-28".

  /usr/bin/python3 tools/make_trailer_v5.py [--clips build/v5/raw/clips] [--only-frames] [--reuse-frames]

Clips come from tools/godot/trailer_world.gd and trailer_game.gd (tools/capture.py --mode clips; the game clips with
--movie for their sound, pulled out by tools/avi_audio.py into build/v5/audio/game_movie.wav). Writes build/v5/frames,
build/v5/audio/mix.wav, media/trailer-v5.mp4 and media/trailer-v5-poster.jpg.
"""
import argparse
import array
import audioop
import math
import shutil
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

import make_trailer as mt

SITE = mt.SITE
GAME = Path.home() / "Documents/CurseOfStrahdGame"
W, H, FPS, RATE = mt.W, mt.H, mt.FPS, mt.RATE
CINZEL = GAME / "addons/dnd_core/art/sourced/google_fonts/cinzel/Cinzel[wght].ttf"
BOOM = GAME / "addons/dnd_core/art/sourced/oga_boom_pack_dklon/boom%d.wav"
GOLD, PARCHMENT, RED = mt.GOLD, mt.PARCHMENT, (196, 38, 52)

# The music's marks: the opening swell (0-10 s), the quiet bed (10-26), the band in at 26.0, a lighter passage
# (46-58), the peak (58-76), the coda from 76 and the fade at 88.
BAND, PEAK, CODA = 26.0, 58.0, 76.0

# The cut. Each segment: a clip (folder under --clips) from "from" seconds, for "seconds"; "fade" dissolves in from the
# segment before over that many frames (hard cuts otherwise); "caption" words over it; "push" a slow zoom in toward
# the middle (1.0 = none), for the shots that hold.
TACTICS = "Turn-based tactics on the 2024 D&D rules"
EDIT = [
	# Cold open (owner, 2026-10-28: open on the most striking shot): the camera rises over the village to Castle
	# Ravenloft in the storm, then bats become Strahd beside the party.
	{"clip": "vista", "from": 0.2, "seconds": 4.4},
	{"clip": "strahd_road", "from": 0.2, "seconds": 3.4},
	# One walk through six outdoor places, a second each and each its own colour (owner, 2026-10-30), never its start
	# or its end: night-blue Barovia, white Krezk, green Berez, the Abbey's gold, the violet vineyard, the grey-blue lake.
	{"clip": "w_village", "from": 0.8, "seconds": 1.0, "caption": "The whole Curse of Strahd campaign"},
	{"clip": "w_krezk", "from": 0.8, "seconds": 1.0, "caption": "The whole Curse of Strahd campaign"},
	{"clip": "w_berez", "from": 0.8, "seconds": 1.0, "caption": "The whole Curse of Strahd campaign"},
	{"clip": "w_abbey", "from": 0.8, "seconds": 1.0},
	{"clip": "w_winery", "from": 0.8, "seconds": 1.0},
	{"clip": "w_lake", "from": 0.8, "seconds": 1.0},
	# His five interiors, each in its own light: Strahd's chapel, the Amber Temple's faceless god, Baba Lysaga's hut,
	# the Blue Water Inn and the Abbey's shrine. Then the walk stops at last, at the Vistani camp by Tser Pool.
	{"clip": "i_castle", "from": 0.8, "seconds": 1.2},
	{"clip": "i_amber_god", "from": 0.8, "seconds": 1.2},
	{"clip": "i_hut", "from": 0.8, "seconds": 1.2},
	{"clip": "i_inn", "from": 0.8, "seconds": 1.2},
	{"clip": "i_abbey", "from": 0.8, "seconds": 1.2},
	{"clip": "d_tser", "from": 0.2, "seconds": 1.4},
	# Madam Eva turns one card over the reading's picture, and Strahd answers her: the last words before the band.
	{"clip": "eva", "from": 0.2, "seconds": 4.8},
	# The band hits: the fight, each moment in a place of its own.
	# Over the fights only the big panels are gone; the odds, damage numbers and boss bars stay (owner, 2026-10-30).
	{"clip": "fight_smite", "from": 0.0, "seconds": 3.4, "caption": TACTICS},
	{"clip": "fight_aim", "from": 0.3, "seconds": 2.2, "caption": "Know the odds before you act", "caption_y": 120},
	{"clip": "fight_fireball", "from": 0.1, "seconds": 2.4},
	{"clip": "fight_blast", "from": 0.4, "seconds": 2.4},
	{"clip": "fight_guardians", "from": 0.3, "seconds": 2.6},
	{"clip": "fight_hadar", "from": 0.2, "seconds": 4.2},
	{"clip": "fight_last", "from": 0.3, "seconds": 2.8},
	# Izek in his room at the Baron's mansion (owner, 2026-10-30: a voice he picked himself): Kip's threat fails on the
	# big d20 and Izek answers, angry, in his own voice. Then into the castle's crypts and up to the dining hall.
	{"clip": "izek", "from": 2.0, "seconds": 8.4, "voices": True, "caption": "Every line voiced", "caption_at": 2.6,
		"top": True},
	{"clip": "sneak", "from": 1.0, "seconds": 1.6},
	{"clip": "hall", "from": 1.0, "seconds": 2.0},
	# The climax (owner, 2026-10-28: more exciting, nothing seen before, no walking): Strahd's entrance, the party's
	# biggest spells, the bosses, Strahd striking back and the Sunsword, the cuts quickening.
	{"clip": "boss_entrance", "from": 1.2, "seconds": 3.0, "sound": True},
	{"clip": "spell_flame", "from": 0.2, "seconds": 1.4, "sound": True},
	{"clip": "spell_bolt", "from": 0.1, "seconds": 1.8, "sound": True},
	{"clip": "boss_dragon", "from": 0.3, "seconds": 2.4, "sound": True},
	{"clip": "boss_lysaga", "from": 0.6, "seconds": 1.6, "sound": True},
	{"clip": "boss_strahd", "from": 0.4, "seconds": 2.0, "sound": True},
	{"clip": "castle_strike", "from": 0.2, "seconds": 2.2, "sound": True},
	{"clip": "sunsword", "from": 0.0, "seconds": 3.6, "sound": True},
	# The title over the game's own key art (owner: the homepage's picture, as in v4), then the button.
	{"title": True, "still": "art/ui/title_backdrop.png", "push": 1.05, "seconds": 11.0},
	{"clip": "camp", "from": 0.3, "seconds": 3.5, "push": 1.06},
]
# Every fight clip carries its own sound effects (the movie's sound, laid on top of the music).
FIGHT = ("fight_", "boss_", "spell_", "castle_strike", "sunsword", "strahd_road")

# Strahd's narration (build/voice/strahd_trailer_NN.mp3): (start, line). 04 and 07 are left out.
VOICE = [(0.4, "01"), (6.6, "02"), (11.0, "03"), (19.0, "05"), (21.4, "06"), (76.6, "08"), (87.6, "09")]

# Levels. The music plays at 1.0 throughout; the lines and sounds are set against it and laid on top.
VOICE_OVER_MUSIC_DB = 9.0   # each line's RMS this far above the music's around it
VOICE_MAX_RMS_DB = -10.0    # but never louder than this
VOICE_MIN_RMS_DB = -17.0    # nor quieter
SOUND_UNDER_MUSIC_DB = 4.0  # the fights' effects this far under the music's RMS around them
SOUND_PEAK = 0.32           # and their loudest moment no higher than this (about -10 dBFS)
VOICE_PEAK = 0.9            # a line's loudest moment no higher than this (about -1 dBFS before the trim)
GAME_VOICE_RMS_DB = -11.0   # the dinner's line, from the game's own clip
BOOMS = [(BAND - 0.05, 7, 0.55), (CODA - 0.05, 5, 0.6)]   # (start, boom pack clip, gain)
MASTER = 0.7                # one fixed trim on the whole mix (-3 dB, v4's own music level), the same from first frame
                            # to last, so the lines and blows fit on top of the music with the limiter barely touching it


# --- Pictures --------------------------------------------------------------------------------------------------------

def cinzel(size: int, weight: int = 600) -> ImageFont.FreeTypeFont:
	f = ImageFont.truetype(str(CINZEL), size)
	try:
		f.set_variation_by_axes([weight])
	except (OSError, AttributeError):
		pass
	return f


def spaced(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, track: float) -> float:
	return sum(d.textlength(ch, font=f) for ch in text) + track * (len(text) - 1)


def draw_spaced(d: ImageDraw.ImageDraw, x: float, y: float, text: str, f, fill, track: float) -> None:
	for ch in text:
		d.text((x, y), ch, font=f, fill=fill)
		x += d.textlength(ch, font=f) + track


def caption(img: Image.Image, text: str, alpha: float, y: float) -> Image.Image:
	"""Words in the game's Cinzel, upper case and spaced, gold with a soft shadow, over a faint dark band."""
	if alpha <= 0:
		return img
	text = text.upper()
	layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
	band = Image.new("L", (W, H), 0)
	ImageDraw.Draw(band).rectangle([0, y - 34, W, y + 92], fill=int(120 * alpha))
	band = band.filter(ImageFilter.GaussianBlur(34))
	layer = Image.composite(Image.new("RGBA", (W, H), (6, 2, 3, 255)), layer, band)
	d = ImageDraw.Draw(layer)
	f = cinzel(50, 700)
	track = 5.0
	x = (W - spaced(d, text, f, track)) / 2
	a = int(255 * alpha)
	shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
	draw_spaced(ImageDraw.Draw(shadow), x + 3, y + 3, text, f, (0, 0, 0, int(a * 0.9)), track)
	layer = Image.alpha_composite(layer, shadow.filter(ImageFilter.GaussianBlur(3)))
	draw_spaced(ImageDraw.Draw(layer), x, y, text, f, GOLD + (a,), track)
	return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def title_frames(base: list, n: int) -> list:
	"""The title over the castle: "CURSE OF STRAHD" eases in, its line under it, then the call to action."""
	out = []
	for i in range(n):
		t = i / FPS
		img = ImageEnhance.Brightness(base[i]).enhance(0.6).convert("RGBA")
		# A soft dark band behind the words, so the red title reads over the moon and the castle.
		img.alpha_composite(_title_band())
		layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
		d = ImageDraw.Draw(layer)

		def line(text: str, size: int, weight: int, y: float, colour: tuple, appear: float, track: float,
				gone: float = 99.0) -> None:
			a = max(0.0, min(1.0, (t - appear) / 0.7, (gone - t) / 0.5))
			if a <= 0:
				return
			f = cinzel(size, weight)
			x = (W - spaced(d, text, f, track)) / 2
			sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
			draw_spaced(ImageDraw.Draw(sh), x + 4, y + 5, text, f, (0, 0, 0, int(230 * a)), track)
			layer.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)))
			draw_spaced(d, x, y, text, f, colour + (int(255 * a),), track)

		# The title grows a little as it comes in (from 0.4 s); the line under it follows.
		line("CURSE OF STRAHD", 132 + int(8 * min(1.0, t / 6.0)), 800, 330, RED, 0.4, 14.0)
		line("BAROVIA HAS NO WAY OUT. ONLY THROUGH.", 40, 600, 520, GOLD, 1.6, 6.0, 5.6)
		line("FREE ON MAC AND WINDOWS", 54, 700, 520, PARCHMENT, 6.0, 8.0)
		line("CURSEOFSTRAHD.APP", 44, 600, 610, GOLD, 6.6, 8.0)
		line("AN UNOFFICIAL FAN GAME  ·  2024 D&D RULES", 26, 500, 720, PARCHMENT, 7.2, 5.0)
		img = Image.alpha_composite(img, layer).convert("RGB")
		out.append(img)
	return out


_BAND = None


def _title_band() -> Image.Image:
	global _BAND
	if _BAND is None:
		mask = Image.new("L", (W, H), 0)
		ImageDraw.Draw(mask).rectangle([0, 300, W, 780], fill=175)
		mask = mask.filter(ImageFilter.GaussianBlur(70))
		_BAND = Image.new("RGBA", (W, H), (8, 3, 5, 255))
		_BAND.putalpha(mask)
	return _BAND


def push(frames: list, k: float) -> list:
	out = []
	for i, f in enumerate(frames):
		z = 1.0 + (k - 1.0) * i / max(len(frames) - 1, 1)
		cw, ch = W / z, H / z
		box = ((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)
		out.append(f.crop(tuple(round(v) for v in box)).resize((W, H), Image.LANCZOS))
	return out


def render(clips: Path, out_dir: Path) -> int:
	shutil.rmtree(out_dir, ignore_errors=True)
	out_dir.mkdir(parents=True)
	written = 0
	at = 0.0
	tail: list = []
	for k, seg in enumerate(EDIT):
		n = round(seg["seconds"] * FPS)
		nxt = EDIT[k + 1] if k + 1 < len(EDIT) else None
		over = int(nxt.get("fade", 0)) if nxt else 0
		if "still" in seg:
			frames = mt.still_frames(GAME / seg["still"], n + over, float(seg.get("push", 1.0)))
		else:
			frames = mt.clip_frames(clips / seg["clip"], n + over, float(seg.get("from", 0.0)))
		if seg.get("title"):
			frames = title_frames(frames, n + over)
		if seg.get("push"):
			if "still" not in seg:
				frames = push(frames, float(seg["push"]))
		if "caption" in seg:
			prev = EDIT[k - 1] if k > 0 else None
			held_in = prev is not None and prev.get("caption") == seg["caption"]
			held_out = nxt is not None and nxt.get("caption") == seg["caption"]
			start = float(seg.get("caption_at", 0.0))
			# Over a fight the words sit low on the field, clear of the turn order, the log and the hotbar.
			y = 150 if seg.get("top") else (H - 370 if seg.get("hud") else H - 200)
			y = int(seg.get("caption_y", y))
			for i in range(n + over):
				t = i / FPS - start
				if t < 0:
					continue
				a = max(0.0, min(1.0, 1.0 if held_in else t / 0.35, 1.0 if held_out else (seg["seconds"] - start - t) / 0.35))
				frames[i] = caption(frames[i], seg["caption"], a, y)
		if k == 0:
			for i in range(min(6, n)):
				frames[i] = Image.blend(Image.new("RGB", (W, H)), frames[i], (i + 1) / 7)
		for i, prev in enumerate(tail):
			frames[i] = Image.blend(prev, frames[i], (i + 1) / (len(tail) + 1))
		tail = frames[n:]
		if nxt is None:
			# The last half second goes to black.
			for i in range(max(0, n - 15), n):
				frames[i] = Image.blend(frames[i], Image.new("RGB", (W, H)), (i - (n - 15) + 1) / 15)
		for img in frames[:n]:
			img.save(out_dir / ("f%05d.jpg" % written), quality=93)
			written += 1
		print("make_trailer_v5: %6.2f s  %s" % (at, seg.get("clip", seg.get("still"))))
		at += seg["seconds"]
	print("make_trailer_v5: %d frames, %.2f s" % (written, written / FPS))
	return written


# --- Sound -----------------------------------------------------------------------------------------------------------

def db(x: float) -> float:
	return 20 * math.log10(max(x, 1e-9))


def gain_of(d: float) -> float:
	return 10 ** (d / 20)


def biquad(samples: array.array, b0, b1, b2, a1, a2) -> array.array:
	out = array.array("f", bytes(4 * len(samples)))
	x1 = x2 = y1 = y2 = 0.0
	for i, x in enumerate(samples):
		y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
		x2, x1, y2, y1 = x1, x, y1, y
		out[i] = y
	return out


def highpass(s: array.array, f0: float, q: float = 0.707) -> array.array:
	w = 2 * math.pi * f0 / RATE
	al = math.sin(w) / (2 * q)
	c = math.cos(w)
	a0 = 1 + al
	return biquad(s, (1 + c) / 2 / a0, -(1 + c) / a0, (1 + c) / 2 / a0, -2 * c / a0, (1 - al) / a0)


def peak_eq(s: array.array, f0: float, gain_db: float, q: float = 1.0) -> array.array:
	A = 10 ** (gain_db / 40)
	w = 2 * math.pi * f0 / RATE
	al = math.sin(w) / (2 * q)
	c = math.cos(w)
	a0 = 1 + al / A
	return biquad(s, (1 + al * A) / a0, -2 * c / a0, (1 - al * A) / a0, -2 * c / a0, (1 - al / A) / a0)


def compress(s: array.array, threshold_db: float = -24.0, ratio: float = 3.0) -> array.array:
	"""A smooth RMS compressor (10 ms attack, 150 ms release) for the narration, so it holds an even level."""
	att = math.exp(-1 / (0.010 * RATE))
	rel = math.exp(-1 / (0.150 * RATE))
	env = 0.0
	out = array.array("f", bytes(4 * len(s)))
	for i, x in enumerate(s):
		p = x * x
		env = att * env + (1 - att) * p if p > env else rel * env + (1 - rel) * p
		lvl = 10 * math.log10(env + 1e-12)
		over = lvl - threshold_db
		g = 10 ** (-(over - over / ratio) / 20) if over > 0 else 1.0
		out[i] = x * g
	return out


def soft_limit(s: array.array, ceiling: float) -> array.array:
	"""A look-ahead peak limiter: in 1 ms blocks, the gain drops just before any peak that would pass `ceiling` and
	comes back over about 60 ms, so a voice's plosives and a blow's crack are held under it without distortion."""
	step = RATE // 1000
	n = (len(s) + step - 1) // step
	want = []
	for i in range(n):
		p = max(map(abs, s[i * step:(i + 1) * step]), default=0.0)
		want.append(min(1.0, ceiling / p) if p > 0 else 1.0)
	back = 1.0 - math.exp(-1.0 / 60.0)
	g = 1.0
	gains = []
	for i in range(n):
		target = min(want[i:i + 6])
		g = target if target < g else g + (target - g) * back
		gains.append(g)
	out = array.array("f", s)
	for i, x in enumerate(s):
		out[i] = x * gains[i // step]
	return out


def level(s: array.array, want_db: float, ceiling: float) -> array.array:
	"""`s` brought to `want_db` (its sounding parts' RMS) under `ceiling`: raised, its peaks held by the limiter, and
	raised again by what the limiter took, a few times over."""
	g = gain_of(want_db - db(active_rms(s)))
	out = s
	for _ in range(6):
		out = soft_limit(array.array("f", (v * g for v in s)), ceiling)
		short = want_db - db(active_rms(out))
		if short < 0.4:
			break
		g *= gain_of(min(short, 8.0))
	return out


def active_rms(s: array.array) -> float:
	"""The RMS of the parts that sound (50 ms windows within 30 dB of the loudest), not the pauses between."""
	step = RATE // 20
	wins = [rms(s, i, i + step) for i in range(0, len(s), step)]
	top = max(wins, default=0.0)
	loud = [w for w in wins if w > top * 0.0316]
	return math.sqrt(sum(w * w for w in loud) / max(len(loud), 1))


def mono_float(path: Path, tmp: Path) -> array.array:
	pcm = mt.to_wav(path, tmp, 1)
	a = array.array("h", pcm)
	return array.array("f", (v / 32768.0 for v in a))


def rms(s, a: int = 0, b: int = -1) -> float:
	b = len(s) if b < 0 else b
	seg = s[a:b]
	return math.sqrt(sum(v * v for v in seg) / max(len(seg), 1))


def voice_line(nn: str, tmp: Path) -> array.array:
	"""Strahd's line, cleaned and evened: rumble cut under 90 Hz, +3 dB of presence at 3 kHz, gently compressed."""
	s = mono_float(SITE / ("build/voice/strahd_trailer_%s.mp3" % nn), tmp / ("v%s.wav" % nn))
	s = highpass(s, 90.0)
	s = peak_eq(s, 3000.0, 3.0, 0.9)
	return compress(s)


def music_rms_db(music_l: array.array, music_r: array.array, at: float, seconds: float) -> float:
	a, b = int(at * RATE), int((at + seconds) * RATE)
	return db(math.sqrt((rms(music_l, a, b) ** 2 + rms(music_r, a, b) ** 2) / 2))


# The Movie Maker runs' sound and logs: a clip re-recorded later is in a later run, which wins.
GAME_SOUNDS = [("build/v5/audio/game_movie.wav", "build/v5/raw/clips/trailer_game.log"),
	("build/v5/audio/game_movie2.wav", "build/v5/raw/clips/trailer_game2.log"),
	("build/v5/audio/game_movie3.wav", "build/v5/raw/clips/trailer_game3.log")] + [
	# One run per fight moment in a place of its own (owner, 2026-10-28): the blast, the guardians, Hadar, the last blow.
	("build/v5/audio/game_movie%d.wav" % n, "build/v5/raw/clips/trailer_game%d.log" % n) for n in range(4, 31)]


def game_sound(edit: list) -> list:
	"""(start in the trailer, mono float samples, kind) for each fight clip's own sound and the dinner's voice. A clip
	recorded in parts (with frames between them left out) takes each part's sound from where that part was played."""
	runs = {}   # clip -> (wav, [(first frame in the clip, process frame of it), ...])
	for wav, log in GAME_SOUNDS:
		if not (SITE / wav).exists() or not (SITE / log).exists():
			continue
		seen = {}
		for line in (SITE / log).read_text().splitlines():
			if line.startswith("segment "):
				_, name, part, frame, _ = line.split()
				seen.setdefault(name, []).append((int(part), int(frame)))
		for name, parts in seen.items():
			runs[name] = (wav, sorted(parts))
	out = []
	cache = {}
	at = 0.0
	for seg in edit:
		name = seg.get("clip", "")
		if name in runs and (seg.get("voices") or seg.get("sound") or name.startswith(FIGHT)):
			wav, parts = runs[name]
			if wav not in cache:
				cache[wav] = _pcm(SITE / wav)
			pcm = cache[wav]
			f0 = int(round(float(seg.get("from", 0.0)) * FPS))
			n = int(round(seg["seconds"] * FPS))
			per = RATE // FPS
			piece = array.array("f")
			for f in range(f0, f0 + n):
				first, proc = parts[0]
				for p_first, p_proc in parts:
					if p_first <= f:
						first, proc = p_first, p_proc
				a = int((proc + (f - first) + mt.SOUND_LAG) / FPS * RATE)
				piece.extend(v / 32768.0 for v in pcm[a:a + per])
			out.append((at, piece, "voice" if seg.get("voices") else "sound"))
		at += seg["seconds"]
	return out


def _pcm(src: Path) -> array.array:
	"""A Movie Maker run's sound as mono 16-bit samples at the mix's rate."""
	with wave.open(str(src)) as w:
		rate, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
		pcm = w.readframes(w.getnframes())
	if width != 2:
		pcm = audioop.lin2lin(pcm, width, 2)
	if ch == 2:
		pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
	if rate != RATE:
		pcm, _ = audioop.ratecv(pcm, 2, 1, rate, RATE, None)
	return array.array("h", pcm)


def mix(seconds: float, out: Path) -> Path:
	tmp = SITE / "build/v5/audio"
	tmp.mkdir(parents=True, exist_ok=True)
	total = int(seconds * RATE)
	music = array.array("h", mt.to_wav(GAME / mt.MUSIC, tmp / "music.wav", 2))
	ml = array.array("f", (music[i] / 32768.0 for i in range(0, len(music), 2)))
	mr = array.array("f", (music[i] / 32768.0 for i in range(1, len(music), 2)))
	pad = max(0, total - len(ml))
	ml.extend([0.0] * pad)
	mr.extend([0.0] * pad)
	del ml[total:]
	del mr[total:]
	# What goes on top, centred: the narration, the game's sound and the two impacts.
	top = array.array("f", bytes(4 * total))

	def lay(at: float, s: array.array, g: float) -> None:
		a = int(at * RATE)
		for i in range(min(len(s), total - a)):
			top[a + i] += s[i] * g

	for at, nn in VOICE:
		s = voice_line(nn, tmp)
		local = music_rms_db(ml, mr, at, len(s) / RATE)
		want = min(VOICE_MAX_RMS_DB, max(VOICE_MIN_RMS_DB, local + VOICE_OVER_MUSIC_DB))
		s = level(s, want, VOICE_PEAK)
		lay(at, s, 1.0)
		print("make_trailer_v5: line %s at %5.1f s, music %5.1f dB, line %5.1f dB (peak %.2f)" % (nn, at, local,
			db(active_rms(s)), max(map(abs, s))))
	for at, s, kind in game_sound(EDIT):
		if rms(s) < 1e-4:
			continue
		local = music_rms_db(ml, mr, at, len(s) / RATE)
		if kind == "voice":
			s = compress(peak_eq(highpass(s, 90.0), 3000.0, 3.0, 0.9))
			want, top_peak = GAME_VOICE_RMS_DB, VOICE_PEAK
		else:
			want, top_peak = local - SOUND_UNDER_MUSIC_DB, SOUND_PEAK
		s = level(s, want, top_peak)
		lay(at, s, 1.0)
		print("make_trailer_v5: %s at %5.1f s, music %5.1f dB, set to %5.1f dB (peak %.2f)" % (kind, at, local,
			db(active_rms(s)), max(map(abs, s))))
	for at, k, g in BOOMS:
		s = mono_float(Path(str(BOOM) % k), tmp / ("boom%d.wav" % k))
		lay(at, s, g)
	# The sum, one fixed trim, then a limiter that only touches the peaks that would still pass -1 dBFS.
	ceiling = gain_of(-1.0)
	left = array.array("f", ((ml[i] + top[i]) * MASTER for i in range(total)))
	right = array.array("f", ((mr[i] + top[i]) * MASTER for i in range(total)))
	step = RATE // 200
	gains = []
	for i in range(0, total, step):
		p = max(max(map(abs, left[i:i + step]), default=0.0), max(map(abs, right[i:i + step]), default=0.0))
		gains.append(min(1.0, ceiling / p) if p > 0 else 1.0)
	smooth = []
	g = 1.0
	for i in range(len(gains)):
		want = min(gains[i:i + 2])
		g = want if want < g else min(want, g + 1.0 / 40)
		smooth.append(g)
	pcm = array.array("h", bytes(4 * total))
	for i in range(total):
		gg = smooth[i // step]
		pcm[2 * i] = max(-32767, min(32767, int(left[i] * gg * 32767)))
		pcm[2 * i + 1] = max(-32767, min(32767, int(right[i] * gg * 32767)))
	low = [x for x in smooth if x < 0.999]
	print("make_trailer_v5: limiter touched %.2f s, at most %.1f dB" % (len(low) * step / RATE, db(min(smooth))))
	with wave.open(str(out), "wb") as w:
		w.setnchannels(2)
		w.setsampwidth(2)
		w.setframerate(RATE)
		w.writeframes(pcm.tobytes())
	return out


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--clips", type=Path, default=SITE / "build/v5/raw/clips")
	ap.add_argument("--only-frames", action="store_true")
	ap.add_argument("--reuse-frames", action="store_true")
	ap.add_argument("--only-audio", action="store_true")
	args = ap.parse_args()
	frames_dir = SITE / "build/v5/frames"
	if args.reuse_frames or args.only_audio:
		written = len(list(frames_dir.glob("f*.jpg")))
	else:
		written = render(args.clips, frames_dir)
	if args.only_frames:
		return
	mixed = mix(written / FPS, SITE / "build/v5/audio/mix.wav")
	if args.only_audio:
		return
	audio = mixed.with_suffix(".m4a")
	audio.unlink(missing_ok=True)
	subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "256000", str(mixed), str(audio)], check=True)
	encode = SITE / "build/encode"
	if not encode.exists():
		subprocess.run(["swiftc", "-O", str(SITE / "tools/encode.swift"), "-o", str(encode)], check=True)
	subprocess.run([str(encode), "--frames", str(frames_dir), "--out", str(SITE / "media/trailer-v5.mp4"), "--fps", "30",
		"--bitrate", "14000000", "--audio", str(audio), "--fade", "0.5"], check=True)
	# The poster: Ratatouille's Fireball bursting.
	at = 0
	for seg in EDIT:
		if seg.get("clip") == "fight_fireball":
			at += round(0.8 * FPS)
			break
		at += round(seg["seconds"] * FPS)
	Image.open(frames_dir / ("f%05d.jpg" % min(at, written - 1))).save(SITE / "media/trailer-v5-poster.jpg", quality=88)
	print("make_trailer_v5: media/trailer-v5.mp4 and media/trailer-v5-poster.jpg")


if __name__ == "__main__":
	main()
