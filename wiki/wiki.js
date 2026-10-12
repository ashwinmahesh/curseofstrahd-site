// The wiki's title search (tools/build_wiki.py writes /wiki/search.json): type to see matching pages; arrows and Enter
// pick one. The list loads on first use.
(function () {
	const input = document.getElementById("wiki-q");
	const hits = document.getElementById("wiki-hits");
	if (!input || !hits) return;
	let pages = null;
	let on = -1;

	function load() {
		if (pages) return Promise.resolve(pages);
		return fetch("/wiki/search.json").then((r) => r.json()).then((d) => (pages = d)).catch(() => (pages = []));
	}

	function words(s) {
		return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").split(/[^a-z0-9]+/).filter(Boolean);
	}

	function show(list) {
		hits.innerHTML = "";
		on = -1;
		for (const p of list) {
			const li = document.createElement("li");
			const a = document.createElement("a");
			a.href = p.u;
			a.textContent = p.t;
			if (p.s) {
				const small = document.createElement("small");
				small.textContent = p.s;
				a.appendChild(small);
			}
			li.appendChild(a);
			hits.appendChild(li);
		}
		hits.hidden = list.length === 0;
	}

	function search() {
		const q = words(input.value);
		if (!q.length) return show([]);
		load().then((all) => {
			const scored = [];
			for (const p of all) {
				const t = words(p.t).join(" ");
				if (!q.every((w) => t.includes(w))) continue;
				scored.push([t.startsWith(q.join(" ")) ? 0 : 1, p.t.length, p]);
			}
			scored.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
			show(scored.slice(0, 14).map((s) => s[2]));
		});
	}

	function move(d) {
		const links = hits.querySelectorAll("a");
		if (!links.length) return;
		if (on >= 0) links[on].classList.remove("is-on");
		on = (on + d + links.length) % links.length;
		links[on].classList.add("is-on");
		links[on].scrollIntoView({ block: "nearest" });
	}

	input.addEventListener("input", search);
	input.addEventListener("focus", load);
	input.addEventListener("keydown", (e) => {
		if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
		else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
		else if (e.key === "Enter") {
			const links = hits.querySelectorAll("a");
			const pick = on >= 0 ? links[on] : links[0];
			if (pick) location.href = pick.href;
		} else if (e.key === "Escape") { show([]); }
	});
	document.addEventListener("click", (e) => {
		if (!e.target.closest(".wiki-search")) hits.hidden = true;
	});
})();

// The contents list marks the section you're reading.
(function () {
	const toc = document.querySelector(".wiki-toc");
	if (!toc || !("IntersectionObserver" in window)) return;
	const links = new Map([...toc.querySelectorAll("a")].map((a) => [decodeURIComponent(a.hash.slice(1)), a]));
	let current = null;
	const io = new IntersectionObserver((entries) => {
		for (const e of entries) {
			if (!e.isIntersecting) continue;
			const a = links.get(e.target.id);
			if (!a) continue;
			if (current) current.classList.remove("is-on");
			a.classList.add("is-on");
			current = a;
		}
	}, { rootMargin: "-90px 0px -70% 0px" });
	for (const id of links.keys()) {
		const h = document.getElementById(id);
		if (h) io.observe(h);
	}
})();
