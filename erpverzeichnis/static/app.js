// ERP-Verzeichnis – statische Seite (GitHub Pages).
// Alle Seiten funktionieren ohne JavaScript; das Skript ergänzt Schublade, Filter im Verzeichnis,
// die Modulauswahl im Berater, den Vergleich und Suchvorschläge.
document.documentElement.classList.add("js");

const ROOT = document.documentElement.dataset.root || "";
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const liste = (p, key) => p.getAll(key).flatMap((v) => v.split(",")).map((v) => v.trim()).filter(Boolean);

document.addEventListener("DOMContentLoaded", () => {
  initMenu();
  initDetails(document);
  initSchublade();
  initBerater();
  initVerzeichnis();
  initVergleich();
  initMerkliste();
  initSuche();
  initZurueck();
});

/* ---------- Menü auf dem Handy ---------- */
function initMenu() {
  const btn = document.querySelector("[data-menu]");
  const nav = document.getElementById("hauptnav");
  if (!btn || !nav) return;
  const setzen = (auf) => { nav.classList.toggle("offen", auf); btn.setAttribute("aria-expanded", String(auf)); };
  btn.addEventListener("click", (e) => { e.stopPropagation(); setzen(!nav.classList.contains("offen")); });
  document.addEventListener("click", (e) => { if (!nav.contains(e.target)) setzen(false); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && nav.classList.contains("offen")) { setzen(false); btn.focus(); } });
}

/* ---------- Alle Details auf-/zuklappen ---------- */
function initDetails(root) {
  const btn = root.querySelector("[data-toggle-all]");
  if (!btn) return;
  const alle = $$("details.acc", root);
  btn.addEventListener("click", () => {
    const auf = !alle.every((d) => d.open);
    alle.forEach((d) => (d.open = auf));
    btn.textContent = auf ? "Alle zuklappen" : "Alle aufklappen";
  });
}

/* ---------- Steckbrief-Schublade ---------- */
function initSchublade() {
  const drawer = document.getElementById("drawer");
  if (!drawer) return;
  const scrim = document.getElementById("scrim");
  const body = document.getElementById("drawer-body");
  const link = document.getElementById("drawer-link");
  let zuletzt = null, aktiveZeile = null;

  const schliessen = () => {
    if (!drawer.classList.contains("on")) return;
    drawer.classList.remove("on");
    scrim.classList.remove("on");
    drawer.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    setTimeout(() => { scrim.hidden = true; }, 200);
    aktiveZeile && aktiveZeile.classList.remove("aktiv");
    zuletzt && zuletzt.focus();
  };

  const oeffnen = async (href, ausloeser) => {
    zuletzt = ausloeser;
    aktiveZeile && aktiveZeile.classList.remove("aktiv");
    aktiveZeile = ausloeser.classList.contains("vz-row") ? ausloeser : null;
    aktiveZeile && aktiveZeile.classList.add("aktiv");
    const seite = new URL(href, location.href);
    link.href = seite.href;
    body.innerHTML = `<div class="dr-laden"><img src="${ROOT}static/maskottchen/kopf.webp" alt="">Lexu holt den Steckbrief …</div>`;
    scrim.hidden = false;
    requestAnimationFrame(() => { scrim.classList.add("on"); drawer.classList.add("on"); });
    drawer.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    try {
      // Zu jeder Steckbrief-Seite gibt es ein Fragment ohne Kopf und Fuss
      const quelle = new URL("steckbrief.html", seite);
      const r = await fetch(quelle);
      if (!r.ok) throw new Error(r.status);
      const tmp = document.createElement("div");
      tmp.innerHTML = await r.text();
      // Relative Links und Bilder beziehen sich auf das Fragment, nicht auf die aktuelle Seite
      $$("[src]", tmp).forEach((el) => el.setAttribute("src", new URL(el.getAttribute("src"), quelle).href));
      $$("a[href]", tmp).forEach((el) => {
        const h = el.getAttribute("href");
        if (!h.startsWith("#")) el.setAttribute("href", new URL(h, quelle).href);
      });
      body.replaceChildren(...tmp.childNodes);
      body.scrollTop = 0;
      initDetails(body);
      vglKnoepfe(body);
      drawer.querySelector("[data-close]").focus();
    } catch (_) {
      location.href = seite.href; // Fallback: normale Seite
    }
  };

  document.addEventListener("click", (e) => {
    const a = e.target.closest("a[data-drawer]");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    if (window.matchMedia("(max-width: 700px)").matches) return; // Handy: normale Seite
    e.preventDefault();
    oeffnen(a.getAttribute("href"), a);
  });
  drawer.querySelector("[data-close]").addEventListener("click", schliessen);
  scrim.addEventListener("click", schliessen);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") schliessen(); });
}

