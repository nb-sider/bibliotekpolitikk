#!/usr/bin/env python3
"""
Bibliotekpolitikk-scraper for regjeringen.no og stortinget.no

Søker etter nøkkelord (bibliotek, lesestrategi, leselyst) i:
  - Stortingets åpne API (data.stortinget.no): saker, spørsmål, høringer
  - Regjeringen.no: søkesidene (dokumenter, nyheter, pressemeldinger)

Bruk:
    python3 bibliotekpolitikk_scraper.py            # siste 12 måneder
    python3 bibliotekpolitikk_scraper.py --deep     # henter også fulltekst av spørsmål

Krav:
    pip install requests beautifulsoup4

Resultat skrives til treff.csv og treff.json i samme mappe.
"""

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# ------------------------- KONFIGURASJON -------------------------

KEYWORDS = ["bibliotek", "lesestrategi", "leselyst",
            "nasjonalbiblioteket", "kulturarv"]  # substring, case-insensitiv
# Spørsmål til disse statsrådene får fulltekst-søk (tittel fanger ikke alt):
RELEVANTE_MINISTRE = re.compile(r"kultur|kunnskap", re.IGNORECASE)
MONTHS_BACK = 12
OUTDIR = Path(__file__).parent
HEADERS = {"User-Agent": "Mozilla/5.0 (bibliotekpolitikk-overvaking; kontakt: trond.myklebust@gmail.com)"}
PAUSE = 1.0  # sekunder mellom kall (vær høflig)

STORTINGET_API = "https://data.stortinget.no/eksport"

# ------------------------- HJELPEFUNKSJONER -------------------------

def cutoff_date():
    return datetime.now() - timedelta(days=MONTHS_BACK * 30)


def find_keywords(text):
    """Returner liste over nøkkelord som finnes i teksten."""
    if not text:
        return []
    low = text.lower()
    return [k for k in KEYWORDS if k in low]


def utdrag_med_treff(text, kws, bredde=140):
    """Tekstutsnitt rundt første forekomst av hvert nøkkelord."""
    low, biter = text.lower(), []
    for k in kws[:3]:
        i = low.find(k.lower())
        if i < 0:
            continue
        start, end = max(0, i - bredde), min(len(text), i + len(k) + bredde)
        biter.append(("…" if start > 0 else "") + text[start:end].strip()
                     + ("…" if end < len(text) else ""))
    return " […] ".join(biter)


def parse_dotnet_date(s):
    """Stortingets API bruker /Date(1700000000000+0200)/ eller ISO."""
    if not s:
        return None
    m = re.search(r"/Date\((\d+)", str(s))
    if m:
        return datetime.fromtimestamp(int(m.group(1)) / 1000)
    try:
        return datetime.fromisoformat(str(s)[:19])
    except ValueError:
        return None


def get_json(url, params=None):
    r = requests.get(url, params=params, headers=HEADERS, timeout=60)
    r.raise_for_status()
    time.sleep(PAUSE)
    return r.json()


def sporsmal_detalj(sporsmal_id):
    """Hent fulltekst for ett spørsmål. Endepunktet svarer kun med XML."""
    import xml.etree.ElementTree as ET
    r = requests.get(f"{STORTINGET_API}/enkeltsporsmal",
                     params={"NSporsmalId": sporsmal_id},
                     headers=HEADERS, timeout=60)
    r.raise_for_status()
    time.sleep(PAUSE)
    root = ET.fromstring(r.content)
    ns = "{http://data.stortinget.no}"
    return {felt: (root.findtext(f"{ns}{felt}") or "")
            for felt in ("sporsmal", "begrunnelse", "svar")}

# ------------------------- STORTINGET -------------------------

def stortinget_sessions():
    """Finn sesjons-id-er som dekker perioden (f.eks. 2024-2025, 2025-2026)."""
    data = get_json(f"{STORTINGET_API}/sesjoner", {"format": "json"})
    cutoff = cutoff_date()
    now = datetime.now()
    sessions = []
    for s in data.get("sesjoner_liste", []):
        fra = parse_dotnet_date(s.get("fra"))
        til = parse_dotnet_date(s.get("til"))
        if fra and fra > now:          # hopp over fremtidige sesjoner
            continue
        if til is None or til >= cutoff:
            sessions.append(s["id"])
    return sessions


