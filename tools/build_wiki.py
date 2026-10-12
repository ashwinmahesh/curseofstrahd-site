#!/usr/bin/env python3
"""The game wiki at curseofstrahd.app/wiki/ (owner, 2026-10-12: a full wiki, kept up to date), from the vault's Wiki/
folder, which the game's wiki lane regenerates after each landing:

  /usr/bin/python3 tools/build_wiki.py [--src <vault>/CurseOfStrahd/Wiki] [--out wiki]

Each Markdown page becomes wiki/<section>/<page>.html in the site's look (site.css, wiki.css), with the site's nav, a
breadcrumb, a title search over every page (wiki/search.json, wiki/wiki.js), and the legal block and credit in the
footer. Obsidian's markup is read the way Obsidian shows it: [[links]] (with #headings and |labels) resolve to pages,
![[pictures]] become compressed WebPs under wiki/img/ (maps stay SVG), callouts, tables, nested lists, tasks, and
single line breaks kept; %% comments %% and front matter are dropped. A link to a note outside the wiki becomes plain
text. Pictures are converted only when their source is newer, and pages and pictures the source no longer has are
removed, so a rebuild after each regeneration is quick. The wiki is all spoilers: its front page says so first, and
nothing else on the site links into it except the nav's "Wiki (spoilers)".
"""
import argparse
import datetime
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

from PIL import Image

SITE = Path(__file__).resolve().parent.parent
SITE_URL = "https://curseofstrahd.app"
SRC = Path.home() / "Documents/Obsidian Vault/CurseOfStrahd/Wiki"
PICTURE_WIDTH = 1280
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
CALLOUT_ICONS = {"warning": "⚠", "danger": "⚠", "caution": "⚠", "info": "✦", "note": "✦", "tip": "✧", "example": "✦",
	"quote": "❝", "success": "✓", "question": "?", "abstract": "✦", "summary": "✦", "todo": "☐", "bug": "✗"}
THUMB_WIDTH = 480
RARITIES = ("common", "uncommon", "rare", "very rare", "legendary", "artifact")
# The front page's sections, each headed by one of the main site's screenshots (media/thumbs).
HOME_ART = {"walkthroughs": "story_mists", "the-world": "travel_map", "items-and-money": "inventory",
	"heroes-and-magic": "party_roster", "rules-and-play": "combat_odds"}


def slug(text: str) -> str:
	text = text.lower().replace("&", " and ").replace("'", "").replace("’", "")
	return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "page"


def front_matter(text: str) -> dict:
	"""The page's front matter (wiki, type, region, level, image, summary...) as plain strings."""
	m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
	meta = {}
	for line in (m.group(1).split("\n") if m else []):
		kv = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
		if kv:
			v = kv.group(2).strip()
			if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
				v = v[1:-1].replace('\\"', '"')
			meta[kv.group(1)] = v
	return meta


def rarity_class(rarity: str) -> str:
	return "r-" + rarity.replace(" ", "-")


# --- Pages and links -------------------------------------------------------------------------------------------------

class Wiki:
	def __init__(self, src: Path, out: Path):
		self.src = src
		self.out = out
		self.pages = {}       # "Wiki/Quests/Black Roses" -> {"path", "url", "title", "section"}
		self.lookup = {}      # lowercased keys (full, without Wiki/, file name) -> page key
		self.images = {}      # "Wiki/images/shots/x.jpg" -> (source path, url)
		self.missing = {}     # unresolved link targets -> count
		for md in sorted(src.rglob("*.md")):
			rel = md.relative_to(src)
			if any(part.startswith(".") for part in rel.parts):
				continue
			key = "Wiki/" + rel.with_suffix("").as_posix()
			parts = [slug(p) for p in rel.with_suffix("").parts]
			url = "/wiki/" if key == "Wiki/Home" else "/wiki/" + "/".join(parts) + ".html"
			self.pages[key] = {"path": md, "url": url, "title": rel.stem, "section": rel.parts[0] if len(rel.parts) > 1 else ""}
		names = {}
		for key in self.pages:
			names.setdefault(key.rsplit("/", 1)[-1].lower(), []).append(key)
		for key in self.pages:
			self.lookup[key.lower()] = key
			self.lookup[key[len("Wiki/"):].lower()] = key
		for name, keys in names.items():
			if len(keys) == 1:
				self.lookup.setdefault(name, keys[0])
		for f in sorted(src.rglob("*")):
			if f.suffix.lower() in IMAGE_EXT and not any(p.startswith(".") for p in f.relative_to(src).parts):
				rel = f.relative_to(src).as_posix()
				name = Path(rel[len("images/"):] if rel.startswith("images/") else rel)
				ext = ".svg" if f.suffix.lower() == ".svg" else ".webp"
				self.images["Wiki/" + rel] = (f, "/wiki/img/" + "/".join([slug(p) for p in name.parent.parts]
					+ [slug(name.stem) + ext]))
		self.image_names = {}
		for key, v in self.images.items():
			self.image_names.setdefault(key.rsplit("/", 1)[-1].lower(), key)
		# Each page's front matter, the pages by their wiki key (region/vallaki), and each listed item's rarity, so a
		# link to an item can wear its rarity's colour.
		self.by_wiki_key = {}
		self.rarity = {}      # (page key, heading slug) -> "very rare"
		self.thumbs = {}      # "/wiki/img/thumbs/..." -> source picture
		for key, info in self.pages.items():
			text = info["path"].read_text(encoding="utf-8")
			info["meta"] = front_matter(text)
			if info["meta"].get("wiki"):
				self.by_wiki_key[info["meta"]["wiki"]] = key
			if info["meta"].get("type") == "item-list":
				for name, line in re.findall(r"^###\s+(.+?)\s*\n+\*([^*\n]+)\*", text, re.M):
					rarity = line.split(",")[0].strip().lower()
					if rarity in RARITIES:
						self.rarity[(key, slug(name))] = rarity

	def page(self, target: str):
		t = target.strip().removesuffix(".md").lower()
		return self.lookup.get(t)

	def image(self, target: str):
		t = target.strip()
		if t in self.images:
			return self.images[t]
		if ("Wiki/" + t) in self.images:
			return self.images["Wiki/" + t]
		key = self.image_names.get(t.rsplit("/", 1)[-1].lower())
		return self.images[key] if key else None

	def thumb(self, target: str):
		"""A small copy of a picture for cards and table rows (written by build), or None."""
		pic = self.image(target)
		if not pic or pic[1].endswith(".svg"):
			return None
		url = "/wiki/img/thumbs/" + pic[1][len("/wiki/img/"):]
		self.thumbs[url] = pic[0]
		return url

	def page_image(self, key: str):
		"""The page's own picture (relative to Wiki/), from its front matter. For a place, its view from above when
		there is one, since the arrival shot has the game's interface over it."""
		meta = self.pages[key].get("meta", {})
		image = meta.get("image")
		if image and meta.get("type") == "location":
			over = re.sub(r"_\d+(\.\w+)$", r"_overview\1", image)
			if over != image and self.image("Wiki/" + over):
				return over
		return image

	def page_pic(self, key: str):
		"""(thumbnail, is a portrait) for a page's own picture, or (None, False)."""
		image = self.page_image(key)
		if not image:
			return None, False
		return self.thumb("Wiki/" + image), "/portraits/" in "/" + image

	def region(self, rid: str):
		"""(name, url) of a region id from the front matter; the url is None when the region has no page."""
		key = self.by_wiki_key.get("region/" + rid)
		if key:
			return self.pages[key]["title"], self.pages[key]["url"]
		return rid.replace("_", " ").strip().title(), None