/* ---------- Berater: Module und Betrieb wählen, Empfehlungen im Browser berechnen ----------
   PUNKTELOGIK – gleich wie in erpverzeichnis/data.py (empfehlen, treffer_liste, Loesung.fit). */
const BETRIEB_WAHL = { cloud: ["Cloud", "Hosted", "Hybrid"], server: ["On-Prem", "Hybrid"] };
const ROLLEN = {
  beide: ["Beste Wahl", "Beste Abdeckung und zugleich die günstigste Lösung"],
  abdeckung: ["Beste Abdeckung", "Deckt Ihre Bereiche am vollständigsten ab"],
  guenstig: ["Günstigste Lösung", "Tiefste Kosten und Einführungsaufwand"],
  kompromiss: ["Guter Kompromiss", "Gute Abdeckung zu vernünftigen Kosten"],
  weitere: ["Ebenfalls passend", "Eine weitere gute Wahl"],
};

function fit(l, groesse, branche, G) {
  let p = 0;
  if (groesse && l.g.length) {
    if (l.g.includes(groesse)) p += 2;
    else if (l.g.some((g) => Math.abs(G.indexOf(g) - G.indexOf(groesse)) === 1)) p += 0.5;
    else return null;
  } else p += 1;
  if (branche && branche !== "andere" && l.b.includes(branche)) p += l.seg === "Branchenlösung" ? 2.5 : 1.5;
  else if (l.seg === "Branchenlösung") return null;
  else if (l.b.includes("neutral") || !l.b.length) p += 1;
  else p += 0.5;
  return p;
}
const kostenAchse = (l) => (l.k ?? 1.5) + (l.a ?? 1);

function empfehlen(D, module, betrieb) {
  const alle = [];
  for (const l of D.loesungen) {
    const f = fit(l, D.groesse, D.branche, D.groessen);
    if (f === null) continue;
    if (betrieb && !l.bt.some((b) => BETRIEB_WAHL[betrieb].includes(b))) continue;
    const werte = module.map((m) => [m, l.m[m]]);
    if (werte.some(([, w]) => w === "nein")) continue;
    const abdeckung = werte.length ? werte.reduce((s, [, w]) => s + D.skala[w].punkte, 0) / werte.length : l.br;
    alle.push({ l, fit: f, abdeckung, werte, gesamt: abdeckung + f - 0.6 * kostenAchse(l) });
  }
  if (!alle.length) return { rollen: [], rest: [], alle };
  const cmp = (...fs) => (a, b) => { for (const f of fs) { const x = f(a), y = f(b); if (x < y) return -1; if (x > y) return 1; } return 0; };
  const beste = [...alle].sort(cmp((t) => -(t.abdeckung + t.fit), (t) => -t.abdeckung, (t) => -t.l.br, (t) => kostenAchse(t.l), (t) => t.l.pp, (t) => t.l.n))[0];
  const mitPreis = alle.filter((t) => t.l.k !== null);
  const guenstig = mitPreis.length ? [...mitPreis].sort(cmp((t) => kostenAchse(t.l), (t) => -t.abdeckung, (t) => -t.fit, (t) => t.l.pp, (t) => t.l.n))[0] : null;
  const gewaehlt = [];
  if (guenstig === beste) gewaehlt.push(["beide", beste]);
  else { gewaehlt.push(["abdeckung", beste]); if (guenstig) gewaehlt.push(["guenstig", guenstig]); }
  const uebrig = alle.filter((t) => !gewaehlt.some(([, x]) => x === t))
    .sort(cmp((t) => -t.gesamt, (t) => -t.abdeckung, (t) => t.l.pp, (t) => t.l.n));
  for (const t of uebrig) {
    if (gewaehlt.length >= 3) break;
    const rolle = !gewaehlt.some(([r]) => r === "kompromiss") && gewaehlt[0][0] !== "beide" ? "kompromiss" : "weitere";
    gewaehlt.push([rolle, t]);
  }
  return { rollen: gewaehlt, rest: uebrig.filter((t) => !gewaehlt.some(([, x]) => x === t)), alle };
}

