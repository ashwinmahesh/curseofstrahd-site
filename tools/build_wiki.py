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
import hashlib
import html
import json
import re
import shutil
from pathlib import Path

from PIL import Image

SITE = Path(__file__).resolve().parent.parent
SRC = Path.home() / "Documents/Obsidian Vault/CurseOfStrahd/Wiki"
PICTURE_WIDTH = 1280
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
CALLOUT_ICONS = {"warning": "⚠", "danger": "⚠", "caution": "⚠", "info": "✦", "note": "✦", "tip": "✧", "example": "✦",
	"quote": "❝", "success": "✓", "question": "?", "abstract": "✦", "summary": "✦", "todo": "☐", "bug": "✗"}


def slug(text: str) -> str:
	text = text.lower().replace("&", " and ").replace("'", "").replace("’", "")
	return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "page"


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
		return '<a href="%s">%s</a>' % (html.escape(url), html.escape(shown))

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
			self.headings.append((level, hid, re.sub(r"<[^>]+>", "", self.inline.render(text))))
		return '<h%d id="%s">%s</h%d>' % (level, hid, self.inline.render(text), level)

	def quote(self, lines: list) -> str:
		body = [re.sub(r"^\s*> ?", "", l) for l in lines]
		m = re.match(r"^\[!(\w+)\]([+-]?)\s*(.*)$", body[0].strip()) if body else None
		if not m:
			return "<blockquote>%s</blockquote>" % self.render(body)
		kind, fold, title = m.group(1).lower(), m.group(2), m.group(3) or m.group(1).capitalize()
		icon = CALLOUT_ICONS.get(kind, "✦")
		inner = self.render(body[1:])
		head = '<span class="callout-icon" aria-hidden="true">%s</span>%s' % (icon, self.inline.render(title))
		if fold:
			return '<details class="callout callout-%s"%s><summary class="callout-title">%s</summary>%s</details>' % (
				kind, " open" if fold == "+" else "", head, inner)
		return '<div class="callout callout-%s"><p class="callout-title">%s</p>%s</div>' % (kind, head, inner)

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
			return "<tr>%s</tr>" % "".join('<%s%s>%s</%s>' % (tag, ' style="text-align:%s"' % aligns[k]
				if k < len(aligns) and aligns[k] else "", self.inline.render(c), tag) for k, c in enumerate(cells))
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
		out = []
		start = ""
		if ordered:
			first = int(re.match(r"\d+", LIST_RE.match(lines[0]).group(2)).group(0))
			start = ' start="%d"' % first if first != 1 else ""
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


def page_html(wiki: Wiki, key: str, body: str, title: str, crumbs: str, toc: str, description: str, v: dict) -> str:
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
<meta property="og:image" content="https://curseofstrahd.app/media/og.jpg">
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
<body class="wiki-body">
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
		"toc": toc, "has_toc": " has-toc" if toc else "", "footer": FOOTER}


def build(wiki: Wiki, out: Path) -> None:
	out.mkdir(parents=True, exist_ok=True)
	v = {"css": stamp(SITE / "css/site.css"), "wcss": stamp(SITE / "css/wiki.css"), "js": stamp(SITE / "js/site.js"),
		"wjs": stamp(SITE / "wiki/wiki.js")}
	written = set()
	index = []
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
		if key == "Wiki/Home":
			# The front page warns first, in the site's own words (the vault's own spoiler callout would repeat it).
			body = re.sub(r'<div class="callout callout-warning"><p class="callout-title">.*?Spoilers</p>.*?</div>\n?', "",
				body, count=1, flags=re.S)
			body = SPOILER_GATE + "\n" + body
		parts = key.split("/")[1:]
		crumbs = ['<a href="/wiki/">Wiki</a>'] if key != "Wiki/Home" else ['<span>Wiki</span>']
		for n in range(1, len(parts)):
			sub = "Wiki/" + "/".join(parts[:n])
			sub_key = wiki.page(sub) or wiki.page(sub + "/" + parts[n - 1])
			label = html.escape(parts[n - 1])
			crumbs.append('<a href="%s">%s</a>' % (wiki.pages[sub_key]["url"], label) if sub_key else "<span>%s</span>" % label)
		if key != "Wiki/Home":
			crumbs.append("<span>%s</span>" % html.escape(title))
		toc = ""
		if len(blocks.headings) >= 3:
			toc = '      <nav class="wiki-toc" aria-label="On this page"><p class="wiki-toc-title">On this page</p><ul>%s</ul></nav>' % "".join(
				'<li class="lv%d"><a href="#%s">%s</a></li>' % (lv, hid, html.escape(t)) for lv, hid, t in blocks.headings)
		para = re.search(r"<p>(.*?)</p>", body.split("</div>", 1)[-1] if key == "Wiki/Home" else body, re.S)
		desc = plain(para.group(1)) if para else "%s, in the Curse of Strahd game wiki." % title
		if len(desc) > 155:
			desc = desc[:152].rsplit(" ", 1)[0] + "..."
		dest = out / ("index.html" if key == "Wiki/Home" else info["url"][len("/wiki/"):])
		dest.parent.mkdir(parents=True, exist_ok=True)
		dest.write_text(page_html(wiki, key, body, title, " <span aria-hidden=\"true\">›</span> ".join(crumbs), toc, desc, v),
			encoding="utf-8")
		written.add(dest.resolve())
		index.append({"t": title, "u": info["url"], "s": info["section"]})
	index.sort(key=lambda e: e["t"].lower())
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