# --- Inline markup ---------------------------------------------------------------------------------------------------

class Inline:
	def __init__(self, wiki: Wiki, here: str):
		self.wiki = wiki
		self.here = here

	def render(self, text: str) -> str:
		held = []

		def hold(s: str) -> str:
			held.append(s)
			return "\x00%d\x00" % (len(held) - 1)

		text = re.sub(r"`([^`]+)`", lambda m: hold("<code>%s</code>" % html.escape(m.group(1))), text)
		text = re.sub(r"!\[\[([^\]]+)\]\]", lambda m: hold(self.embed(m.group(1))), text)
		text = re.sub(r"\[\[([^\]]+)\]\]", lambda m: hold(self.link(m.group(1))), text)
		text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
			lambda m: hold('<a href="%s" rel="noopener">%s</a>' % (html.escape(m.group(2)), html.escape(m.group(1)))), text)
		text = html.escape(text, quote=False)
		# A check's difficulty reads as a chip: "Insight DC 15".
		text = re.sub(r"\bDC (\d+)\b", r'<span class="wiki-dc">DC&nbsp;\1</span>', text)
		text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
		text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
		text = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"<em>\1</em>", text)
		text = re.sub(r"==(.+?)==", r"<mark>\1</mark>", text)
		text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)
		while "\x00" in text:
			text = re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], text)
		return text

	def link(self, inner: str) -> str:
		target, _, label = inner.partition("|")
		target, _, heading = target.partition("#")
		shown = label or heading or target.rsplit("/", 1)[-1]
		if not target:   # a heading on this page
			return '<a href="#%s">%s</a>' % (slug(heading), html.escape(shown))
		key = self.wiki.page(target)
		if key is None:
			if self.wiki.image(target):
				return self.embed(inner)
			self.wiki.missing[target] = self.wiki.missing.get(target, 0) + 1
			return '<span class="wl-plain">%s</span>' % html.escape(shown)
		url = self.wiki.pages[key]["url"] + ("#" + slug(heading.lstrip("^")) if heading else "")
		rarity = self.wiki.rarity.get((key, slug(heading.lstrip("^")))) if heading else None
		cls = ' class="%s"' % rarity_class(rarity) if rarity else ""
		return '<a href="%s"%s>%s</a>' % (html.escape(url), cls, html.escape(shown))

	def embed(self, inner: str) -> str:
		target, _, size = inner.partition("|")
		pic = self.wiki.image(target)
		if pic is None:
			key = self.wiki.page(target.partition("#")[0])
			if key:
				return self.link(inner)
			self.wiki.missing[target] = self.wiki.missing.get(target, 0) + 1
			return ""
		width = ' style="max-width: %dpx"' % int(size) if size.strip().isdigit() else ""
		alt = Path(target).stem.replace("_", " ")
		return '<img class="wiki-pic" src="%s" alt="%s" loading="lazy" decoding="async"%s>' % (pic[1], html.escape(alt), width)


# --- Blocks ----------------------------------------------------------------------------------------------------------

LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def indent_of(line: str) -> int:
	return len(line) - len(line.lstrip(" \t").replace("\t", "    ")) if line.strip() else 10 ** 6


def dedent(lines: list, n: int) -> list:
	out = []
	for line in lines:
		line = line.replace("\t", "    ")
		out.append(line[n:] if line[:n].strip() == "" else line.lstrip())
	return out