function gruende(t, D) {
  const out = t.werte.map(([m, w]) => ({ ton: D.skala[w].ton, text: `${D.bedarf[m]}: ${D.skala[w].satz}` }));
  if (!t.werte.length) {
    out.push({ ton: t.l.v >= 18 ? "gut" : "mittel", text: `${t.l.v} von ${D.modul_total} Bereichen im Standard enthalten` });
  }
  if (D.groesse && !t.l.g.length) out.push({ ton: "offen", text: "Für welche Betriebsgrösse, ist noch offen" });
  else if (D.groesse) {
    out.push(t.l.g.includes(D.groesse)
      ? { ton: "gut", text: "Passt zu Ihrer Betriebsgrösse" }
      : { ton: "mittel", text: `Grösse grenzwertig: gedacht für ${t.l.gt}` });
  }
  if (D.branche && t.l.b.includes(D.branche)) out.push({ ton: "gut", text: `Auf ${D.branche_label} ausgerichtet` });
  return out;
}

function initBerater() {
  const form = document.querySelector("[data-berater]");
  const datenEl = document.getElementById("berater-daten");
  if (!form || !datenEl) return;
  const D = JSON.parse(datenEl.textContent);
  const pool = document.querySelector("[data-pool]");
  const recs = document.querySelector("[data-recs]");
  const leer = document.querySelector("[data-leer]");
  const mehr = document.querySelector("[data-mehr]");
  const restBox = document.querySelector("[data-rest]");
  const restListe = document.querySelector("[data-rest-liste]");
  const text = document.querySelector("[data-erg-text]");
  const auswahl = document.querySelector("[data-erg-auswahl]");
  const vglLink = document.querySelector("[data-vergleich-link]");
  const teilen = document.querySelector("[data-teilen]");

  const p = new URLSearchParams(location.search);
  const startModule = liste(p, "modul");
  $$('input[name="modul"]', form).forEach((i) => (i.checked = startModule.includes(i.value)));
  const b = p.get("betrieb") || "";
  $$('input[name="betrieb"]', form).forEach((i) => (i.checked = i.value === b));

  const listeHtml = (punkte) => `<ul class="ton-liste">${punkte.map((k) =>
    `<li class="ton-${k.ton}"><span class="ti" aria-hidden="true"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${D.zeichen[k.ton] || D.zeichen.offen}</svg></span><span>${esc(k.text)}</span></li>`).join("")}</ul>`;

  const rechnen = (urlSetzen) => {
    const module = $$('input[name="modul"]:checked', form).map((i) => i.value);
    const betrieb = (form.querySelector('input[name="betrieb"]:checked') || {}).value || "";
    const { rollen, rest, alle } = empfehlen(D, module, betrieb);

    recs.replaceChildren(...rollen.map(([rolle, t]) => {
      const el = pool.querySelector(`.rec[data-id="${CSS.escape(t.l.id)}"]`).cloneNode(true);
      el.className = `rec rolle-${rolle}`;
      el.querySelector("[data-rolle]").textContent = ROLLEN[rolle][0];
      el.querySelector("[data-rolle-hilfe]").textContent = ROLLEN[rolle][1];
      el.querySelector("[data-gruende]").innerHTML = listeHtml(gruende(t, D));
      return el;
    }));
    vglKnoepfe(recs);
    leer.hidden = rollen.length > 0;
    mehr.hidden = rollen.length < 2;
    vglLink.href = `${ROOT}vergleich/?ids=${rollen.map(([, t]) => t.l.id).join(",")}`;
    restBox.hidden = !rest.length;
    document.querySelector("[data-rest-n]").textContent = rest.length;
    restListe.replaceChildren(...rest.map((t) => pool.querySelector(`[data-rest-vorlage] [data-id="${CSS.escape(t.l.id)}"]`).cloneNode(true)));
    const n = alle.length;
    text.innerHTML = n
      ? `Es passen <b>${n} ${n === 1 ? "Lösung" : "Lösungen"}</b>. Statt einer Rangliste zeige ich Ihnen, wo Sie wählen müssen – zwischen Abdeckung und Kosten:`
      : "Für diese Auswahl habe ich keine passende Lösung gefunden.";
    const teile = module.map((m) => D.bedarf[m]);
    if (betrieb) teile.push(betrieb === "cloud" ? "Cloud" : "eigener Server");
    auswahl.textContent = teile.length ? `Ihre Auswahl: ${teile.join(" · ")}` : "";

    if (urlSetzen) {
      const q = new URLSearchParams();
      if (module.length) q.set("modul", module.join(","));
      if (betrieb) q.set("betrieb", betrieb);
      const s = q.toString().replace(/%2C/g, ",");
      history.replaceState(null, "", location.pathname + (s ? "?" + s : "") + "#ergebnis");
    }
  };

  form.addEventListener("change", () => rechnen(true));
  form.addEventListener("submit", (e) => { e.preventDefault(); rechnen(true); document.getElementById("ergebnis").scrollIntoView(); });
  if (startModule.length || b) rechnen(false);

  if (navigator.clipboard && teilen) {
    teilen.hidden = false;
    teilen.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(location.href); teilen.lastChild.textContent = " Link kopiert"; } catch (_) { /* egal */ }
    });
  }
}

