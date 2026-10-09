// The pages' small interactions: the navigation bar, the screenshot switchers in the feature sections, the
// companion picker and the gallery's full-size viewer.
(() => {
	const nav = document.getElementById("nav");
	const toggle = document.getElementById("nav-toggle");
	const links = document.getElementById("nav-links");

	// The bar turns solid once the banner is scrolled past.
	const solid = () => nav.classList.toggle("is-solid", window.scrollY > 40);
	solid();
	window.addEventListener("scroll", solid, { passive: true });

	toggle.addEventListener("click", () => {
		const open = links.classList.toggle("is-open");
		toggle.setAttribute("aria-expanded", String(open));
	});
	links.addEventListener("click", (e) => {
		if (e.target.closest("a")) {
			links.classList.remove("is-open");
			toggle.setAttribute("aria-expanded", "false");
		}
	});

	// Feature sections: a thumbnail swaps the large screenshot above it.
	for (const box of document.querySelectorAll("[data-switcher]")) {
		const main = box.querySelector(".dive-main img");
		for (const t of box.querySelectorAll(".thumb")) {
			t.addEventListener("click", () => {
				box.querySelectorAll(".thumb").forEach((o) => o.classList.toggle("is-on", o === t));
				main.style.opacity = "0";
				const next = new Image();
				next.onload = next.onerror = () => {
					main.src = t.dataset.src;
					main.alt = t.dataset.alt;
					main.style.opacity = "1";
				};
				next.src = t.dataset.src;
			});
		}
	}

	// The game in motion: each loop plays only while it's on screen, so the page doesn't download them all at once.
	const loops = document.querySelectorAll("video[data-loop]");
	if (loops.length && "IntersectionObserver" in window) {
		const seen = new IntersectionObserver((entries) => {
			for (const e of entries) {
				if (e.isIntersecting) e.target.play().catch(() => {});
				else e.target.pause();
			}
		}, { threshold: 0.4 });
		loops.forEach((v) => seen.observe(v));
	}

	// Companions: one card picked at a time shows its story below.
	const grid = document.getElementById("comp-grid");
	const detail = document.getElementById("comp-detail");
	if (grid) grid.addEventListener("click", (e) => {
		const card = e.target.closest(".comp");
		if (!card) return;
		for (const c of grid.querySelectorAll(".comp")) {
			const on = c === card;
			c.classList.toggle("is-on", on);
			c.setAttribute("aria-pressed", String(on));
		}
		for (const a of detail.querySelectorAll("article")) a.hidden = a.dataset.id !== card.dataset.id;
	});

	// Gallery viewer (the home page only).
	const lb = document.getElementById("lightbox");
	if (!lb) return;
	const lbImg = document.getElementById("lb-img");
	const lbCap = document.getElementById("lb-cap");
	const shots = [...document.querySelectorAll("#gal-grid button")];
	let at = 0;
	let opener = null;
	const show = (i) => {
		at = (i + shots.length) % shots.length;
		const b = shots[at];
		lbImg.src = b.dataset.full;
		lbImg.alt = b.dataset.caption;
		lbCap.textContent = b.dataset.caption;
	};
	const close = () => {
		lb.hidden = true;
		document.body.style.overflow = "";
		if (opener) opener.focus();
	};
	shots.forEach((b, i) => b.addEventListener("click", () => {
		opener = b;
		show(i);
		lb.hidden = false;
		document.body.style.overflow = "hidden";
		lb.querySelector(".lb-close").focus();
	}));
	lb.querySelector(".lb-close").addEventListener("click", close);
	lb.querySelector(".lb-prev").addEventListener("click", () => show(at - 1));
	lb.querySelector(".lb-next").addEventListener("click", () => show(at + 1));
	lb.addEventListener("click", (e) => { if (e.target === lb) close(); });
	document.addEventListener("keydown", (e) => {
		if (lb.hidden) return;
		if (e.key === "Escape") close();
		else if (e.key === "ArrowLeft") show(at - 1);
		else if (e.key === "ArrowRight") show(at + 1);
	});
	// Swipe between screenshots on a phone.
	let x0 = null;
	lb.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
	lb.addEventListener("touchend", (e) => {
		if (x0 === null) return;
		const dx = e.changedTouches[0].clientX - x0;
		if (Math.abs(dx) > 50) show(at + (dx < 0 ? 1 : -1));
		x0 = null;
	});
})();