class Blocks:
	def __init__(self, inline: Inline):
		self.inline = inline
		self.ids = {}
		self.headings = []

	def render(self, lines: list) -> str:
		out = []
		i = 0
		while i < len(lines):
			line = lines[i]
			s = line.strip()
			if not s:
				i += 1
				continue
			if s.startswith("```"):
				j = i + 1
				while j < len(lines) and not lines[j].strip().startswith("```"):
					j += 1
				out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(lines[i + 1:j])))
				i = j + 1
				continue
			m = re.match(r"^(#{1,6})\s+(.*?)\s*#*$", s)
			if m:
				out.append(self.heading(len(m.group(1)), m.group(2)))
				i += 1
				continue
			if re.match(r"^(-{3,}|\*{3,}|_{3,})$", s):
				out.append("<hr>")
				i += 1
				continue
			if s.startswith(">"):
				j = i
				while j < len(lines) and lines[j].strip().startswith(">"):
					j += 1
				out.append(self.quote(lines[i:j]))
				i = j
				continue
			if s.startswith("|") and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1]):
				j = i + 2
				while j < len(lines) and lines[j].strip().startswith("|"):
					j += 1
				out.append(self.table(lines[i], lines[i + 1], lines[i + 2:j]))
				i = j
				continue
			if LIST_RE.match(line):
				j = self.list_end(lines, i)
				out.append(self.list(lines[i:j]))
				i = j
				continue
			j = i
			para = []
			while j < len(lines) and lines[j].strip() and not self.starts_block(lines, j):
				para.append(lines[j].strip())
				j += 1
			if not para:   # a line that looks like a block start but isn't one (a lone "|"): keep it as text
				para, j = [s], i + 1
			out.append("<p>%s</p>" % "<br>\n".join(self.inline.render(p) for p in para))
			i = j
		return "\n".join(out)

	def starts_block(self, lines: list, j: int) -> bool:
		s = lines[j].strip()
		return (s.startswith(("#", ">", "```")) and (not s.startswith("#") or re.match(r"^#{1,6}\s", s) is not None)) \
			or LIST_RE.match(lines[j]) is not None \
			or (s.startswith("|") and j + 1 < len(lines) and TABLE_SEP.match(lines[j + 1]) is not None)

	def heading(self, level: int, text: str) -> str:
		base = slug(re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", text))
		n = self.ids.get(base, 0)
		self.ids[base] = n + 1
		hid = base if n == 0 else "%s-%d" % (base, n)
		if level in (2, 3):
			self.headings.append((level, hid, html.unescape(re.sub(r"<[^>]+>", "", self.inline.render(text)))))
		return '<h%d id="%s">%s</h%d>' % (level, hid, self.inline.render(text), level)

	def quote(self, lines: list) -> str:
		body = [re.sub(r"^\s*> ?", "", l) for l in lines]
		m = re.match(r"^\[!(\w+)\]([+-]?)\s*(.*)$", body[0].strip()) if body else None
		if not m:
			return "<blockquote>%s</blockquote>" % self.render(body)
		kind, fold, title = m.group(1).lower(), m.group(2), m.group(3) or m.group(1).capitalize()
		if kind == "infobox":
			return self.infobox(body[1:])
		icon = CALLOUT_ICONS.get(kind, "✦")
		inner = self.render(body[1:])
		head = '<span class="callout-icon" aria-hidden="true">%s</span>%s' % (icon, self.inline.render(title))
		if fold:
			return '<details class="callout callout-%s"%s><summary class="callout-title">%s</summary>%s</details>' % (
				kind, " open" if fold == "+" else "", head, inner)
		return '<div class="callout callout-%s"><p class="callout-title">%s</p>%s</div>' % (kind, head, inner)

	def infobox(self, lines: list) -> str:
		"""> [!infobox]: the page's picture, then **Label:** value lines, as a box beside the text."""
		pics, rows, rest = [], [], []
		for line in lines:
			s = line.strip()
			if not s:
				continue
			field = re.match(r"^\*\*(.+?):\*\*\s*(.*)$", s)
			if re.fullmatch(r"!\[\[[^\]]+\]\]", s) and not rows:
				pics.append(self.inline.render(s))
			elif field:
				rows.append("<dt>%s</dt><dd>%s</dd>" % (self.inline.render(field.group(1)), self.inline.render(field.group(2))))
			else:
				rest.append(s)
		parts = ['<aside class="wiki-infobox">']
		parts += ['<div class="wiki-infobox-pic">%s</div>' % p for p in pics if p]
		if rows:
			parts.append("<dl>%s</dl>" % "".join(rows))
		if rest:
			parts.append(self.render(rest))
		parts.append("</aside>")
		return "".join(parts)

	def cells(self, row: str) -> list:
		row = row.strip()
		if row.startswith("|"):
			row = row[1:]
		if row.endswith("|") and not row.endswith("\\|"):
			row = row[:-1]
		# A pipe splits cells unless it's escaped or inside a [[link|label]], as Obsidian reads it.
		cells, cur, depth, k = [], "", 0, 0
		while k < len(row):
			if row.startswith("[[", k):
				depth += 1
				cur += "[["
				k += 2
				continue
			if row.startswith("]]", k) and depth:
				depth -= 1
				cur += "]]"
				k += 2
				continue
			ch = row[k]
			if ch == "\\" and row[k + 1:k + 2] == "|":
				cur += "|"
				k += 2
				continue
			if ch == "|" and not depth:
				cells.append(cur.strip())
				cur = ""
			else:
				cur += ch
			k += 1
		cells.append(cur.strip())
		return cells

	def table(self, head: str, sep: str, rows: list) -> str:
		aligns = []
		for c in self.cells(sep):
			aligns.append("center" if c.startswith(":") and c.endswith(":") else "right" if c.endswith(":") else "")
		def row_html(cells, tag):
			shown = [self.inline.render(c) for c in cells]
			if tag == "td":
				# The first cell that's only a link to a page with a picture gets that picture as a thumbnail.
				for k, c in enumerate(cells):
					m = re.fullmatch(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]", c.strip())
					key = self.inline.wiki.page(m.group(1)) if m else None
					if key:
						pic, portrait = self.inline.wiki.page_pic(key)
						if pic:
							shown[k] = ('<span class="wiki-with-thumb"><img class="wiki-thumb%s" src="%s" alt="" loading="lazy" '
								'decoding="async"><span>%s</span></span>') % (" is-portrait" if portrait else "", pic, shown[k])
						break
			return "<tr>%s</tr>" % "".join('<%s%s>%s</%s>' % (tag, ' style="text-align:%s"' % aligns[k]
				if k < len(aligns) and aligns[k] else "", shown[k], tag) for k in range(len(cells)))
		body = "\n".join(row_html(self.cells(r), "td") for r in rows)
		return '<div class="wiki-table"><table><thead>%s</thead><tbody>\n%s\n</tbody></table></div>' % (
			row_html(self.cells(head), "th"), body)

	def list_end(self, lines: list, i: int) -> int:
		"""Where the list starting at line i ends: at a blank line not followed by more of it, or at a less-indented
		line that isn't an item."""
		base = indent_of(lines[i])
		j = i + 1
		while j < len(lines):
			l = lines[j]
			if not l.strip():
				k = j + 1
				while k < len(lines) and not lines[k].strip():
					k += 1
				if k < len(lines) and (indent_of(lines[k]) > base or (LIST_RE.match(lines[k]) and indent_of(lines[k]) == base)):
					j = k
					continue
				return j
			if indent_of(l) < base or (indent_of(l) == base and not LIST_RE.match(l)):
				return j
			j += 1
		return j

	def cards(self, items: list, ordered: bool):
		"""On the index pages, a list whose every entry is a page link and a line about it ("[[Place]]: what it is"),
		most of them pages with pictures, as picture cards. None when the list isn't one."""
		wiki = self.inline.wiki
		meta = wiki.pages.get(self.inline.here, {}).get("meta", {})
		if "index" not in meta.get("tags", "") or any(len([l for l in item if l.strip()]) != 1 for item in items):
			return None
		rows = []
		for item in items:
			text = LIST_RE.match(item[0]).group(3)
			m = re.match(r"^\[\[([^\]|#]+)(?:\|([^\]]+))?\]\](.*)$", text)
			key = wiki.page(m.group(1)) if m else None
			if not key:
				return None
			rows.append((key, m.group(2) or wiki.pages[key]["title"], m.group(3).strip()))
		pics = [wiki.page_pic(key) for key, _, _ in rows]
		if sum(1 for p, _ in pics if p) * 10 < len(rows) * 6:
			return None
		out = []
		for (key, label, rest), (pic, portrait) in zip(rows, pics):
			url = html.escape(wiki.pages[key]["url"])
			note, desc = "", rest
			m = re.match(r"^\(([^)]*(?:\([^)]*\)[^)]*)*)\)\s*:?\s*(.*)$", rest)
			if m:
				note, desc = m.group(1), m.group(2)
			elif rest.startswith(":"):
				desc = rest[1:].strip()
			li = ['<li class="wiki-card%s">' % ("" if pic else " no-pic")]
			if pic:
				li.append('<a class="wiki-card-pic" href="%s" tabindex="-1" aria-hidden="true"><img src="%s" alt="" '
					'loading="lazy" decoding="async"%s></a>' % (url, pic, ' class="is-portrait"' if portrait else ""))
			li.append('<div class="wiki-card-text"><a class="wiki-card-title" href="%s">%s</a>' % (url, html.escape(label)))
			if note:
				li.append('<p class="wiki-card-note">%s</p>' % self.inline.render(note))
			if desc:
				li.append('<p class="wiki-card-desc">%s</p>' % self.inline.render(desc))
			li.append("</div></li>")
			out.append("".join(li))
		tag = "ol" if ordered else "ul"
		return '<%s class="wiki-cards">\n%s\n</%s>' % (tag, "\n".join(out), tag)

	def list(self, lines: list) -> str:
		base = indent_of(lines[0])
		ordered = re.match(r"\d", LIST_RE.match(lines[0]).group(2)) is not None
		items = []
		for line in lines:
			m = LIST_RE.match(line)
			if m and indent_of(line) == base:
				items.append([line])
			else:
				items[-1].append(line)
		cards = self.cards(items, ordered)
		if cards:
			return cards
		out = []
		start = ""
		if ordered:
			first = int(re.match(r"\d+", LIST_RE.match(lines[0]).group(2)).group(0))
			start = ' start="%d" style="counter-reset: step %d"' % (first, first - 1) if first != 1 else ""
		for item in items:
			m = LIST_RE.match(item[0])
			text = m.group(3)
			pad = len(item[0].replace("\t", "    ")) - len(item[0].lstrip()) + len(m.group(2)) + 1
			task = re.match(r"^\[([ xX])\]\s+(.*)$", text)
			cls = prefix = ""
			if task:
				done = task.group(1).lower() == "x"
				prefix = '<span class="task-box" aria-hidden="true">%s</span>' % ("☑" if done else "☐")
				text = task.group(2)
				cls = ' class="task%s"' % (" done" if done else "")
			rest = dedent(item[1:], pad)
			first_line = prefix + self.inline.render(text)
			# Lines right under the item's text that aren't blocks continue its paragraph, on new lines.
			cont = []
			while rest and rest[0].strip() and not self.starts_block(rest, 0):
				cont.append(self.inline.render(rest.pop(0).strip()))
			inner = "<br>\n".join([first_line] + cont)
			sub = self.render(rest) if any(l.strip() for l in rest) else ""
			out.append("<li%s>%s%s</li>" % (cls, inner, "\n" + sub if sub else ""))
		tag = "ol" if ordered else "ul"
		return "<%s%s>\n%s\n</%s>" % (tag, start, "\n".join(out), tag)


# --- Pages -----------------------------------------------------------------------------------------------------------

def clean(text: str) -> str:
	text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
	text = re.sub(r"%%.*?%%", "", text, flags=re.S)
	return text


def stamp(path: Path) -> str:
	return hashlib.sha1(path.read_bytes()).hexdigest()[:8] if path.exists() else "0"


def plain(html_text: str) -> str:
	return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", html_text))).strip()


NAV = """<header class="nav is-solid" id="nav">
  <a class="nav-brand" href="/" aria-label="Curse of Strahd, the home page">
    <span class="nav-mark" aria-hidden="true">✠</span><span>Curse of Strahd</span>
  </a>
  <button class="nav-toggle" id="nav-toggle" aria-expanded="false" aria-controls="nav-links">
    <span class="sr">Menu</span><span aria-hidden="true">☰</span>
  </button>
  <nav class="nav-links" id="nav-links" aria-label="Sections">
    <a href="/#features">Features</a>
    <a href="/#companions">Companions</a>
    <a href="/#gallery">Gallery</a>
    <a href="/#faq">FAQ</a>
    <a href="/wiki/" aria-current="page">Wiki (spoilers)</a>
    <a class="nav-cta" href="/#download">Download</a>
  </nav>
</header>"""

FOOTER = """<footer class="footer">
  <div class="wrap">
    <div class="foot-top">
      <a class="nav-brand" href="/"><span class="nav-mark" aria-hidden="true">✠</span><span>Curse of Strahd</span></a>
      <p class="foot-tag">An unofficial fan game. Game created by Ashwin Mahesh.</p>
    </div>
    <div class="legal">
      <p><strong>This website is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed
        by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast
        LLC.</strong></p>
      <p>The game shown here is an unofficial, free, non-commercial fan project made by one fan. It is not made,
        approved, endorsed or sponsored by Wizards of the Coast LLC or Hasbro, Inc., and it is not affiliated with
        them in any way. It is not for sale and never will be. <em>Dungeons &amp; Dragons</em>, <em>D&amp;D</em>,
        <em>Curse of Strahd</em> and <em>Ravenloft</em> are trademarks of Wizards of the Coast LLC, and the
        characters, places and story of <em>Curse of Strahd</em> are their property; they are named here only to
        say what the game is based on, with no claim of ownership. The game includes material from the System
        Reference Document 5.2.1 by Wizards of the Coast LLC, used under the Creative Commons Attribution 4.0
        licence.</p>
      <p>The game's code is on <a href="https://github.com/ashwinmahesh/CurseOfStrahd" rel="noopener">GitHub</a>.
        Rights holders with a concern can open an issue there.</p>
    </div>
  </div>
</footer>"""

SPOILER_GATE = """<div class="wiki-spoiler" role="note">
  <p class="wiki-spoiler-title">Spoilers ahead</p>
  <p>This wiki covers the whole game: every quest, twist, ending and secret. If you'd rather find Barovia out for
    yourself, <a href="/">head back to the main site</a>.</p>
</div>"""


TYPE_LABELS = {"location": "Location", "person": "Person", "creature": "Creature"}


def md_url_of(url: str) -> str:
	return "/wiki/index.md" if url == "/wiki/" else url[:-len(".html")] + ".md"


def markdown_copy(wiki: Wiki, key: str, lines: list, title: str) -> str:
	"""The page as plain Markdown for AI tools and scripts: Obsidian links become ordinary links to the other pages'
	Markdown copies, pictures point at the site's copies, and a line under the title says where it's from."""
	def link(m):
		inner = m.group(2).replace("\\|", "|")
		target, _, label = inner.partition("|")
		target, _, heading = target.partition("#")
		if m.group(1):   # a picture
			pic = wiki.image(target)
			if not pic:
				return ""
			return "![%s](%s%s)" % (Path(target).stem.replace("_", " "), SITE_URL, pic[1])
		shown = label or heading or target.rsplit("/", 1)[-1]
		k = wiki.page(target) if target else key
		if k is None:
			return shown
		return "[%s](%s%s%s)" % (shown, SITE_URL, md_url_of(wiki.pages[k]["url"]), "#" + slug(heading.lstrip("^")) if heading else "")
	text = "\n".join(lines)
	text = re.sub(r"(!?)\[\[((?:[^\]\\]|\\.)+?)\]\]", link, text)
	text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
	note = ("> From the Curse of Strahd game wiki (it covers the whole game, spoilers included): %s%s. Unofficial Fan "
		"Content permitted under the Fan Content Policy, not approved or endorsed by Wizards of the Coast.\n"
		% (SITE_URL, wiki.pages[key]["url"]))
	m = re.search(r"^# .*$", text, flags=re.M)
	if m:
		return text[:m.end()] + "\n\n" + note.rstrip("\n") + text[m.end():]
	return "# %s\n\n%s\n%s" % (title, note, text)


def hero(wiki: Wiki, key: str, title: str):
	"""The page's header: what it is (an eyebrow: "Side quest · Vallaki · Level 5"), its title, and for quests and
	places their opening screenshot behind it with the summary under the title. Returns (html, the picture's url or
	None, the summary shown or None)."""
	meta = wiki.pages[key].get("meta", {})
	kind = meta.get("type")
	if key == "Wiki/Home":
		return ('<header class="wiki-hero has-pic wiki-hero-home"><img class="wiki-hero-pic" src="/media/shots/hero.webp" '
			'alt="" fetchpriority="high" decoding="async"><div class="wiki-hero-text"><p class="wiki-eyebrow">The game '
			'guide</p><h1>%s</h1></div></header>' % html.escape(title)), None, None
	if kind not in ("quest", "location", "person", "creature"):
		return "", None, None
	bits = []
	if kind == "quest":
		bits.append("Main quest" if meta.get("kind") == "main" else "Side quest")
	elif kind == "person" and meta.get("title"):
		bits.append(html.escape(meta["title"]))
	elif kind == "creature":
		bits.append(html.escape((meta.get("creature") or "Creature").replace("_", " ").capitalize()))
	else:
		bits.append(TYPE_LABELS[kind])
	if meta.get("region"):
		name, url = wiki.region(meta["region"])
		bits.append('<a href="%s">%s</a>' % (url, html.escape(name)) if url else html.escape(name))
	if meta.get("level"):
		bits.append("Level %s" % html.escape(meta["level"]))
	if kind == "creature" and meta.get("cr"):
		bits.append("CR %s" % html.escape(meta["cr"]))
	eyebrow = '<p class="wiki-eyebrow">%s</p>' % ' <span aria-hidden="true">·</span> '.join(bits)
	image = wiki.page_image(key) if kind in ("quest", "location") else None
	pic = wiki.image("Wiki/" + image) if image else None
	summary = meta.get("summary", "")
	lede = summary if pic and summary and not summary.endswith(("…", "...")) else None
	parts = ['<header class="wiki-hero%s">' % (" has-pic" if pic else "")]
	if pic:
		parts.append('<img class="wiki-hero-pic" src="%s" alt="" fetchpriority="high" decoding="async">' % pic[1])
	parts.append('<div class="wiki-hero-text">%s<h1>%s</h1>' % (eyebrow, html.escape(title)))
	if lede:
		parts.append('<p class="wiki-lede">%s</p>' % html.escape(lede))
	parts.append("</div></header>")
	return "".join(parts), pic[1] if pic else None, lede


def home_cards(body: str) -> str:
	"""The front page's contents as a card per section, each headed by a screenshot from the main site."""
	def card(m):
		hid, head, rest = m.group(1), m.group(2), m.group(3)
		art = HOME_ART.get(hid)
		pic = '<img class="wiki-home-pic" src="/media/thumbs/%s.webp" alt="" loading="lazy">' % art if art else ""
		rest = re.sub(r"<li>(<a [^>]+>[^<]+</a>): (.*?)</li>", r'<li>\1<span class="wiki-home-desc">\2</span></li>', rest)
		return '<section class="wiki-home-card">%s<h2 id="%s">%s</h2>%s</section>' % (pic, hid, head, rest)
	return re.sub(r'<h2 id="([^"]+)">(.*?)</h2>\s*(<ul>.*?</ul>)', card, body, flags=re.S)


def item_sections(body: str, rarities: dict, key: str) -> str:
	"""On the item lists, each item (a ### heading, its meta line and text) as a card edged in its rarity's colour."""
	chunks = re.split(r'(?=<h[23] id=")', body)
	out = []
	for c in chunks:
		m = re.match(r'<h3 id="([^"]+)">', c)
		if not m:
			out.append(c)
			continue
		rarity = rarities.get((key, m.group(1)))
		cls = " " + rarity_class(rarity) if rarity else ""
		c = re.sub(r"(</h3>\s*)<p>(<em>.*?</em>)", r'\1<p class="wiki-item-meta">\2', c, count=1, flags=re.S)
		out.append('<section class="wiki-item%s">%s</section>\n' % (cls, c))
	body = "".join(out)
	return re.sub(r'((?:<section class="wiki-item[^"]*">.*?</section>\n)+)', r'<div class="wiki-items">\n\1</div>\n', body, flags=re.S)


def page_html(wiki: Wiki, key: str, body: str, title: str, crumbs: str, toc: str, description: str, v: dict,
		top: str = "", og_image: str = SITE_URL + "/media/og.jpg", md_url: str = "", ld: str = "{}") -> str:
	url = wiki.pages[key]["url"]
	full_title = "Curse of Strahd Wiki" if key == "Wiki/Home" else "%s - Curse of Strahd Wiki" % title
	return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(full_title)s</title>
<meta name="description" content="%(description)s">
<meta name="theme-color" content="#120709">
<link rel="canonical" href="https://curseofstrahd.app%(url)s">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Curse of Strahd - An unofficial fan game">
<meta property="og:title" content="%(full_title)s">
<meta property="og:description" content="%(description)s">
<meta property="og:url" content="https://curseofstrahd.app%(url)s">
<meta property="og:image" content="%(og_image)s">
<meta name="robots" content="max-image-preview:large">
<link rel="alternate" type="text/markdown" href="%(md_url)s" title="This page as Markdown">
<script type="application/ld+json">%(ld)s</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700;900&family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/site.css?v=%(css)s">
<link rel="stylesheet" href="/css/wiki.css?v=%(wcss)s">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/media/icon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="/media/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
</head>
<body class="wiki-body wiki-type-%(ptype)s">
<a class="skip" href="#main">Skip to the content</a>

%(nav)s

<main id="main" class="wiki">
  <div class="wrap wiki-wrap">
    <div class="wiki-bar">
      <nav class="wiki-crumbs" aria-label="Breadcrumb">%(crumbs)s</nav>
      <div class="wiki-search">
        <label class="sr" for="wiki-q">Search the wiki</label>
        <input id="wiki-q" type="search" placeholder="Search the wiki" autocomplete="off">
        <ul id="wiki-hits" class="wiki-hits" hidden></ul>
      </div>
    </div>
%(top)s
    <div class="wiki-layout%(has_toc)s">
      <article class="wiki-page">
%(body)s
      </article>
%(toc)s
    </div>
  </div>
</main>

%(footer)s

<script src="/js/site.js?v=%(js)s" defer></script>
<script src="/wiki/wiki.js?v=%(wjs)s" defer></script>
</body>
</html>
""" % {"full_title": html.escape(full_title), "description": html.escape(description, quote=True), "url": url,
		"css": v["css"], "wcss": v["wcss"], "js": v["js"], "wjs": v["wjs"], "nav": NAV, "crumbs": crumbs, "body": body,
		"toc": toc, "has_toc": " has-toc" if toc else "", "footer": FOOTER, "top": top, "og_image": html.escape(og_image),
		"md_url": html.escape(md_url), "ld": ld,
		"ptype": "home" if key == "Wiki/Home" else html.escape(wiki.pages[key].get("meta", {}).get("type") or "page")}


def build(wiki: Wiki, out: Path) -> None:
	out.mkdir(parents=True, exist_ok=True)
	v = {"css": stamp(SITE / "css/site.css"), "wcss": stamp(SITE / "css/wiki.css"), "js": stamp(SITE / "js/site.js"),
		"wjs": stamp(SITE / "wiki/wiki.js")}
	written = set()
	index = []
	site_map = []
	for key, info in wiki.pages.items():
		text = clean(info["path"].read_text(encoding="utf-8"))
		inline = Inline(wiki, key)
		blocks = Blocks(inline)
		# A list entry that only points at a note outside the wiki (the vault's own notes) is left out.
		lines = [l for l in text.split("\n") if not ((m := re.match(r"^\s*[-*] \[\[([^\]|#]+)", l))
			and wiki.page(m.group(1)) is None and wiki.image(m.group(1)) is None)]
		title = info["title"]
		for l in lines:
			m = re.match(r"^#\s+(.*)$", l.strip())
			if m:
				title = plain(inline.render(m.group(1)))
				break
		body = blocks.render(lines)
		top, hero_pic, lede = hero(wiki, key, title)
		if top:
			body = re.sub(r"<h1 [^>]*>.*?</h1>\n?", "", body, count=1, flags=re.S)
			if hero_pic:   # the header shows the picture, so neither the facts box nor the overview repeats it
				body = re.sub(r'<div class="wiki-infobox-pic"><img [^>]*src="%s"[^>]*></div>' % re.escape(hero_pic), "", body, count=1)
				body = re.sub(r'<p><img class="wiki-pic" src="%s"[^>]*>(<br>\n<em>[^<]*</em>)?</p>\n?' % re.escape(hero_pic), "",
					body, count=1)
			if lede:   # nor the summary's first paragraph, now under the title
				same = re.sub(r"\s+", " ", lede).strip()
				for m in re.finditer(r"<p>(.*?)</p>\n?", body, flags=re.S):
					if plain(m.group(1)) == same:
						body = body[:m.start()] + body[m.end():]
						break
				body = re.sub(r'<h2 id="summary">Summary</h2>\n?(?=<h2 )', "", body, count=1)
				blocks.headings = [h for h in blocks.headings if not (h[1] == "summary" and 'id="summary"' not in body)]
		if wiki.pages[key].get("meta", {}).get("type") == "item-list":
			body = item_sections(body, wiki.rarity, key)
		if key == "Wiki/Home":
			# The front page warns first, in the site's own words (the vault's own spoiler callout would repeat it).
			body = re.sub(r'<div class="callout callout-warning"><p class="callout-title">.*?Spoilers</p>.*?</div>\n?', "",
				body, count=1, flags=re.S)
			intro = re.search(r"<p>(.*?)</p>\n?", body, flags=re.S)   # the opening line goes under the header's title
			if intro:
				body = body[:intro.start()] + body[intro.end():]
				top = top.replace("</div></header>", '<p class="wiki-lede">%s</p></div></header>' % intro.group(1))
				lede = plain(intro.group(1))
			body = SPOILER_GATE + "\n" + home_cards(body)
		parts = key.split("/")[1:]
		crumbs = ['<a href="/wiki/">Wiki</a>'] if key != "Wiki/Home" else ['<span>Wiki</span>']
		trail = [("Wiki", "/wiki/")]
		for n in range(1, len(parts)):
			sub = "Wiki/" + "/".join(parts[:n])
			sub_key = wiki.page(sub) or wiki.page(sub + "/" + parts[n - 1])
			label = html.escape(parts[n - 1])
			crumbs.append('<a href="%s">%s</a>' % (wiki.pages[sub_key]["url"], label) if sub_key else "<span>%s</span>" % label)
			if sub_key:
				trail.append((parts[n - 1], wiki.pages[sub_key]["url"]))
		if key != "Wiki/Home":
			crumbs.append("<span>%s</span>" % html.escape(title))
			trail.append((title, info["url"]))
		if wiki.pages[key].get("meta", {}).get("type") == "item-list":
			blocks.headings = [h for h in blocks.headings if h[0] == 2]
		toc = ""
		if len(blocks.headings) >= 3 and key != "Wiki/Home":
			toc = '      <nav class="wiki-toc" aria-label="On this page"><p class="wiki-toc-title">On this page</p><ul>%s</ul></nav>' % "".join(
				'<li class="lv%d"><a href="#%s">%s</a></li>' % (lv, hid, html.escape(t)) for lv, hid, t in blocks.headings)
		para = re.search(r"<p>(.*?)</p>", body.split("</div>", 1)[-1] if key == "Wiki/Home" else body, re.S)
		desc = lede or (plain(para.group(1)) if para else "%s, in the Curse of Strahd game wiki." % title)
		if len(desc) > 155:
			desc = desc[:152].rsplit(" ", 1)[0] + "..."
		dest = out / ("index.html" if key == "Wiki/Home" else info["url"][len("/wiki/"):])
		dest.parent.mkdir(parents=True, exist_ok=True)
		# For search engines and AI tools: the page's picture, its date, structured data and a Markdown copy.
		image = hero_pic or (wiki.image("Wiki/" + wiki.page_image(key))[1] if wiki.page_image(key)
			and wiki.image("Wiki/" + wiki.page_image(key)) else None)
		if image and image.endswith(".svg"):
			image = None
		modified = datetime.date.fromtimestamp(info["path"].stat().st_mtime).isoformat()
		md_url = md_url_of(info["url"])
		canon = SITE_URL + info["url"]
		page_ld = {"@type": "WebPage", "@id": canon, "url": canon, "name": title, "description": desc, "inLanguage": "en",
			"dateModified": modified,
			"isPartOf": {"@type": "WebSite", "name": "Curse of Strahd Wiki", "url": SITE_URL + "/wiki/"},
			"about": {"@type": "VideoGame", "name": "Curse of Strahd (an unofficial fan game)", "url": SITE_URL + "/"},
			"encoding": {"@type": "MediaObject", "encodingFormat": "text/markdown", "contentUrl": SITE_URL + md_url}}
		if image:
			page_ld["image"] = SITE_URL + image
		graph = [page_ld]
		if len(trail) > 1:
			graph.append({"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": n + 1,
				"name": name, "item": SITE_URL + u} for n, (name, u) in enumerate(trail)]})
		ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")
		dest.write_text(page_html(wiki, key, body, title, " <span aria-hidden=\"true\">›</span> ".join(crumbs), toc, desc, v,
			top, SITE_URL + image if image else SITE_URL + "/media/og.jpg", md_url, ld), encoding="utf-8")
		written.add(dest.resolve())
		md_dest = dest.with_suffix(".md")
		md_dest.write_text(markdown_copy(wiki, key, lines, title), encoding="utf-8")
		written.add(md_dest.resolve())
		site_map.append((canon, modified, SITE_URL + image if image else None))
		index.append({"t": title, "u": info["url"], "s": info["section"]})
	index.sort(key=lambda e: e["t"].lower())
	# The wiki's own sitemap (robots.txt names it beside the main site's).
	rows = []
	for loc, modified, image in sorted(site_map):
		pic = "<image:image><image:loc>%s</image:loc></image:image>" % html.escape(image) if image else ""
		rows.append("  <url><loc>%s</loc><lastmod>%s</lastmod>%s</url>" % (html.escape(loc), modified, pic))
	(out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/'
		'sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n%s\n</urlset>\n' % "\n".join(rows),
		encoding="utf-8")
	written.add((out / "sitemap.xml").resolve())
	(out / "search.json").write_text(json.dumps(index, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
	written.add((out / "search.json").resolve())
	# Pictures: compressed WebPs (maps stay SVG), converted only when the source is newer.
	made = 0
	for src, url in wiki.images.values():
		dest = out / url[len("/wiki/"):]
		written.add(dest.resolve())
		if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
			continue
		dest.parent.mkdir(parents=True, exist_ok=True)
		if src.suffix.lower() == ".svg":
			shutil.copyfile(src, dest)
		else:
			im = Image.open(src)
			im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
			if im.width > PICTURE_WIDTH:
				im = im.resize((PICTURE_WIDTH, round(im.height * PICTURE_WIDTH / im.width)), Image.LANCZOS)
			im.save(dest, "WEBP", quality=78, method=5)
		made += 1
	for url, src in wiki.thumbs.items():
		dest = out / url[len("/wiki/"):]
		written.add(dest.resolve())
		if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
			continue
		dest.parent.mkdir(parents=True, exist_ok=True)
		im = Image.open(src)
		im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
		if "/shots/" in url and not re.search(r"overview|travel-map", url) and im.width > im.height:
			im = im.crop((round(im.width * 0.17), 0, round(im.width * 0.86), round(im.height * 0.6)))
		width = min(THUMB_WIDTH, im.width, 192 if "/portraits/" in url else THUMB_WIDTH)
		if im.width > width:
			im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
		im.save(dest, "WEBP", quality=74, method=5)
		made += 1
	# Whatever the source no longer has goes, except the wiki's own script.
	keep = {(out / "wiki.js").resolve()}
	gone = 0
	for f in sorted(out.rglob("*"), reverse=True):
		if f.is_file() and f.resolve() not in written and f.resolve() not in keep:
			f.unlink()
			gone += 1
		elif f.is_dir() and not any(f.iterdir()):
			f.rmdir()
	print("build_wiki: %d pages, %d pictures (%d converted), %d stale files removed" % (len(wiki.pages), len(wiki.images), made, gone))
	if wiki.missing:
		print("build_wiki: %d link targets outside the wiki, shown as text: %s" % (len(wiki.missing),
			", ".join("%s (%d)" % (k, n) for k, n in sorted(wiki.missing.items(), key=lambda kv: -kv[1])[:12])))


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--src", type=Path, default=SRC)
	ap.add_argument("--out", type=Path, default=SITE / "wiki")
	args = ap.parse_args()
	build(Wiki(args.src, args.out), args.out)


if __name__ == "__main__":
	main()