/* ---------- Verzeichnis: Filter, Zähler im Browser ---------- */
function initVerzeichnis() {
  const form = document.getElementById("filter");
  const tbl = document.getElementById("vz-tbl");
  if (!form || !tbl) return;
  const zeilen = $$(".vz-row", tbl).map((el) => {
    const d = el.dataset;
    const m = Object.fromEntries(d.m.trim().split(/\s+/).filter(Boolean).map((x) => x.split(":")));
    return { el, id: d.id, g: d.g.split(" "), seg: d.seg, bt: d.bt.split(" "), m, sd: d.sd, ort: d.ort, ca: d.ca, such: d.such };
  });
  const total = zeilen.length;

  const lesen = () => {
    const f = new FormData(form);
    return {
      q: (f.get("q") || "").trim().toLowerCase(), groesse: f.get("groesse") || "", segment: f.get("segment") || "",
      modul: f.getAll("modul"), betrieb: f.get("betrieb") || "",
      swissdec: f.has("swissdec"), datench: f.has("datench"), cloudact: f.has("cloudact"),
    };
  };
  const passt = (z, s, ohne) => {
    if (ohne !== "groesse" && s.groesse && !z.g.includes(s.groesse)) return false;
    if (ohne !== "segment" && s.segment && z.seg !== s.segment) return false;
    if (ohne !== "betrieb" && s.betrieb && !z.bt.some((b) => BETRIEB_WAHL[s.betrieb].includes(b))) return false;
    if (s.modul.some((m) => z.m[m] === "nein")) return false;
    if (s.swissdec && z.sd !== "ja") return false;
    if (s.datench && z.ort !== "ch") return false;
    if (s.cloudact && z.ca !== "nein") return false;
    if (s.q && !s.q.split(/\s+/).every((w) => z.such.includes(w))) return false;
    return true;
  };

  const anwenden = (urlSetzen) => {
    const s = lesen();
    let n = 0;
    for (const z of zeilen) { const ok = passt(z, s); z.el.parentElement.hidden = !ok; if (ok) n++; }
    document.querySelector("[data-anzahl]").textContent = `${n} ${n === 1 ? "Lösung" : "Lösungen"}`;
    document.querySelector("[data-anzahl-info]").textContent = n === total ? "– alle Einträge" : `von ${total}`;
    document.querySelector("[data-leer]").hidden = n > 0;
    tbl.hidden = n === 0;
    const aktiv = s.q || s.groesse || s.segment || s.modul.length || s.betrieb || s.swissdec || s.datench || s.cloudact;
    $$("[data-reset]").forEach((el) => (el.hidden = !aktiv));
    document.querySelector("[data-aktiv]").hidden = !aktiv;
    // Zähler: wie viele Lösungen bei dieser Option übrig blieben
    $$("[data-n]").forEach((em) => {
      const [key, wert] = em.dataset.n.split(":");
      const probe = { ...s };
      if (key === "modul") probe.modul = [...new Set([...s.modul, wert])];
      else if (["swissdec", "datench", "cloudact"].includes(key)) probe[key] = true;
      else probe[key] = wert;
      const k = zeilen.filter((z) => passt(z, probe)).length;
      em.textContent = k;
      em.closest("label").classList.toggle("leer", k === 0);
    });
    if (urlSetzen) {
      const q = new URLSearchParams();
      if (s.q) q.set("q", s.q);
      for (const k of ["groesse", "segment", "betrieb"]) if (s[k]) q.set(k, s[k]);
      if (s.modul.length) q.set("modul", s.modul.join(","));
      for (const k of ["swissdec", "datench", "cloudact"]) if (s[k]) q.set(k, "1");
      const str = q.toString().replace(/%2C/g, ",");
      history.replaceState(null, "", location.pathname + (str ? "?" + str : ""));
    }
  };

  // Startzustand aus der Adresse
  const p = new URLSearchParams(location.search);
  form.elements.q.value = p.get("q") || "";
  for (const k of ["groesse", "segment", "betrieb"]) {
    const v = p.get(k) || "";
    $$(`input[name="${k}"]`, form).forEach((i) => (i.checked = i.value === v));
  }
  const module = liste(p, "modul");
  $$('input[name="modul"]', form).forEach((i) => (i.checked = module.includes(i.value)));
  for (const k of ["swissdec", "datench", "cloudact"]) form.elements[k].checked = p.get(k) === "1";

  form.addEventListener("input", () => anwenden(true));
  form.addEventListener("change", () => anwenden(true));
  form.addEventListener("submit", (e) => { e.preventDefault(); anwenden(true); });
  $$("[data-reset]").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    form.reset();
    anwenden(true);
  }));
  if (window.matchMedia("(max-width: 1000px)").matches) document.querySelector(".vz-filter").open = false;
  anwenden(false);
}

