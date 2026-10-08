#!/usr/bin/env python3
"""Fills the generated parts of index.html and the media the page uses.

  python3 tools/build.py [--raw <dir of PNG captures>] [--game ~/Documents/CurseOfStrahdGame] [--placeholders]

- Screenshots: each shot in SHOTS is read from <raw>/<name>.png and written as media/shots/<name>.webp (1920 wide)
  and media/thumbs/<name>.webp (640 wide). A shot with no capture yet keeps the file it has; with --placeholders, a
  dark card naming the shot is drawn in its place, so the layout can be checked before the captures exist.
- The gallery's buttons, from GALLERY, between <!-- gallery:start --> and <!-- gallery:end -->.
- The credits, from the game's art/credits.json (the lines its own Credits screen shows), between
  <!-- credits:start --> and <!-- credits:end -->, with the voices added.
- media/og.jpg (the link preview) and media/icon.png.
"""
import argparse
import hashlib
import html
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SITE = Path(__file__).resolve().parent.parent

# Every screenshot the page uses: name -> caption (also the image's alt text in the gallery).
SHOTS = {
	"hero": "Castle Ravenloft above the valley",
	"title": "The animated title screen",
	"village_night": "The Village of Barovia at night",
	"vallaki_rain": "Rain over Vallaki at dusk",
	"road_dusk": "The party on the misty road at dusk",
	"castle_vista": "The gates of Castle Ravenloft in a storm",
	"vallaki_noon": "Vallaki's square on a festival day",
	"lake_dusk": "Lake Zarovich at dusk",
	"krezk_snow": "Snow in the walled village of Krezk",
	"death_house": "Candlelight in a haunted house, its near walls cut away",
	"tser_pool_night": "Firelight and water at the Vistani camp by night",
	"combat_fireball": "A Fireball bursts among the foes",
	"combat_odds": "Hover a foe for the chance to hit, the damage and any Advantage",
	"combat_area": "An area spell shows who it will catch, and warns about an ally in the blast",
	"combat_battlefield": "Spirit Guardians and Hunger of Hadar lingering on the field",
	"combat_boss": "A boss fight, with its name plate and health bar",
	"dialogue_check": "Liriel speaks for the party, and the check shows her chance",
	"dialogue_d20": "Godrick rolls the d20, with the DC and every bonus",
	"cutscene": "Storybook: a rider watches from the ridge",
	"tarokka": "Storybook: Madam Eva lays out the Tarokka cards",
	"story_mists": "Storybook: the mists close in behind you",
	"story_village": "Storybook: rain over the Village of Barovia",
	"story_palisade": "Storybook: the palisade of Vallaki",
	"story_camp": "Storybook: a Vistani camp at Tser Pool",
	"stealth_sight": "Sneaking: the ground each guard can see",
	"party_roster": "Choosing four of the six companions",
	"character_sheet": "The character sheet, with a number's breakdown",
	"inventory": "The inventory's paper doll",
	"inventory_list": "The inventory in its list view",
	"creator_appearance": "Make your own hero: choosing their look",
	"dialogue_busts": "Kip at the inn, a bust on each side",
	"travel_map": "The travel map of Barovia",
	"skirmish": "Skirmish and the Character Lab",
}

# Shots that are the game's own storybook art (data/cutscenes), taken straight from the game's files.
ART = {
	"cutscene": "art/cutscenes/strahd_watcher_alone.jpg",
	"tarokka": "art/cutscenes/madam_eva_reading.jpg",
	"story_mists": "art/cutscenes/mists_arrival.jpg",
	"story_village": "art/cutscenes/village_rain.jpg",
	"story_palisade": "art/cutscenes/vallaki_palisade.jpg",
	"story_camp": "art/cutscenes/tser_pool_fire.jpg",
}

# The gallery, in order (the first is shown large).
GALLERY = ["combat_fireball", "village_night", "dialogue_busts", "vallaki_rain", "creator_appearance", "dialogue_check", "castle_vista", "combat_odds",
	"krezk_snow", "combat_area", "vallaki_noon", "death_house", "tarokka", "tser_pool_night", "stealth_sight", "combat_battlefield",
	"combat_boss", "lake_dusk", "party_roster", "character_sheet", "inventory_list", "travel_map", "skirmish", "road_dusk",
	"dialogue_d20", "title", "cutscene", "story_mists", "story_village", "story_palisade", "story_camp"]

INK = (12, 6, 7)
GILT = (226, 196, 117)
SERIF = "/System/Library/Fonts/Supplemental/Trattatello.ttf"


def font(size: int) -> ImageFont.FreeTypeFont:
	for path in [SERIF, "/System/Library/Fonts/Supplemental/Baskerville.ttc"]:
		try:
			return ImageFont.truetype(path, size)
		except OSError:
			pass
	return ImageFont.load_default()