def scrape_stortinget(deep=False, sporsmal_status=None):
    """sporsmal_status: dict id->status fra forrige kjøring. Spørsmål med
    uendret status hoppes over (fulltekst er allerede vurdert)."""
    if sporsmal_status is None:
        sporsmal_status = {}
    hits = []
    cutoff = cutoff_date()
    for ses in stortinget_sessions():
        print(f"  Sesjon {ses} ...")

        # --- Saker ---
        try:
            data = get_json(f"{STORTINGET_API}/saker", {"sesjonid": ses, "format": "json"})
            for sak in data.get("saker_liste", []):
                emner = " ".join(e.get("navn", "") for e in (sak.get("emne_liste") or []))
                blob = f"{sak.get('tittel','')} {sak.get('korttittel','')} {emner}"
                kw = find_keywords(blob)
                dato = parse_dotnet_date(sak.get("sist_oppdatert_dato"))
                if kw and (dato is None or dato >= cutoff):
                    hits.append({
                        "kilde": "Stortinget",
                        "type": sak.get("type", "sak"),
                        "dato": dato.strftime("%Y-%m-%d") if dato else "",
                        "tittel": sak.get("tittel", ""),
                        "lenke": f"https://www.stortinget.no/no/Saker-og-publikasjoner/Saker/Sak/?p={sak.get('id')}",
                        "nokkelord": ", ".join(kw),
                        "utdrag": emner,
                    })
        except Exception as e:
            print(f"    FEIL saker {ses}: {e}", file=sys.stderr)

        # --- Spørsmål (skriftlige, spørretime, interpellasjoner) ---
        # Tittel fanger ikke alt: For spørsmål til relevante statsråder
        # (kultur/kunnskap) hentes fulltekst (spørsmål, begrunnelse, svar).
        # Med --deep hentes fulltekst for ALLE spørsmål (tregt).
        sp_liste = []
        for endepunkt in ("skriftligesporsmal", "sporretimesporsmal", "interpellasjoner"):
            try:
                data = get_json(f"{STORTINGET_API}/{endepunkt}",
                                {"sesjonid": ses, "format": "json"})
                sp_liste += data.get("sporsmal_liste", [])
            except Exception as e:
                print(f"    FEIL {endepunkt} {ses}: {e}", file=sys.stderr)
        try:
            print(f"    {len(sp_liste)} spørsmål ...")
            for sp in sp_liste:
                dato = parse_dotnet_date(sp.get("sendt_dato") or sp.get("datert_dato"))
                if dato and dato < cutoff:
                    continue
                sid, status = str(sp.get("id")), str(sp.get("status") or "")
                if sporsmal_status.get(sid) == status:
                    continue  # uendret siden sist - allerede vurdert
                sporsmal_status[sid] = status
                minister = " ".join(str(sp.get(f) or "") for f in
                                    ("sporsmal_til_minister_tittel",
                                     "besvart_av_minister_tittel",
                                     "rette_vedkommende_minister_tittel"))
                blob = sp.get("tittel", "") or ""
                utdrag = ""
                if deep or RELEVANTE_MINISTRE.search(minister):
                    try:
                        det = sporsmal_detalj(sp["id"])
                        blob += " " + " ".join(det.values())
                    except Exception as e:
                        print(f"    (detalj {sp.get('id')}: {e})", file=sys.stderr)
                kw = find_keywords(blob)
                utdrag = utdrag_med_treff(blob, kw)
                if kw:
                    fra = (sp.get("sporsmal_fra") or {})
                    navn = f"{fra.get('fornavn','')} {fra.get('etternavn','')}".strip()
                    hits.append({
                        "kilde": "Stortinget",
                        "type": sp.get("type", "spørsmål"),
                        "dato": dato.strftime("%Y-%m-%d") if dato else "",
                        "tittel": sp.get("tittel", ""),
                        "lenke": f"https://www.stortinget.no/no/Saker-og-publikasjoner/Sporsmal/Skriftlige-sporsmal-og-svar/Skriftlig-sporsmal/?qnid={sp.get('id')}",
                        "nokkelord": ", ".join(kw),
                        "utdrag": f"Fra: {navn}. Til: {minister.strip()}. {utdrag}".strip(),
                    })
        except Exception as e:
            print(f"    FEIL sporsmal {ses}: {e}", file=sys.stderr)

        # --- Høringer ---
        try:
            data = get_json(f"{STORTINGET_API}/horinger", {"sesjonid": ses, "format": "json"})
            for h in data.get("horinger_liste", []):
                titler = " ".join(s.get("tittel", "") for s in (h.get("horing_sak_liste") or []))
                kw = find_keywords(titler)
                if kw:
                    hits.append({
                        "kilde": "Stortinget",
                        "type": "høring",
                        "dato": "",
                        "tittel": titler[:200],
                        "lenke": "https://www.stortinget.no/no/Hva-skjer-pa-Stortinget/Horing/",
                        "nokkelord": ", ".join(kw),
                        "utdrag": "",
                    })
        except Exception as e:
            print(f"    FEIL horinger {ses}: {e}", file=sys.stderr)

    return hits