/* ---------- Merkliste für den Vergleich (seitenübergreifend, nur in diesem Browser) ----------
   Gespeichert als [{id, name}] in localStorage – reine Bequemlichkeit, die Seite funktioniert auch ohne. */
const VGL_KEY = "erp-vergleich", VGL_MAX = 4;
const vglLesen = () => {
  try { const x = JSON.parse(localStorage.getItem(VGL_KEY)); return Array.isArray(x) ? x.slice(0, VGL_MAX) : []; } catch (_) { return []; }
};
const vglSchreiben = (liste) => {
  try { localStorage.setItem(VGL_KEY, JSON.stringify(liste.slice(0, VGL_MAX))); } catch (_) { /* privat/blockiert */ }
  document.dispatchEvent(new CustomEvent("vgl-geaendert"));
};

function vglKnoepfe(root = document) {
  const ids = vglLesen().map((x) => x.id);
  $$("[data-merken]", root).forEach((b) => {
    const an = ids.includes(b.dataset.merken);
    b.classList.toggle("an", an);
    b.setAttribute("aria-pressed", String(an));
    const t = b.querySelector(".merk-t");
    if (t) t.textContent = an ? "Im Vergleich" : (b.classList.contains("merk-gross") ? "Zum Vergleich hinzufügen" : "Vergleichen");
  });
}

