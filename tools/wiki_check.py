# Static checks on the rendered wiki (after tools/build_wiki.py): nav, credit, legal block on every page, no broken /wiki/ links, no raw markup.
import glob, re, collections, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
files = glob.glob("wiki/**/*.html", recursive=True)
need = {"nav": "Wiki (spoilers)", "credit": "Game created by Ashwin Mahesh", "legal": "Fan Content"}
miss = collections.Counter(); broken = []; raw = collections.Counter()
for f in files:
	t = open(f, encoding="utf-8").read()
	for k, s in need.items():
		if s not in t: miss[k] += 1
	for u in re.findall(r'(?:href|src)="(/wiki/[^"#?]*)', t):
		p = u.lstrip("/")
		if p.endswith("/"): p += "index.html"
		if not os.path.exists(p): broken.append((f, u))
	body = re.sub(r"<[^>]+>", " ", t.split('<article class="wiki-page">', 1)[1].split("</article>", 1)[0])
	for k, p in {"[[": r"\[\[", "%%": r"%%", "[!": r"\[!", "**": r"\*\*"}.items():
		if re.search(p, body): raw[k] += 1
print(len(files), "pages; missing", dict(miss), "; broken", len(broken), broken[:2], "; raw", dict(raw), "; warning",
	"Spoilers ahead" in open("wiki/index.html").read())