# ------------------------- REGJERINGEN.NO -------------------------

def hent_sidetekst(url):
    """Hent hovedteksten fra en side på regjeringen.no."""
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    time.sleep(PAUSE)
    soup = BeautifulSoup(r.text, "html.parser")
    main = soup.find("main") or soup.find("article") or soup.body or soup
    return main.get_text(" ", strip=True)


def verifiser_treff(hit):
    """Sjekk at søkeordene faktisk står i sidens tekst, og hent utsnitt.
    Regjeringen.no-søket matcher også i vedlegg/PDF-fulltekst som ikke
    vises på selve siden - de merkes i stedet for å stoles blindt på."""
    try:
        tekst = hit["tittel"] + " " + hent_sidetekst(hit["lenke"])
    except Exception as e:
        print(f"    (verifisering {hit['lenke']}: {e})", file=sys.stderr)
        return hit
    kws = find_keywords(tekst)
    if kws:
        hit["nokkelord"] = ", ".join(kws)
        hit["utdrag"] = utdrag_med_treff(tekst, kws) or hit["utdrag"]
    else:
        hit["utdrag"] = ("(Søkeordet står ikke i sidens hovedtekst - "
                         "trolig treff i vedlegg eller fulltekstdokument.)")
    return hit


def scrape_regjeringen(sist_kjort=None, kjente_lenker=None):
    """Søk på regjeringen.no per nøkkelord, med datofilter, paginert.
    Ved inkrementell kjøring søkes bare fra siste kjøring minus 14 dager.
    Nye treff verifiseres mot sidens faktiske tekst."""
    if BeautifulSoup is None:
        print("  beautifulsoup4 mangler - hopper over regjeringen.no "
              "(pip install beautifulsoup4)", file=sys.stderr)
        return []

    per_url = {}  # href -> treff; samme side kan matche flere søkeord
    start = cutoff_date()
    if sist_kjort:
        try:
            start = max(start, datetime.fromisoformat(sist_kjort) - timedelta(days=14))
        except ValueError:
            pass
    frm = start.strftime("%d.%m.%Y")
    to = datetime.now().strftime("%d.%m.%Y")

    for kw in KEYWORDS:
        print(f"  Søker: {kw} ...")
        for page in range(1, 21):  # maks 20 sider per ord
            url = "https://www.regjeringen.no/no/sok/id86008/"
            params = {"term": kw, "fromdate": frm, "todate": to, "page": page}
            try:
                r = requests.get(url, params=params, headers=HEADERS, timeout=60)
                r.raise_for_status()
            except Exception as e:
                print(f"    FEIL side {page}: {e}", file=sys.stderr)
                break
            time.sleep(PAUSE)
            soup = BeautifulSoup(r.text, "html.parser")

            # Resultatlenker på regjeringen.no har alltid /idNNNNN/ i url-en.
            # Person-/organisasjonssider (/dep/<dep>/org/...) er kontorinfo,
            # ikke politikk, og holdes utenfor.
            links = [a for a in soup.select("a[href*='/id']")
                     if re.search(r"/id\d{4,}/?", a.get("href", ""))
                     and not re.search(r"/dep/[^/]+/org/", a.get("href", ""))
                     and a.get_text(strip=True)]
            resultater = 0  # ekte søketreff (med dato) på denne siden
            for a in links:
                href = a["href"].split("?")[0]
                if not href.startswith("http"):
                    href = "https://www.regjeringen.no" + href
                title = a.get_text(" ", strip=True)
                # dato og type ligger i samme listeelement for ekte søketreff;
                # meny-/footerlenker har ikke dato og hoppes over
                li = a.find_parent("li") or a.find_parent("div")
                context = li.get_text(" ", strip=True)[:300] if li else ""
                m = re.search(r"(\d{2}\.\d{2}\.\d{4})", context)
                if not m:
                    continue
                resultater += 1
                if href in per_url:
                    # allerede funnet via annet søkeord - legg bare til taggen
                    kws = per_url[href]["nokkelord"]
                    if kw not in kws:
                        per_url[href]["nokkelord"] = f"{kws}, {kw}"
                    continue
                per_url[href] = {
                    "kilde": "Regjeringen",
                    "type": "dokument/nyhet",
                    "dato": datetime.strptime(m.group(1), "%d.%m.%Y").strftime("%Y-%m-%d"),
                    "tittel": title,
                    "lenke": href,
                    "nokkelord": kw,
                    "utdrag": context,
                }
            # Stopp først når en side ikke har NOEN søketreff (reell slutt),
            # ikke når den mangler nye - en side kan bestå av dupletter fra
            # et tidligere søkeord uten at vi er ved slutten.
            if resultater == 0:
                break

    # Verifiser bare nye sider (kjente beholdes som de er)
    nye = [h for u, h in per_url.items() if u not in (kjente_lenker or set())]
    print(f"  Verifiserer {len(nye)} nye sider mot faktisk innhold ...")
    for h in nye:
        verifiser_treff(h)
    return nye