function initMerkliste() {
  const leiste = document.getElementById("vgl-leiste");
  let hinweisTimer;
  const zeigeLeiste = (hinweis = "") => {
    if (!leiste) return;
    const liste = vglLesen();
    leiste.hidden = liste.length === 0;
    document.body.classList.toggle("mit-vgl-leiste", liste.length > 0);
    leiste.querySelector("[data-vgl-n]").textContent = liste.length;
    leiste.querySelector("[data-vgl-chips]").innerHTML = liste.map((x) =>
      `<span class="vgl-chip">${esc(x.name)}<button type="button" data-vgl-weg="${esc(x.id)}" aria-label="${esc(x.name)} entfernen">×</button></span>`).join("");
    const los = leiste.querySelector("[data-vgl-los]");
    los.href = `${leiste.dataset.ziel}?ids=${liste.map((x) => x.id).join(",")}`;
    los.classList.toggle("aus", liste.length < 2);
    los.title = liste.length < 2 ? "Wählen Sie mindestens zwei Lösungen" : "";
    const h = leiste.querySelector("[data-vgl-hinweis]");
    h.textContent = hinweis || (liste.length === 1 ? "Noch mindestens eine weitere wählen" : "");
    clearTimeout(hinweisTimer);
    if (hinweis) hinweisTimer = setTimeout(() => zeigeLeiste(), 3500);
  };
  const aktualisieren = (hinweis) => { vglKnoepfe(); zeigeLeiste(hinweis); };

  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-merken]");
    if (b) {
      e.preventDefault();
      e.stopPropagation();
      const liste = vglLesen();
      const id = b.dataset.merken;
      if (liste.some((x) => x.id === id)) vglSchreiben(liste.filter((x) => x.id !== id));
      else if (liste.length >= VGL_MAX) { aktualisieren(`Höchstens ${VGL_MAX} – entfernen Sie zuerst eine Lösung`); return; }
      else vglSchreiben([...liste, { id, name: b.dataset.name || id }]);
      return;
    }
    const weg = e.target.closest("[data-vgl-weg]");
    if (weg) vglSchreiben(vglLesen().filter((x) => x.id !== weg.dataset.vglWeg));
    if (e.target.closest("[data-vgl-leeren]")) vglSchreiben([]);
    const los = e.target.closest("[data-vgl-los]");
    if (los && los.classList.contains("aus")) e.preventDefault();
  }, true);
  document.addEventListener("vgl-geaendert", () => aktualisieren());
  window.addEventListener("storage", (e) => { if (e.key === VGL_KEY) aktualisieren(); });
  aktualisieren();
}

