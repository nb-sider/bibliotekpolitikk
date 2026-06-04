#!/usr/bin/env python3
"""
Bygger dashboard.html fra treff.json.
Kjøres automatisk av bibliotekpolitikk_scraper.py, eller manuelt:
    python3 lag_dashboard.py
Åpne dashboard.html i nettleseren (dobbeltklikk) - alt er innebygd i filen.
"""

import json
from datetime import datetime
from pathlib import Path

HER = Path(__file__).parent

MAL = """<!DOCTYPE html>
<html lang="nb">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bibliotekpolitikk – overvåking</title>
<style>
  :root {
    /* nb-framework design-tokens */
    --nb-burgundy: #550029; --ink: #17181B; --hero: #E4DFDE;
    --bg: #f2efee; --card: #ffffff; --muted: #5d5d60;
    --accent: var(--nb-burgundy); --accent2: var(--nb-burgundy); --line: #d6d0ce;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
         background: var(--bg); color: var(--ink); }
  header { background: var(--hero); color: var(--ink); padding: 28px;
           text-align: center; }
  header .logo { display: inline-flex; align-items: center; gap: 10px;
                 color: var(--nb-burgundy); margin-bottom: 10px;
                 font-weight: 700; font-size: 14px; letter-spacing: .02em; }
  header h1 { margin: 0 0 6px; font-size: 24px; }
  header p { margin: 0; color: var(--muted); font-size: 13px; }
  .wrap { max-width: 1280px; margin: 0 auto; padding: 20px 28px 60px; }
  .stats { display: flex; gap: 10px; flex-wrap: nowrap; overflow-x: auto;
           margin: 18px 0; padding: 4px 4px 8px; }
  .stat { background: var(--card); border: 1px solid var(--line); border-radius: 16px;
          padding: 10px 14px; flex: 1 1 0; min-width: 0; white-space: nowrap;
          text-align: center; }
  .stat[data-kw], .stat[data-act] { cursor: pointer; }
  .stat[data-kw]:hover, .stat[data-act]:hover { border-color: var(--accent); }
  .stat.aktiv { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent);
                background: #f6eef2; }
  .stat b { display: block; font-size: 22px; }
  .stat span { font-size: 11px; color: var(--muted); }
  .controls { display: flex; gap: 10px; flex-wrap: wrap; margin: 14px 0 20px; }
  .controls input, .controls select {
    padding: 9px 14px; border: 1px solid var(--line); border-radius: 999px;
    font-size: 14px; background: var(--card); }
  .controls input { flex: 1; min-width: 220px; }
  .controls input:focus, .controls select:focus, label.cb:focus-within {
    outline: 2px solid var(--nb-burgundy); outline-offset: 1px; }
  .hit { background: var(--card); border: 1px solid var(--line); border-radius: 24px;
         padding: 16px 20px; margin-bottom: 10px; }
  .hit a.title { color: var(--nb-burgundy); font-weight: 600; text-decoration: none; font-size: 15px; }
  .hit a.title:hover { text-decoration: underline; }
  .meta { font-size: 12px; color: var(--muted); margin-top: 5px; }
  .tag { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 11px;
         margin-right: 5px; color: #fff; }
  .tag.kilde-Regjeringen { background: var(--nb-burgundy); }
  .tag.kilde-Stortinget { background: var(--ink); }
  .tag.kw { background: #5a7d2a; }
  .tag.ny { background: #d4731c; font-weight: 700; }
  .stat.ny b { color: #d4731c; }
  label.cb { display: flex; align-items: center; gap: 6px; font-size: 14px;
             background: var(--card); border: 1px solid var(--line);
             border-radius: 999px; padding: 9px 14px; cursor: pointer; }
  button.mer { border-radius: 999px; }
  .utdrag { font-size: 13px; color: #444; margin-top: 7px; line-height: 1.45; }
  mark { background: #f3d9a4; color: inherit; border-radius: 3px; padding: 0 2px; }
  .tom { text-align: center; color: var(--muted); padding: 40px; }
  footer { text-align: center; font-size: 12px; color: var(--muted); margin-top: 30px; }
  button.mer { display: block; margin: 18px auto; padding: 10px 26px; border: 1px solid var(--line);
         border-radius: 8px; background: var(--card); cursor: pointer; font-size: 14px; }
</style>
</head>
<body>
<header>
  <div class="logo">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 26" height="26" width="20" aria-hidden="true" focusable="false">
      <path d="M1.33333 7.49151C2.06971 7.49151 2.66666 6.89962 2.66666 6.16948C2.66666 5.43934 2.06971 4.84744 1.33333 4.84744C0.596953 4.84744 0 5.43934 0 6.16948C0 6.89962 0.596953 7.49151 1.33333 7.49151Z" fill="currentColor"/>
      <path fill-rule="evenodd" clip-rule="evenodd" d="M20 0H4.44448V21.5932H20V0ZM15.1111 6.16948C15.1111 6.8996 14.5142 7.4915 13.7778 7.4915C13.0414 7.4915 12.4444 6.8996 12.4444 6.16948C12.4444 5.43935 13.0414 4.84746 13.7778 4.84746C14.5142 4.84746 15.1111 5.43935 15.1111 6.16948ZM8.88888 6.16948C8.88888 6.8996 8.29192 7.4915 7.55556 7.4915C6.8192 7.4915 6.22224 6.8996 6.22224 6.16948C6.22224 5.43935 6.8192 4.84746 7.55556 4.84746C8.29192 4.84746 8.88888 5.43935 8.88888 6.16948ZM13.7778 13.661C14.5142 13.661 15.1111 13.0691 15.1111 12.339C15.1111 11.6088 14.5142 11.017 13.7778 11.017C13.0414 11.017 12.4444 11.6088 12.4444 12.339C12.4444 13.0691 13.0414 13.661 13.7778 13.661ZM15.1111 18.5085C15.1111 19.2386 14.5142 19.8305 13.7778 19.8305C13.0414 19.8305 12.4444 19.2386 12.4444 18.5085C12.4444 17.7783 13.0414 17.1864 13.7778 17.1864C14.5142 17.1864 15.1111 17.7783 15.1111 18.5085Z" fill="currentColor"/>
      <path d="M13.7778 26C14.5142 26 15.1111 25.4081 15.1111 24.678C15.1111 23.9478 14.5142 23.3559 13.7778 23.3559C13.0414 23.3559 12.4445 23.9478 12.4445 24.678C12.4445 25.4081 13.0414 26 13.7778 26Z" fill="currentColor"/>
    </svg>
    <span>Nasjonalbiblioteket</span>
  </div>
  <h1>Bibliotekpolitikk – regjeringen.no og stortinget.no</h1>
  <p>Søkeord: __SOKEORD__ &nbsp;•&nbsp; Sist oppdatert: __OPPDATERT__</p>
</header>
<div class="wrap">
  <div class="stats" id="stats"></div>
  <div class="controls">
    <input id="sok" type="search" placeholder="Søk i tittel og utdrag …">
    <select id="fKilde"><option value="">Alle kilder</option></select>
    <select id="fKw"><option value="">Alle søkeord</option></select>
    <select id="fSort">
      <option value="ny">Nyeste først</option>
      <option value="gammel">Eldste først</option>
    </select>
    <label class="cb"><input type="checkbox" id="fNy"> Bare nye</label>
  </div>
  <div id="liste"></div>
  <button class="mer" id="mer" hidden>Vis flere</button>
  <footer>Generert av bibliotekpolitikk-scraperen · prosjekt «Svein Arne»</footer>
</div>
<script>
const DATA = __DATA__;
const SISTE_KJORING = "__SISTE__";  // treff funnet denne datoen er "nye"
const erNy = d => d.funnet_dato && d.funnet_dato === SISTE_KJORING;
const SIDE = 50;
let vist = SIDE;

const $ = id => document.getElementById(id);

// fyll filtre
const kilder = [...new Set(DATA.map(d => d.kilde))].sort();
kilder.forEach(k => $("fKilde").append(new Option(k, k)));
const kws = [...new Set(DATA.flatMap(d => d.nokkelord.split(",").map(s => s.trim())))].filter(Boolean).sort();
kws.forEach(k => $("fKw").append(new Option(k, k)));

function filtrert() {
  const q = $("sok").value.toLowerCase();
  const fk = $("fKilde").value, fw = $("fKw").value;
  let r = DATA.filter(d =>
    (!$("fNy").checked || erNy(d)) &&
    (!fk || d.kilde === fk) &&
    (!fw || d.nokkelord.includes(fw)) &&
    (!q || (d.tittel + " " + d.utdrag).toLowerCase().includes(q)));
  r.sort((a, b) => $("fSort").value === "ny"
    ? (b.dato || "").localeCompare(a.dato || "")
    : (a.dato || "").localeCompare(b.dato || ""));
  return r;
}

function esc(s) { const d = document.createElement("div"); d.textContent = s || ""; return d.innerHTML; }

// uthev søkeord (lengste først, så "nasjonalbiblioteket" ikke brytes av "bibliotek")
const kwRegex = new RegExp("(" + [...kws].sort((a, b) => b.length - a.length).join("|") + ")", "gi");
function hl(s) { return kws.length ? esc(s).replace(kwRegex, "<mark>$1</mark>") : esc(s); }

function tegn() {
  const r = filtrert();
  // statistikk (klikkbare: totalt nullstiller, søkeord/nye filtrerer)
  const ingenFilter = !$("sok").value && !$("fKilde").value && !$("fKw").value && !$("fNy").checked;
  const perKw = kws.map(k =>
    `<div class="stat${$("fKw").value === k ? " aktiv" : ""}" data-kw="${esc(k)}"><b>${DATA.filter(d => d.nokkelord.includes(k)).length}</b><span>${esc(k)}</span></div>`).join("");
  const nye = DATA.filter(erNy).length;
  $("stats").innerHTML =
    `<div class="stat${ingenFilter ? " aktiv" : ""}" data-act="alle"><b>${DATA.length}</b><span>treff totalt</span></div>` +
    `<div class="stat ny${$("fNy").checked ? " aktiv" : ""}" data-act="ny"><b>${nye}</b><span>nye siste kjøring</span></div>` + perKw +
    `<div class="stat"><b>${r.length}</b><span>i utvalget</span></div>`;
  // liste
  $("liste").innerHTML = r.slice(0, vist).map(d => `
    <div class="hit">
      <a class="title" href="${esc(d.lenke)}" target="_blank" rel="noopener">${hl(d.tittel) || "(uten tittel)"}</a>
      <div class="meta">
        ${erNy(d) ? '<span class="tag ny">NY</span>' : ""}
        <span class="tag kilde-${esc(d.kilde)}">${esc(d.kilde)}</span>
        ${d.nokkelord.split(",").map(k => `<span class="tag kw">${esc(k.trim())}</span>`).join("")}
        ${esc(d.dato)} ${d.type ? "· " + esc(d.type) : ""}
      </div>
      ${d.utdrag ? `<div class="utdrag">${hl(d.utdrag)}</div>` : ""}
    </div>`).join("") || '<div class="tom">Ingen treff med gjeldende filter.</div>';
  $("mer").hidden = r.length <= vist;
}

["sok", "fKilde", "fKw", "fSort", "fNy"].forEach(id =>
  $(id).addEventListener("input", () => { vist = SIDE; tegn(); }));
$("mer").addEventListener("click", () => { vist += SIDE; tegn(); });

// klikk på statistikk-feltene øverst
$("stats").addEventListener("click", e => {
  const el = e.target.closest(".stat");
  if (!el) return;
  if (el.dataset.kw !== undefined) {
    // klikk på søkeord: filtrer (klikk igjen for å fjerne)
    $("fKw").value = $("fKw").value === el.dataset.kw ? "" : el.dataset.kw;
  } else if (el.dataset.act === "alle") {
    $("sok").value = ""; $("fKilde").value = ""; $("fKw").value = ""; $("fNy").checked = false;
  } else if (el.dataset.act === "ny") {
    $("fNy").checked = !$("fNy").checked;
  } else {
    return;
  }
  vist = SIDE; tegn();
});
tegn();
</script>
</body>
</html>
"""


def lag_dashboard():
    treff = json.loads((HER / "treff.json").read_text(encoding="utf-8"))
    try:
        siste = json.loads((HER / "tilstand.json").read_text(encoding="utf-8")
                           ).get("sist_kjort", "")
    except FileNotFoundError:
        siste = ""
    try:
        from bibliotekpolitikk_scraper import KEYWORDS as sokeord
    except Exception:
        sokeord = sorted({k.strip() for t in treff
                          for k in t["nokkelord"].split(",") if k.strip()})
    html = (MAL
            .replace("__OPPDATERT__", datetime.now().strftime("%d.%m.%Y kl. %H:%M"))
            .replace("__SOKEORD__", ", ".join(sokeord))
            .replace("__SISTE__", siste)
            .replace("__DATA__", json.dumps(treff, ensure_ascii=False)
                     .replace("</", "<\\/")))  # unngå at </script> i data bryter siden
    (HER / "dashboard.html").write_text(html, encoding="utf-8")
    print(f"dashboard.html oppdatert ({len(treff)} treff)")


if __name__ == "__main__":
    lag_dashboard()