# ------------------------- MAIN -------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deep", action="store_true",
                    help="hent fulltekst av alle stortingsspørsmål (tregt)")
    ap.add_argument("--full", action="store_true",
                    help="full kjøring: glem tilstand og hent alt på nytt")
    ap.add_argument("--verifiser", action="store_true",
                    help="re-verifiser alle eksisterende regjeringen-treff "
                         "mot sidenes faktiske innhold")
    args = ap.parse_args()

    # Tidligere treff og tilstand (for inkrementell kjøring)
    prev, tilstand = {}, {}
    if not args.full:
        try:
            for h in json.loads((OUTDIR / "treff.json").read_text(encoding="utf-8")):
                h.setdefault("funnet_dato", "")
                prev[h["lenke"]] = h
            tilstand = json.loads((OUTDIR / "tilstand.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass
    sporsmal_status = tilstand.get("sporsmal_status", {})

    if args.verifiser:
        reg = [h for h in prev.values() if h["kilde"] == "Regjeringen"]
        print(f"Re-verifiserer {len(reg)} eksisterende regjeringen-treff ...")
        for h in reg:
            verifiser_treff(h)

    print("Stortinget ...")
    nye = scrape_stortinget(deep=args.deep, sporsmal_status=sporsmal_status)
    print("Regjeringen.no ...")
    nye += scrape_regjeringen(sist_kjort=tilstand.get("sist_kjort"),
                              kjente_lenker=set(prev))

    # Slå sammen: nye oppføringer får funnet_dato = i dag
    idag = datetime.now().strftime("%Y-%m-%d")
    antall_nye = 0
    for h in nye:
        if h["lenke"] in prev:
            h["funnet_dato"] = prev[h["lenke"]].get("funnet_dato", "")
        else:
            h["funnet_dato"] = idag
            antall_nye += 1
        prev[h["lenke"]] = h
    # rydd bort person-/organisasjonssider som ble fanget før filteret kom
    prev = {u: h for u, h in prev.items()
            if not re.search(r"/dep/[^/]+/org/", u)}
    hits = sorted(prev.values(), key=lambda h: h["dato"], reverse=True)

    csv_path = OUTDIR / "treff.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["kilde", "type", "dato", "tittel",
                                          "lenke", "nokkelord", "utdrag",
                                          "funnet_dato"])
        w.writeheader()
        w.writerows(hits)
    (OUTDIR / "treff.json").write_text(
        json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTDIR / "tilstand.json").write_text(
        json.dumps({"sist_kjort": idag, "sporsmal_status": sporsmal_status},
                   ensure_ascii=False), encoding="utf-8")

    print(f"\n{len(hits)} treff lagret i {csv_path} ({antall_nye} nye)")
    for k in KEYWORDS:
        n = sum(1 for h in hits if k in h["nokkelord"])
        print(f"  {k}: {n}")

    try:
        from lag_dashboard import lag_dashboard
        lag_dashboard()
    except Exception as e:
        print(f"Kunne ikke oppdatere dashboard.html: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