/* ---------- Vergleich: vier Plätze + Suche; Auswahl in der Adresse (?ids=a,b,c) ---------- */
function initVergleich() {
  const form = document.querySelector("[data-vergleich-form]");
  if (!form) return;
  const MAX = VGL_MAX;
  const boxen = $$('input[name="ids"]', form);
  const box = (id) => boxen.find((b) => b.value === id);
  const nurDiff = form.querySelector("[data-nur-unterschiede]");
  const info = form.querySelector("[data-vg-info]");
  const tabelle = document.querySelector("[data-vg-tabelle]");
  const leer = document.querySelector("[data-vg-leer]");
  const picker = form.querySelector("[data-vg-picker]");
  const slots = form.querySelector("[data-vg-slots]");
  const q = form.querySelector("[data-vg-q]");
  const treffer = form.querySelector("[data-vg-treffer]");
  picker.hidden = false;
  form.querySelector(".vg-liste").hidden = true;

  // Start: Adresse, sonst die Merkliste aus Verzeichnis/Steckbrief
  let ids = liste(new URLSearchParams(location.search), "ids");
  if (!ids.length) ids = vglLesen().map((x) => x.id);
  ids = ids.filter((id) => box(id)).slice(0, MAX);

  const daten = (id) => box(id).dataset;
  const speichern = () => vglSchreiben(ids.map((id) => ({ id, name: daten(id).name })));

  const plaetze = () => {
    let html = ids.map((id) => {
      const d = daten(id);
      return `<div class="vg-slot voll"><span class="seg seg-${esc(d.segid)}">${esc(d.seg)}</span><b>${esc(d.name)}</b><small>${esc(d.an)}</small>` +
        `<button type="button" class="vg-weg" data-slot-weg="${esc(id)}" aria-label="${esc(d.name)} entfernen">×</button></div>`;
    }).join("");
    for (let i = ids.length; i < MAX; i++) {
      html += `<button type="button" class="vg-slot frei" data-slot-neu><span class="vg-plus">+</span>${i === ids.length ? "Lösung hinzufügen" : "Platz frei"}</button>`;
    }
    slots.innerHTML = html;
  };

  const trefferZeigen = () => {
    const w = q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (ids.length >= MAX) {
      treffer.innerHTML = `<p class="vg-treffer-leer">Alle ${MAX} Plätze sind belegt – entfernen Sie zuerst eine Lösung.</p>`;
      treffer.hidden = false;
      return;
    }
    const passend = boxen.filter((b) => !ids.includes(b.value)).filter((b) => {
      const t = `${b.dataset.name} ${b.dataset.an} ${b.dataset.seg}`.toLowerCase();
      return w.every((x) => t.includes(x));
    });
    const gruppen = {};
    passend.forEach((b) => (gruppen[b.dataset.seg] ||= []).push(b));
    treffer.innerHTML = Object.entries(gruppen).map(([seg, bs]) =>
      `<div class="vg-gruppe"><p>${esc(seg)}</p>${bs.map((b) =>
        `<button type="button" data-hinzu="${esc(b.value)}"><b>${esc(b.dataset.name)}</b><small>${esc(b.dataset.an)} · ${esc(b.dataset.g)}</small></button>`).join("")}</div>`).join("")
      || `<p class="vg-treffer-leer">Keine weitere Lösung gefunden.</p>`;
    treffer.hidden = false;
  };

  const zeigen = (urlSetzen) => {
    boxen.forEach((b) => (b.checked = ids.includes(b.value)));
    plaetze();
    info.textContent = ids.length === 1 ? "Wählen Sie mindestens eine weitere Lösung." : "";
    leer.hidden = ids.length > 0;
    tabelle.hidden = ids.length === 0;
    $$("tr", tabelle).forEach((tr) => {
      const zellen = $$("[data-col]", tr);
      zellen.forEach((z) => (z.hidden = !ids.includes(z.dataset.col)));
      ids.forEach((id) => { const z = zellen.find((x) => x.dataset.col === id); if (z) tr.appendChild(z); });
      const kopf = tr.querySelector(".vg-bereich th");
      if (kopf) kopf.colSpan = ids.length + 1;
    });
    $$("[data-entfernen]", tabelle).forEach((b) => (b.hidden = false));
    $$("tr[data-zeile]", tabelle).forEach((tr) => {
      const werte = $$("[data-col]", tr).filter((z) => !z.hidden).map((z) => z.dataset.v);
      tr.classList.toggle("gleich", nurDiff.checked && werte.length > 1 && werte.every((w) => w === werte[0]));
    });
    if (urlSetzen) {
      history.replaceState(null, "", location.pathname + (ids.length ? `?ids=${ids.join(",")}` : ""));
      speichern();
    }
  };

  const entfernen = (id) => { ids = ids.filter((x) => x !== id); zeigen(true); };
  form.addEventListener("click", (e) => {
    const weg = e.target.closest("[data-slot-weg]");
    if (weg) return entfernen(weg.dataset.slotWeg);
    if (e.target.closest("[data-slot-neu]")) { q.focus(); trefferZeigen(); return; }
    const hinzu = e.target.closest("[data-hinzu]");
    if (hinzu && ids.length < MAX) {
      ids = [...ids, hinzu.dataset.hinzu];
      q.value = "";
      zeigen(true);
      if (ids.length < MAX) { trefferZeigen(); q.focus(); } else treffer.hidden = true;
    }
  });
  q.addEventListener("input", trefferZeigen);
  q.addEventListener("focus", trefferZeigen);
  q.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { treffer.hidden = true; q.blur(); }
    if (e.key === "Enter") { e.preventDefault(); const erst = treffer.querySelector("[data-hinzu]"); if (erst) erst.click(); }
  });
  document.addEventListener("click", (e) => { if (!picker.contains(e.target)) treffer.hidden = true; });
  nurDiff.addEventListener("change", () => zeigen(false));
  form.addEventListener("submit", (e) => e.preventDefault());
  tabelle.addEventListener("click", (e) => {
    const b = e.target.closest("[data-entfernen]");
    if (b) entfernen(b.dataset.entfernen);
  });
  zeigen(ids.length > 0);
}