def placeholder(name: str) -> Image.Image:
	img = Image.new("RGB", (1920, 1080), INK)
	d = ImageDraw.Draw(img)
	for i in range(0, 1080, 6):
		shade = int(18 + 22 * (1 - abs(540 - i) / 540))
		d.line([(0, i), (1920, i)], fill=(shade + 10, shade // 3, shade // 3 + 2), width=6)
	d.rectangle([40, 40, 1880, 1040], outline=(107, 79, 36), width=3)
	f = font(72)
	text = name.replace("_", " ")
	w = d.textlength(text, font=f)
	d.text(((1920 - w) / 2, 470), text, font=f, fill=GILT)
	f2 = font(40)
	sub = "screenshot to come"
	d.text(((1920 - d.textlength(sub, font=f2)) / 2, 580), sub, font=f2, fill=(179, 161, 133))
	return img


def write_shot(img: Image.Image, name: str) -> None:
	img = img.convert("RGB")
	full = img.copy()
	if full.width != 1920:
		full = full.resize((1920, round(full.height * 1920 / full.width)), Image.LANCZOS)
	(SITE / "media/shots").mkdir(parents=True, exist_ok=True)
	(SITE / "media/thumbs").mkdir(parents=True, exist_ok=True)
	full.save(SITE / f"media/shots/{name}.webp", quality=84, method=6)
	thumb = full.resize((640, round(full.height * 640 / full.width)), Image.LANCZOS)
	thumb.save(SITE / f"media/thumbs/{name}.webp", quality=80, method=6)


def replace_block(text: str, tag: str, body: str) -> str:
	pattern = re.compile(r"(<!-- %s:start -->)(.*?)(\s*<!-- %s:end -->)" % (tag, tag), re.S)
	indent = re.search(r"\n([ \t]*)<!-- %s:start -->" % tag, text).group(1)
	lines = "\n".join(indent + line for line in body.splitlines())
	return pattern.sub(lambda m: m.group(1) + "\n" + lines + m.group(3), text, count=1)


def gallery_html() -> str:
	out = []
	for name in GALLERY:
		cap = html.escape(SHOTS[name], quote=True)
		out.append(f'<button data-full="media/shots/{name}.webp" data-caption="{cap}">'
			f'<img src="media/thumbs/{name}.webp" alt="{cap}" loading="lazy"></button>')
	return "\n".join(out)


def linkify(line: str) -> str:
	text = html.escape(line)
	return re.sub(r"(https?://[^\s)]+[^\s).,])", r'<a href="\1" rel="noopener">\1</a>', text)


def credits_html(game: Path) -> str:
	data = json.loads((game / "art/credits.json").read_text())
	out = []
	for sec in data["sections"]:
		out.append(f"<h4>{html.escape(sec['title'])}</h4>")
		for line in sec["lines"]:
			out.append(f"<p>{linkify(line)}</p>")
		if sec["title"] == "Art":
			out.append("<h4>Voices</h4>")
			out.append("<p>The Narrator, the cast and the companions were voiced with ElevenLabs.</p>")
	return "\n".join(out)


def og_image() -> None:
	src = SITE / "media/shots/hero.webp"
	if not src.exists():
		return
	img = Image.open(src).convert("RGB").resize((1200, 675), Image.LANCZOS)
	shade = Image.new("RGBA", img.size, (0, 0, 0, 0))
	d = ImageDraw.Draw(shade)
	for y in range(675):
		d.line([(0, y), (1200, y)], fill=(12, 6, 7, int(150 * max(0, (y - 300) / 375))))
	img = Image.alpha_composite(img.convert("RGBA"), shade)
	d = ImageDraw.Draw(img)
	f = font(96)
	t = "Curse of Strahd"
	d.text(((1200 - d.textlength(t, font=f)) / 2, 470), t, font=f, fill=GILT)
	f2 = font(34)
	s = "An unofficial fan game"
	d.text(((1200 - d.textlength(s, font=f2)) / 2, 590), s, font=f2, fill=(240, 226, 192))
	img.convert("RGB").save(SITE / "media/og.jpg", quality=86)


def icon() -> None:
	img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
	d = ImageDraw.Draw(img)
	d.ellipse([8, 8, 248, 248], fill=(42, 12, 18, 255), outline=(176, 138, 62, 255), width=10)
	f = font(150)
	d.text((128, 136), "S", font=f, fill=GILT, anchor="mm")
	img.save(SITE / "media/icon.png")


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--raw", type=Path, help="folder of PNG captures named after the shots")
	ap.add_argument("--game", type=Path, default=Path.home() / "Documents/CurseOfStrahdGame")
	ap.add_argument("--placeholders", action="store_true")
	args = ap.parse_args()
	# The banner is the title screen's key art (art/ui/title_backdrop.png), at its own size.
	key_art = args.game / "art/ui/title_backdrop.png"
	if key_art.exists():
		Image.open(key_art).convert("RGB").save(SITE / "media/shots/hero.webp", quality=86, method=6)
	for name, rel in ART.items():
		if (args.game / rel).exists():
			write_shot(Image.open(args.game / rel), name)
			print("art", name)
	for name in SHOTS:
		if name == "hero" or name in ART:
			continue
		src = args.raw / f"{name}.png" if args.raw else None
		if src and src.exists():
			write_shot(Image.open(src), name)
			print("shot", name)
		elif args.placeholders and not (SITE / f"media/shots/{name}.webp").exists():
			write_shot(placeholder(name), name)
			print("placeholder", name)
	page = (SITE / "index.html").read_text()
	page = replace_block(page, "gallery", gallery_html())
	page = replace_block(page, "credits", credits_html(args.game))
	# The stylesheet and script carry a hash of their contents, so a browser never keeps an old copy.
	for rel in ("css/site.css", "js/site.js"):
		digest = hashlib.sha1((SITE / rel).read_bytes()).hexdigest()[:8]
		page = re.sub(r'%s\?v=[0-9a-z]+' % re.escape(rel), "%s?v=%s" % (rel, digest), page)
	(SITE / "index.html").write_text(page)
	og_image()
	print("index.html updated")


if __name__ == "__main__":
	main()