/* ---------- Suchvorschläge im Berater ---------- */
function initSuche() {
  const input = document.getElementById("vb-q");
  const box = document.getElementById("vb-sugg");
  if (!input || !box) return;
  let daten = null, sel = -1;
  const laden = async () => {
    if (daten) return daten;
    try { daten = await (await fetch(ROOT + "suche.json")).json(); } catch (_) { daten = []; }
    return daten;
  };
  const zeigen = async () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { box.hidden = true; return; }
    const w = q.split(/\s+/);
    const treffer = (await laden()).filter((t) => w.every((x) => t.such.includes(x)))
      .sort((a, b) => (b.n.startsWith(q) - a.n.startsWith(q)) || a.n.localeCompare(b.n)).slice(0, 7);
    sel = -1;
    box.innerHTML = treffer.length
      ? treffer.map((t) => `<a href="${ROOT}erp/${t.id}/"><span><b>${esc(t.name)}</b> <span class="muted">${esc(t.an)}</span></span><span class="muted">${esc(t.seg)}</span></a>`).join("")
      : `<a href="${ROOT}verzeichnis/?q=${encodeURIComponent(q)}"><span>Keine Lösung gefunden – im Verzeichnis suchen</span></a>`;
    box.hidden = false;
  };
  input.addEventListener("input", zeigen);
  input.addEventListener("focus", () => { laden(); if (input.value) zeigen(); });
  input.addEventListener("keydown", (e) => {
    const links = $$("a", box);
    if (!links.length || box.hidden) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + links.length) % links.length;
      links.forEach((a, i) => a.classList.toggle("sel", i === sel));
    } else if (e.key === "Enter" && sel >= 0) {
      e.preventDefault();
      location.href = links[sel].href;
    } else if (e.key === "Escape") box.hidden = true;
  });
  document.addEventListener("click", (e) => { if (!box.contains(e.target) && e.target !== input) box.hidden = true; });
}

/* ---------- «Zurück» auf der Steckbrief-Seite ---------- */
function initZurueck() {
  const a = document.querySelector("[data-back]");
  if (!a || !document.referrer) return;
  try {
    if (new URL(document.referrer).origin === location.origin) {
      a.addEventListener("click", (e) => { e.preventDefault(); history.back(); });
    }
  } catch (_) { /* egal */ }
}
