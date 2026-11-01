"""Dove_Volo - Tappa 1: test delle fonti dati.

Scarica i file pubblici, li misura e scrive REPORT_FONTI.md.
Solo libreria standard di Python: non serve installare nulla.

    python test_fonti.py             usa i file gia' scaricati, se ci sono
    python test_fonti.py --aggiorna  riscarica tutto

Non tocca flightsfrom.com.
"""
import csv
import gzip
import hashlib
import json
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATI = BASE / "dati_scaricati"
NOTE = BASE / "note_report.md"
REPORT = BASE.parent.parent / "docs" / "REPORT_FONTI.md"
SEGNAPOSTO = "<!--DATI-->"

UA = "Dove_Volo-test-fonti/0.0 (progetto personale, non commerciale; https://github.com/dedavi97)"
PAUSA_WIKI = 1.0  # secondi tra una richiesta e l'altra verso Wikipedia e Wikidata
OGGI = date.today()

RAW = "https://raw.githubusercontent.com/{}/airline-route-data/main/{}"
API = "https://api.github.com/repos/{}/airline-route-data/{}"
REPO = {"omaxim": "omaxim", "jonty": "Jonty"}
URL_AEROPORTI = "https://davidmegginson.github.io/ourairports-data/airports.csv"

UE27 = "AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split()
PAESI_AREA = set(UE27) | set(
    "GB IE NO IS CH LI AL BA ME RS MK XK MD UA BY TR GE AM AZ CY FO GI IM JE GG SJ".split()
)
LON_MAX_RUSSIA = 60.0

CAMPIONI = "TRN MXP BGY OTP TBS KUT BCN STN ATH KEF".split()
LOW_COST = {
    "Ryanair (FR)": {"FR"},
    "easyJet (U2/EC/DS)": {"U2", "EC", "DS"},
    "Wizz Air (W6/W4/W9)": {"W6", "W4", "W9"},
    "Volotea (V7)": {"V7"},
    "Vueling (VY)": {"VY"},
}
# Dal cambio d'orario del 25 ottobre: le giornate prima sono ancora orario estivo.
INIZIO_ORARIO_INVERNALE = "2026-10-25"
LETTERE_GIORNI = "LMMGVSD"


def scarica(url, percorso, aggiorna=False):
    if percorso.exists() and not aggiorna:
        return percorso
    percorso.parent.mkdir(parents=True, exist_ok=True)
    richiesta = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(richiesta, timeout=180) as r:
        percorso.write_bytes(r.read())
    return percorso


def leggi_url_json(url):
    richiesta = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(richiesta, timeout=60) as r:
        return json.load(r)


def json_con_cache(url, percorso, aggiorna=False):
    if percorso.exists() and not aggiorna:
        return json.loads(percorso.read_text(encoding="utf-8"))
    dati = leggi_url_json(url)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(json.dumps(dati, ensure_ascii=False), encoding="utf-8")
    return dati


def wiki_json(url, percorso, aggiorna=False):
    """Come json_con_cache, ma lenta e senza salvare le risposte di errore.

    Se il server e' sotto carico (maxlag) aspetta e riprova poche volte, come chiede Wikimedia.
    """
    if percorso.exists() and not aggiorna:
        return json.loads(percorso.read_text(encoding="utf-8"))
    for tentativo in range(5):
        dati = leggi_url_json(url)
        time.sleep(PAUSA_WIKI)
        errore = dati.get("error", {}).get("code")
        if errore != "maxlag":
            break
        time.sleep(10 * (tentativo + 1))
    if "error" in dati:
        raise RuntimeError(f"Wikipedia/Wikidata ha risposto {dati['error'].get('code')}: {url}")
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(json.dumps(dati, ensure_ascii=False), encoding="utf-8")
    return dati


# ---------------------------------------------------------------- aeroporti e area


def carica_aeroporti(aggiorna):
    percorso = scarica(URL_AEROPORTI, DATI / "airports.csv", aggiorna)
    per_iata = {}
    with open(percorso, encoding="utf-8", newline="") as f:
        for riga in csv.DictReader(f):
            codice = riga["iata_code"].strip()
            if not codice or riga["type"] == "closed":
                continue
            attuale = per_iata.get(codice)
            if attuale is None or riga["scheduled_service"] == "yes":
                per_iata[codice] = riga
    return per_iata


def in_area_paese_lon(paese, lon):
    if paese == "RU":
        return lon is not None and lon < LON_MAX_RUSSIA
    return paese in PAESI_AREA


def numero(valore):
    try:
        return float(valore)
    except (TypeError, ValueError):
        return None


class Area:
    """Dice se un aeroporto e' nell'area. Fonte: OurAirports; se manca, il file rotte."""

    def __init__(self, aeroporti):
        self.aeroporti = aeroporti
        self.supplenti = {}

    def contiene(self, codice):
        riga = self.aeroporti.get(codice)
        if riga:
            return in_area_paese_lon(riga["iso_country"], numero(riga["longitude_deg"]))
        riga = self.supplenti.get(codice)
        if riga:
            return in_area_paese_lon(riga.get("country_code"), numero(riga.get("longitude")))
        return False


def nome_citta(codice, aeroporti, rotte):
    if codice in rotte and rotte[codice].get("city_name"):
        return rotte[codice]["city_name"]
    riga = aeroporti.get(codice)
    return riga["municipality"] if riga else "?"


# ---------------------------------------------------------------- fonti rotte


def info_repo(chiave, aggiorna):
    repo = REPO[chiave]
    cartella = DATI / "github"
    commit = json_con_cache(
        API.format(repo, "commits?path=airline_routes.json&per_page=1"),
        cartella / f"{chiave}_ultimo_commit_file.json", aggiorna)
    corse = json_con_cache(
        API.format(repo, "actions/runs?per_page=10"),
        cartella / f"{chiave}_corse.json", aggiorna)
    testo = commit[0]["commit"]["committer"]["date"]
    data_file = datetime.strptime(testo, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).date()
    return {
        "data_file": data_file,
        "giorni_fa": (OGGI - data_file).days,
        "corse": Counter(c["conclusion"] for c in corse["workflow_runs"]),
    }


def analizza_file(dati, area):
    """Conta aeroporti, rotte e campi nell'area."""
    aeroporti_area = {c for c in dati if area.contiene(c)}
    rotte = {}
    campi_rotta, campi_compagnia = Counter(), Counter()
    for origine in aeroporti_area:
        for rotta in dati[origine].get("routes", []):
            if area.contiene(rotta["iata"]):
                rotte[(origine, rotta["iata"])] = rotta
                campi_rotta.update(rotta.keys())
                for compagnia in rotta.get("carriers", []):
                    campi_compagnia.update(compagnia.keys())
    con_rotte = {o for o, _ in rotte}
    ritorno = sum(1 for (a, b) in rotte if (b, a) in rotte)
    return {
        "aeroporti": len(aeroporti_area),
        "aeroporti_con_rotte": len(con_rotte),
        "rotte": rotte,
        "ritorno_pct": 100 * ritorno / max(len(rotte), 1),
        "campi_rotta": campi_rotta,
        "campi_compagnia": campi_compagnia,
    }


# ---------------------------------------------------------------- file giornalieri


def carica_giornalieri(aggiorna):
    elenco = json_con_cache(API.format("omaxim", "contents/days"),
                            DATI / "github" / "omaxim_days.json", aggiorna)
    giornate = []
    for voce in elenco:
        percorso = scarica(voce["download_url"], DATI / "days" / voce["name"], aggiorna)
        with gzip.open(percorso, "rt", encoding="utf-8") as f:
            giornate.append(json.load(f))
    return sorted(giornate, key=lambda g: g["date"])


def durata_minuti(volo):
    try:
        ore_p, min_p = map(int, volo[3].split(":"))
        ore_a, min_a = map(int, volo[4].split(":"))
        return ((ore_a * 60 + min_a - int(volo[6])) - (ore_p * 60 + min_p - int(volo[5]))) % 1440
    except (ValueError, IndexError):
        return None


def ricostruisci_settimana(giornate, area):
    """Per ogni aeroporto e giorno della settimana usa la giornata piu' recente che lo contiene.

    Solo orario invernale. Conta i voli per rotta e compagnia, come farebbe l'assemblaggio
    settimanale di omaxim se le giornate fossero complete.
    """
    invernali = [g for g in giornate if g["date"] >= INIZIO_ORARIO_INVERNALE]
    scelta = defaultdict(dict)
    for giornata in invernali:  # in ordine di data: la piu' recente sovrascrive
        giorno = date.fromisoformat(giornata["date"]).isoweekday()
        for aeroporto in giornata["flights"]:
            scelta[aeroporto][giorno] = giornata

    rotte = {}
    duplicati = totale = 0
    giorni_coperti = Counter()
    for aeroporto, per_giorno in scelta.items():
        if not area.contiene(aeroporto):
            continue
        giorni_coperti[len(per_giorno)] += 1
        for giorno, giornata in per_giorno.items():
            visti = set()
            for volo in giornata["flights"][aeroporto]:
                totale += 1
                chiave = (volo[0], volo[1], volo[2], volo[3])
                if chiave in visti:
                    duplicati += 1
                    continue
                visti.add(chiave)
                if not area.contiene(volo[0]):
                    continue
                rotta = rotte.setdefault(
                    (aeroporto, volo[0]),
                    {"compagnie": defaultdict(lambda: {"voli": 0, "giorni": set()}), "durate": []})
                voce = rotta["compagnie"][volo[1]]
                voce["voli"] += 1
                voce["giorni"].add(giorno)
                minuti = durata_minuti(volo)
                if minuti:
                    rotta["durate"].append(minuti)
    return {
        "rotte": rotte,
        "giorni_coperti": giorni_coperti,
        "duplicati": duplicati,
        "totale": totale,
        "giornate": invernali,
        "per_giorno": {a: g for a, g in scelta.items() if area.contiene(a)},
    }


def voli_rotta(rotta):
    return sum(c["voli"] for c in rotta["compagnie"].values())


def giorni_rotta(rotta):
    tutti = set()
    for c in rotta["compagnie"].values():
        tutti |= c["giorni"]
    return tutti


def giorni_lettere(giorni):
    return "".join(LETTERE_GIORNI[i - 1] if i in giorni else "·" for i in range(1, 8))


def convenzione_giorni(rotte_omaxim, ricostruite):
    """Il giorno 1 di operating_days e' lunedi' o domenica? Lo misura sulle rotte con pochi giorni."""
    lun = dom = n = 0
    for chiave, rotta in rotte_omaxim.items():
        giorni = set(rotta.get("operating_days") or [])
        if chiave not in ricostruite or not 1 <= len(giorni) <= 3:
            continue
        reali = giorni_rotta(ricostruite[chiave])
        if not 1 <= len(reali) <= 3:
            continue
        n += 1
        lun += giorni == reali
        dom += {(g + 5) % 7 + 1 for g in giorni} == reali
    return {"rotte": n, "lunedi": lun, "domenica": dom}


# ---------------------------------------------------------------- Wikipedia

RE_COMMENTO = re.compile(r"<!--.*?-->", re.S)
RE_REF = re.compile(r"<ref\b[^>/]*/>|<ref\b[^>]*>.*?</ref>", re.S | re.I)
RE_LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]")
RE_BEGINS = re.compile(r"\b(begins|resumes|ends)\b\s*([^)}\n,<]*)", re.I)
RE_ETICHETTA = re.compile(r"'''\s*([^']+?)\s*:?\s*'''\s*:?")


def blocchi_template(testo, nome):
    """Restituisce il contenuto di ogni {{nome ...}}, rispettando le graffe annidate."""
    risultati = []
    for trovato in re.finditer(r"\{\{\s*" + nome, testo, re.I):
        inizio = trovato.end()
        i, profondita = inizio, 1
        while i < len(testo) and profondita:
            if testo.startswith("{{", i):
                profondita += 1
                i += 2
            elif testo.startswith("}}", i):
                profondita -= 1
                i += 2
            else:
                i += 1
        risultati.append((trovato.start(), testo[inizio:i - 2]))
    return risultati


def separa_pipe(testo):
    """Divide sui | fuori da link e template."""
    parti, attuale, graffe, quadre, i = [], [], 0, 0, 0
    while i < len(testo):
        coppia = testo[i:i + 2]
        if coppia == "{{":
            graffe += 1
        elif coppia == "}}":
            graffe -= 1
        elif coppia == "[[":
            quadre += 1
        elif coppia == "]]":
            quadre -= 1
        if coppia in ("{{", "}}", "[[", "]]"):
            attuale.append(coppia)
            i += 2
            continue
        if testo[i] == "|" and not graffe and not quadre:
            parti.append("".join(attuale))
            attuale = []
        else:
            attuale.append(testo[i])
        i += 1
    parti.append("".join(attuale))
    return [p.strip() for p in parti]


def data_futura(testo):
    """True, False, o None se la data non si capisce."""
    pulito = re.sub(r"[{}|\[\]]", " ", testo)
    for formato, schema in (("%d %B %Y", r"\d{1,2} [A-Z][a-z]+ \d{4}"),
                            ("%B %d %Y", r"[A-Z][a-z]+ \d{1,2},? \d{4}"),
                            ("%B %Y", r"[A-Z][a-z]+ \d{4}")):
        m = re.search(schema, pulito)
        if m:
            try:
                return datetime.strptime(m.group(0).replace(",", ""), formato).date() > OGGI
            except ValueError:
                continue
    return None


def sezione_passeggeri(testo):
    """Taglia il testo della sezione destinazioni, escludendo il cargo."""
    m = re.search(r"^==+\s*Airlines and destinations\s*==+\s*$", testo, re.M | re.I)
    if not m:
        return None
    resto = testo[m.end():]
    fine = re.search(r"^==[^=].*==\s*$", resto, re.M)
    sezione = resto[:fine.start()] if fine else resto
    cargo = re.search(r"^===+\s*Cargo.*$", sezione, re.M | re.I)
    return sezione[:cargo.start()] if cargo else sezione


def analizza_pagina(wikitesto):
    testo = RE_REF.sub("", RE_COMMENTO.sub("", wikitesto))
    sezione = sezione_passeggeri(testo)
    esito = {"sezione": sezione is not None, "template": False, "righe": 0, "voci": [],
             "righe_seasonal": 0, "righe_begins": 0}
    if sezione is None:
        return esito
    blocchi = blocchi_template(sezione, r"Airport[- ]dest(?:ination)?[- ]list")
    esito["template"] = bool(blocchi)
    for _, blocco in blocchi:
        parti = [p for p in separa_pipe(blocco) if not re.match(r"^\w*title\s*=|^\w+\s*=\s*\S*$", p)]
        parti = [p for p in parti if p]
        for compagnia, destinazioni in zip(parti[0::2], parti[1::2]):
            esito["righe"] += 1
            link = RE_LINK.search(compagnia)
            nome = (link.group(2) or link.group(1)) if link else compagnia
            ha_stagionale = ha_inizio = False
            for segmento in re.split(r"<br\s*/?>|\n", destinazioni, flags=re.I):
                etichetta = RE_ETICHETTA.search(segmento)
                corrente = etichetta.group(1).strip().lower() if etichetta else ""
                stagionale = "seasonal" in corrente
                charter = "charter" in corrente
                link_trovati = list(RE_LINK.finditer(segmento))
                for pos, lk in enumerate(link_trovati):
                    if lk.group(1).lower().startswith(("file:", "image:")):
                        continue
                    fine = link_trovati[pos + 1].start() if pos + 1 < len(link_trovati) else len(segmento)
                    nota = RE_BEGINS.search(segmento[lk.end():fine])
                    voce = {"compagnia": nome, "pagina": lk.group(1).strip(),
                            "nome": (lk.group(2) or lk.group(1)).strip(),
                            "stagionale": stagionale, "charter": charter,
                            "nota": None, "futura": None}
                    if nota:
                        voce["nota"] = nota.group(1).lower()
                        voce["data"] = nota.group(2).strip()
                        voce["futura"] = data_futura(nota.group(2))
                    esito["voci"].append(voce)
                    ha_stagionale |= stagionale
                    ha_inizio |= bool(nota and nota.group(1).lower() == "begins")
            esito["righe_seasonal"] += ha_stagionale
            esito["righe_begins"] += ha_inizio
    return esito


def api_wiki(parametri):
    return "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"format": "json", "formatversion": 2, "maxlag": 5, **parametri})


def api_wikidata(parametri):
    return "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
        {"format": "json", "formatversion": 2, "maxlag": 5, **parametri})


def titolo_da_iata(codice, cartella, aggiorna):
    """IATA -> elemento Wikidata -> titolo della pagina inglese."""
    cerca = wiki_json(api_wikidata({"action": "query", "list": "search",
                                    "srsearch": f"haswbstatement:P238={codice}"}),
                      cartella / f"cerca_{codice}.json", aggiorna)
    risultati = cerca["query"]["search"]
    if not risultati:
        return None
    ids = "|".join(r["title"] for r in risultati[:5])
    entita = wiki_json(api_wikidata({"action": "wbgetentities", "ids": ids, "props": "sitelinks",
                                     "sitefilter": "enwiki"}),
                       cartella / f"link_{codice}.json", aggiorna)["entities"]
    for r in risultati[:5]:
        link = entita.get(r["title"], {}).get("sitelinks", {}).get("enwiki")
        if link:
            return link["title"]
    return None


def impronta(voci):
    """Nome di cache che cambia se cambia il gruppo di titoli."""
    return hashlib.sha1("|".join(voci).encode("utf-8")).hexdigest()[:12]


def risolvi_pagine(pagine, cartella, aggiorna):
    """Titolo pagina Wikipedia -> codice IATA, passando da Wikidata."""
    pagine = sorted(pagine)
    titolo_a_q, risultato = {}, {}
    for i in range(0, len(pagine), 50):
        gruppo = pagine[i:i + 50]
        r = wiki_json(api_wiki({"action": "query", "redirects": 1, "prop": "pageprops",
                                "ppprop": "wikibase_item", "titles": "|".join(gruppo)}),
                      cartella / f"pagine_{impronta(gruppo)}.json", aggiorna)["query"]
        rinomina = {}
        for lista in (r.get("normalized", []), r.get("redirects", [])):
            for voce in lista:
                rinomina[voce["from"]] = voce["to"]
        per_titolo = {p["title"]: p.get("pageprops", {}).get("wikibase_item") for p in r["pages"]}
        for titolo in gruppo:
            attuale, passi = titolo, 0
            while attuale in rinomina and passi < 5:
                attuale, passi = rinomina[attuale], passi + 1
            titolo_a_q[titolo] = per_titolo.get(attuale)
    tutte_q = sorted({q for q in titolo_a_q.values() if q})
    q_a_iata = {}
    for i in range(0, len(tutte_q), 50):
        gruppo = tutte_q[i:i + 50]
        entita = wiki_json(api_wikidata({"action": "wbgetentities", "ids": "|".join(gruppo),
                                         "props": "claims"}),
                           cartella / f"entita_{impronta(gruppo)}.json", aggiorna)["entities"]
        for q, e in entita.items():
            for affermazione in e.get("claims", {}).get("P238", []):
                try:
                    q_a_iata[q] = affermazione["mainsnak"]["datavalue"]["value"]
                    break
                except KeyError:
                    continue
    for titolo, q in titolo_a_q.items():
        risultato[titolo] = q_a_iata.get(q)
    return risultato


def test_wikipedia(area, ricostruite, rotte_omaxim, aggiorna):
    cartella = DATI / "wikipedia"
    richieste = 0
    pagine = {}
    for codice in CAMPIONI:
        titolo = titolo_da_iata(codice, cartella, aggiorna)
        richieste += 2
        if not titolo:
            pagine[codice] = {"titolo": None, "esito": None}
            continue
        r = wiki_json(api_wiki({"action": "parse", "redirects": 1, "prop": "wikitext", "page": titolo}),
                      cartella / f"pagina_{codice}.json", aggiorna)
        richieste += 1
        esito = analizza_pagina(r["parse"]["wikitext"])
        pagine[codice] = {"titolo": titolo, "esito": esito}

    tutte = {v["pagina"] for p in pagine.values() if p["esito"] for v in p["esito"]["voci"]}
    mappa = risolvi_pagine(tutte, cartella, aggiorna)
    richieste += 2 * (len(tutte) // 50 + 1)

    for codice, p in pagine.items():
        if not p["esito"]:
            continue
        voci = p["esito"]["voci"]
        for v in voci:
            v["iata"] = mappa.get(v["pagina"])
        p["risolte_pct"] = 100 * sum(1 for v in voci if v["iata"]) / max(len(voci), 1)
        wiki_area = {v["iata"] for v in voci if v["iata"] and area.contiene(v["iata"])}
        p["wiki_area"] = wiki_area
        file_ott = {b for (a, b) in rotte_omaxim if a == codice}
        file_giorn = {b for (a, b) in ricostruite if a == codice}
        p["solo_wiki"] = wiki_area - file_ott - file_giorn
        p["solo_dati"] = (file_ott | file_giorn) - wiki_area
        p["comuni"] = wiki_area & (file_ott | file_giorn)
        normali = {v["iata"] for v in voci if v["iata"] and not v["stagionale"]}
        stagionali = {v["iata"] for v in voci if v["iata"] and v["stagionale"]} - normali
        sparite = file_ott - file_giorn
        p["sparite"] = len(sparite)
        p["sparite_stagionali"] = len(sparite & stagionali)
        p["sparite_normali"] = len(sparite & normali)
        p["sparite_assenti"] = len(sparite - stagionali - normali)
        p["stagionali_area"] = len(stagionali & wiki_area)
        p["stagionali_volano_ora"] = len(stagionali & wiki_area & file_giorn)
    return {"pagine": pagine, "richieste": richieste}


# ---------------------------------------------------------------- scrittura del report


def punti(n):
    return f"{n:,}".replace(",", ".")


def stima_file_finale(analisi, ricostruzione, aeroporti, area, fonti):
    """Costruisce per prova il JSON del sito, con il dizionario delle compagnie, e ne misura il peso."""
    rotte_o, rr = analisi["omaxim"]["rotte"], ricostruzione["rotte"]
    nomi = {c["iata"]: c.get("name") for r in rotte_o.values() for c in r.get("carriers", [])}
    usate = {k for r in rr.values() for k in r["compagnie"]}
    rotte = []
    for chiave in sorted(set(rr) | set(rotte_o)):
        g, o = rr.get(chiave), rotte_o.get(chiave)
        voce = {"da": chiave[0], "a": chiave[1], "stato": "attiva" if g else "stagionale",
                "km": o["km"] if o else None, "vista_ultima": "2026-11-08"}
        if g:
            voce["durata_min"] = int(statistics.median(g["durate"])) if g["durate"] else None
            voce["compagnie"] = [{"iata": k, "voli_sett": v["voli"],
                                  "giorni": "".join("1" if i in v["giorni"] else "0" for i in range(1, 8))}
                                 for k, v in g["compagnie"].items()]
        else:
            voce["compagnie"] = [{"iata": c["iata"]} for c in o.get("carriers", [])]
        rotte.append(voce)
    codici = {c for k in rotte for c in (k["da"], k["a"])}
    dati = {"tipo": "dove_volo_dati", "versione_formato": 1, "aggiornato": "2026-11-08",
            "compagnie": {k: nomi.get(k) for k in usate},
            "aeroporti": {c: {"nome": aeroporti[c]["name"] if c in aeroporti else "?",
                              "citta": nome_citta(c, aeroporti, fonti["omaxim"]),
                              "paese": aeroporti[c]["iso_country"] if c in aeroporti else "?",
                              "lat": 45.123, "lon": 7.123} for c in codici},
            "rotte": rotte}
    grezzo = json.dumps(dati, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    senza_nome = sorted(k for k in usate if not nomi.get(k))
    return {"mb": len(grezzo) / 1e6, "gz_mb": len(gzip.compress(grezzo)) / 1e6, "rotte": len(rotte),
            "compagnie": len(usate), "senza_nome": senza_nome}


def tabella(intestazione, righe):
    testo = ["| " + " | ".join(intestazione) + " |", "|" + "---|" * len(intestazione)]
    testo += ["| " + " | ".join(str(c) for c in r) + " |" for r in righe]
    return "\n".join(testo)


def ottieni_compagnie(rotta):
    return {c["iata"] for c in rotta.get("carriers", [])}


def sezione_file(info, analisi, percorsi, giornate, ricostruzione, conv, aeroporti, area, fonti):
    out = ["## 1. I file di omaxim e Jonty, misurati", ""]
    righe = []
    for chiave in ("omaxim", "jonty"):
        a, i = analisi[chiave], info[chiave]
        corse = ", ".join(f"{v} {k}" for k, v in i["corse"].items())
        righe.append((chiave, f"{i['data_file']} ({i['giorni_fa']} giorni fa)", corse,
                      f"{percorsi[chiave].stat().st_size / 1e6:.0f} MB",
                      f"{a['aeroporti']} (con rotte: {a['aeroporti_con_rotte']})",
                      f"{len(a['rotte']):,}".replace(",", "."),
                      f"{a['ritorno_pct']:.1f}%"))
    out.append(tabella(["Fonte", "Ultimo aggiornamento del file", "Ultime 10 esecuzioni automatiche",
                        "Dimensione", "Aeroporti nell'area", "Rotte nell'area (A>B)",
                        "Rotte che hanno anche il ritorno"], righe))
    out += ["", "**Campi presenti** (percentuali sulle rotte nell'area):", ""]
    for chiave in ("omaxim", "jonty"):
        a = analisi[chiave]
        tot = max(len(a["rotte"]), 1)
        campi = ", ".join(f"`{k}` {100 * v / tot:.0f}%" for k, v in sorted(a["campi_rotta"].items()))
        comp = ", ".join(f"`{k}`" for k in sorted(a["campi_compagnia"]))
        out += [f"- **{chiave}**, per rotta: {campi}", f"- **{chiave}**, per compagnia: {comp}"]
    rotte_o = analisi["omaxim"]["rotte"]
    tot = max(len(rotte_o), 1)
    con_voli = sum(1 for r in rotte_o.values() if r.get("flights_per_week"))
    con_giorni = sum(1 for r in rotte_o.values() if r.get("operating_days"))
    con_pax = sum(1 for r in rotte_o.values() if r.get("passengers_per_day"))
    out += ["",
            f"Nel file omaxim i campi hanno un valore utile su: voli a settimana {100 * con_voli / tot:.1f}%, "
            f"giorni operativi {100 * con_giorni / tot:.1f}%, passeggeri al giorno {100 * con_pax / tot:.1f}%. "
            "I voli a settimana e i giorni sono **per rotta**, non per compagnia.",
            ""]

    out += ["### I file giornalieri di omaxim (`days/`)", ""]
    n_compl = sum(1 for g in giornate if not g.get("partial"))
    righe = []
    for g in giornate:
        nell_area = sum(1 for c in g["flights"] if area.contiene(c))
        righe.append((g["date"], "parziale" if g.get("partial") else "completa",
                      len(g["flights"]), nell_area, sum(len(v) for v in g["flights"].values())))
    out.append(f"Giornate disponibili: {len(giornate)}, complete: {n_compl}. "
               "Il file settimanale viene creato solo con 7 giornate complete di fila.")
    out += ["", tabella(["Data", "Stato", "Aeroporti (tutto il mondo)", "Aeroporti nell'area",
                         "Voli (tutto il mondo)"], righe), ""]
    rr = ricostruzione["rotte"]
    copertura = ricostruzione["giorni_coperti"]
    settimana_piena = copertura.get(7, 0)
    aer_con_rotte = {a for a, _ in rr}
    solo_ott = set(rotte_o) - set(rr)
    solo_giorn = set(rr) - set(rotte_o)
    complete = {a for a, per_giorno in ricostruzione["per_giorno"].items() if len(per_giorno) == 7}
    sparite_complete = sum(1 for (a, _) in solo_ott if a in complete)
    sparite_doppie = sum(1 for (a, b) in solo_ott if (b, a) in solo_ott)
    con_ritorno = sum(1 for (a, b) in rr if (b, a) in rr)
    voli_zero = sum(1 for k in solo_ott if not rotte_o[k].get("flights_per_week"))
    voli_pochi = sum(1 for k in solo_ott if 0 < (rotte_o[k].get("flights_per_week") or 0) <= 2)
    out += [
        "**Prova di ricostruzione.** Ho rifatto io il conto settimanale con le giornate "
        f"dal {INIZIO_ORARIO_INVERNALE} in poi ({len(ricostruzione['giornate'])} giornate): per ogni aeroporto "
        "e giorno della settimana prendo la giornata più recente che lo contiene.",
        "",
        f"- Aeroporti dell'area con tutti e 7 i giorni: **{settimana_piena}** su {sum(copertura.values())}; "
        f"con rotte nell'area: {len(aer_con_rotte)}.",
        f"- Rotte nell'area ricostruite: **{len(rr):,}**".replace(",", ".") +
        f" (file del {info['omaxim']['data_file']}: {len(rotte_o):,}).".replace(",", "."),
        f"- Rotte solo nel file di ottobre (probabilmente estive o cessate): {len(solo_ott):,}.".replace(",", "."),
        f"- Rotte solo nelle giornate (probabilmente nuove o invernali): {len(solo_giorn):,}.".replace(",", "."),
        f"- Di quelle solo a ottobre: {punti(sparite_complete)} partono da aeroporti con settimana completa "
        f"(quindi l'assenza è reale, non un buco); {punti(sparite_doppie)} mancano in entrambi i sensi; "
        f"nel file di ottobre {punti(voli_zero)} avevano 0 voli a settimana e {punti(voli_pochi)} ne avevano 1 o 2.",
        f"- Rotte ricostruite che hanno anche il ritorno: {100 * con_ritorno / max(len(rr), 1):.1f}%.",
        f"- Voli doppi eliminati: {ricostruzione['duplicati']} su {ricostruzione['totale']:,}.".replace(",", "."),
        f"- Convenzione dei giorni nel file omaxim, su {conv['rotte']} rotte con massimo 3 giorni: "
        f"se 1 = lunedì coincidono {conv['lunedi']}, se 1 = domenica coincidono {conv['domenica']}.",
        "",
    ]

    fuori = [(c, v.get("country_code"), v.get("city_name"),
              sum(1 for r in v.get("routes", []) if area.contiene(r["iata"])))
             for c, v in fonti["omaxim"].items()
             if v.get("continent") == "EU" and not area.contiene(c) and
             not (v.get("country_code") == "RU")]
    senza_oa = [c for c in fonti["omaxim"] if c not in aeroporti]
    senza_oa_area = sorted(c for c in senza_oa if c in analisi["omaxim"]["aeroporti_con_rotte_set"])
    diversi = [(c, v.get("country_code"), aeroporti[c]["iso_country"])
               for c, v in fonti["omaxim"].items()
               if c in aeroporti and v.get("country_code") != aeroporti[c]["iso_country"]
               and (area.contiene(c) or v.get("country_code") in PAESI_AREA)]
    out += ["### Controlli sull'area geografica", "",
            "Aeroporti segnati in Europa dal file omaxim ma **fuori** dalla nostra area:", ""]
    out.append(tabella(["Codice", "Paese", "Città", "Rotte verso l'area"], sorted(fuori)) if fuori else "Nessuno.")
    melilla = [c for c in analisi["omaxim"]["aeroporti_con_rotte_set"] if c in ("MLN", "JCU")]
    out += ["",
            f"Aeroporti spagnoli in Nord Africa con rotte: {', '.join(melilla) or 'nessuno'}.",
            f"Codici del file omaxim che OurAirports non conosce: {len(senza_oa)} nel mondo, "
            f"{len(senza_oa_area)} nell'area con rotte ({', '.join(senza_oa_area) or 'nessuno'}).",
            f"Aeroporti dell'area con paese diverso tra le due fonti: "
            f"{', '.join(f'{c} ({a}/{b})' for c, a, b in diversi[:25]) or 'nessuno'}"
            f"{' ...' if len(diversi) > 25 else ''}.",
            ""]
    return out


def sezione_campioni(analisi, ricostruzione, aeroporti, fonti):
    legenda = ["Confronta queste liste con quello che sai. Legenda delle colonne:", "",
           "- **Giornate**: voli della settimana contati dai file giornalieri (orario invernale, novembre), "
           "per compagnia, e giorni in cui vola qualcuno.",
           "- **omaxim ott**: voli a settimana nel file del 4 ottobre (ancora orario estivo).",
           "- **Jonty**: `sì` se la rotta c'è nel file di Jonty del 25 settembre.",
           "- Solo rotte con entrambi gli aeroporti nell'area.", ""]
    out = ["## 2. I 10 aeroporti campione", "", "L'elenco completo delle mete è nell'allegato in fondo.", ""]
    riepilogo = []
    dettaglio = []
    rotte_o, rotte_j = analisi["omaxim"]["rotte"], analisi["jonty"]["rotte"]
    rr = ricostruzione["rotte"]
    for codice in CAMPIONI:
        mete_o = {b for (a, b) in rotte_o if a == codice}
        mete_j = {b for (a, b) in rotte_j if a == codice}
        mete_g = {b for (a, b) in rr if a == codice}
        riepilogo.append((codice, nome_citta(codice, aeroporti, fonti["omaxim"]), len(mete_g), len(mete_o), len(mete_j),
                          " ".join(sorted(mete_j - mete_o)) or "-",
                          " ".join(sorted(mete_o - mete_j)) or "-",
                          len(mete_o - mete_g), len(mete_g - mete_o)))
        righe = []
        for meta in sorted(mete_o | mete_j | mete_g,
                           key=lambda m: -voli_rotta(rr[(codice, m)]) if (codice, m) in rr else 0):
            g = rr.get((codice, meta))
            o = rotte_o.get((codice, meta))
            j = rotte_j.get((codice, meta))
            if g:
                compagnie = ", ".join(f"{k} {v['voli']}" for k, v in
                                      sorted(g["compagnie"].items(), key=lambda kv: -kv[1]["voli"]))
                testo_g = f"{compagnie} · {giorni_lettere(giorni_rotta(g))}"
            else:
                testo_g = "-"
            testo_o = "-"
            if o:
                testo_o = f"{o.get('flights_per_week', '?')} ({', '.join(sorted(ottieni_compagnie(o)))})"
            righe.append((meta, nome_citta(meta, aeroporti, fonti["omaxim"]), testo_g, testo_o, "sì" if j else "-"))
        dettaglio += [f"### {codice} · {nome_citta(codice, aeroporti, fonti['omaxim'])}", "",
                      tabella(["Meta", "Città", "Giornate: compagnie voli/sett · giorni", "omaxim ott", "Jonty"], righe),
                      ""]
    out += ["**Riepilogo delle differenze:**", "",
            tabella(["Aeroporto", "Città", "Mete giornate", "Mete omaxim", "Mete Jonty",
                     "Solo in Jonty", "Solo in omaxim", "In omaxim ott ma non nelle giornate",
                     "Nelle giornate ma non in omaxim ott"], riepilogo), ""]
    return out, ["## Allegato: le mete dei 10 aeroporti campione", ""] + legenda + dettaglio


def sezione_low_cost(analisi, ricostruzione):
    out = ["## 3. Copertura low cost", "",
           "Rotte in cui compare la compagnia, entrambi gli aeroporti nell'area (ogni senso conta come una rotta).",
           ""]
    righe = []
    for nome, codici in LOW_COST.items():
        o = sum(1 for r in analisi["omaxim"]["rotte"].values() if ottieni_compagnie(r) & codici)
        j = sum(1 for r in analisi["jonty"]["rotte"].values() if ottieni_compagnie(r) & codici)
        rotte_g = [r for r in ricostruzione["rotte"].values() if set(r["compagnie"]) & codici]
        voli = sum(c["voli"] for r in rotte_g for k, c in r["compagnie"].items() if k in codici)
        righe.append((nome, f"{o:,}".replace(",", "."), f"{j:,}".replace(",", "."),
                      f"{len(rotte_g):,}".replace(",", "."), f"{voli:,}".replace(",", ".")))
    out += [tabella(["Compagnia", "omaxim ott", "Jonty set", "Giornate nov", "Voli/sett giornate"], righe), ""]
    return out


def sezione_wikipedia(wiki, n_aeroporti_area):
    out = ["## 4. Wikipedia", "", "Pagine inglesi, via API ufficiale, una richiesta al secondo.", ""]
    righe = []
    for codice in CAMPIONI:
        p = wiki["pagine"][codice]
        e = p["esito"]
        if not e:
            righe.append((codice, "pagina non trovata", "-", "-", "-", "-", "-", "-", "-", "-"))
            continue
        voci = e["voci"]
        begins = [v for v in voci if v["nota"] == "begins"]
        righe.append((codice, p["titolo"], "sì" if e["template"] else "NO", e["righe"], len(voci),
                      e["righe_seasonal"], sum(v["stagionale"] for v in voci),
                      f"{e['righe_begins']} / {sum(1 for v in begins if v['futura'])}",
                      f"{p['risolte_pct']:.0f}%",
                      f"{len(p['comuni'])} / {len(p['solo_wiki'])} / {len(p['solo_dati'])}"))
    out += [tabella(["Aeroporto", "Pagina", "Tabella letta", "Righe compagnia", "Mete elencate",
                     "Righe Seasonal", "Mete Seasonal", "Righe begins / mete future",
                     "Codice IATA trovato", "Mete: in comune / solo Wiki / solo file"], righe), "",
            "\"Mete\" conta una stessa destinazione una volta per compagnia. Il confronto dell'ultima colonna "
            "è solo nell'area: \"solo file\" unisce file di ottobre e giornate.", ""]

    righe = []
    for codice in CAMPIONI:
        p = wiki["pagine"][codice]
        if p["esito"]:
            righe.append((codice, p["sparite"], p["sparite_stagionali"], p["sparite_normali"], p["sparite_assenti"],
                          p["stagionali_area"], p["stagionali_volano_ora"]))
    out += ["### Le rotte \"sparite\" sono stagionali?", "",
            "Rotte presenti nel file di ottobre ma senza voli nelle giornate di novembre, confrontate con Wikipedia. "
            "Se la sola stagionalità spiegasse tutto, la prima colonna sarebbe uguale alla seconda.", "",
            tabella(["Aeroporto", "Sparite", "...su Wiki come Seasonal", "...su Wiki come normali", "...non su Wiki",
                     "Solo-Seasonal su Wiki (area)", "...che volano adesso"], righe), ""]

    for codice in ("TRN", "KUT"):
        p = wiki["pagine"][codice]
        if not p["esito"]:
            continue
        out += [f"### Esempio: {codice}", ""]
        per_compagnia = defaultdict(list)
        for v in p["esito"]["voci"]:
            testo = v["iata"] or f"?{v['nome']}"
            if v["charter"]:
                testo += " (charter)"
            if v["stagionale"]:
                testo += " (stagionale)"
            if v["nota"]:
                testo += f" ({v['nota']} {v.get('data', '')})".replace(" )", ")")
            per_compagnia[v["compagnia"]].append(testo)
        out.append(tabella(["Compagnia", "Mete estratte"],
                           [(k, ", ".join(v)) for k, v in sorted(per_compagnia.items())]))
        out += [""]

    n_pagine = sum(1 for p in wiki["pagine"].values() if p["esito"])
    voci_totali = sum(len(p["esito"]["voci"]) for p in wiki["pagine"].values() if p["esito"])
    richieste = n_aeroporti_area * 3 + max(voci_totali // max(n_pagine, 1), 1) * n_aeroporti_area // 50
    minuti = richieste * PAUSA_WIKI / 60
    out += ["### Stima della fatica per tutta l'area", "",
            f"- Aeroporti dell'area con rotte: {n_aeroporti_area}.",
            f"- Circa {richieste:,} richieste".replace(",", ".") + f", a una al secondo: circa **{minuti:.0f} minuti** "
            "alla prima scansione (per eccesso: i codici si ripetono e le risposte si riusano).",
            "- Le pagine piccole o mancanti sono il punto debole: questa stima non misura quante siano, "
            "perché il test ha guardato solo 10 aeroporti.",
            ""]
    return out


def main():
    aggiorna = "--aggiorna" in sys.argv
    sys.stdout.reconfigure(encoding="utf-8")
    DATI.mkdir(exist_ok=True)

    print("Scarico aeroporti (OurAirports)...")
    aeroporti = carica_aeroporti(aggiorna)
    area = Area(aeroporti)

    fonti, info, analisi, percorsi = {}, {}, {}, {}
    for chiave, repo in REPO.items():
        print(f"Scarico rotte {chiave}...")
        percorsi[chiave] = scarica(RAW.format(repo, "airline_routes.json"),
                                   DATI / f"{chiave}_airline_routes.json", aggiorna)
        fonti[chiave] = json.loads(percorsi[chiave].read_text(encoding="utf-8"))
        info[chiave] = info_repo(chiave, aggiorna)
    for chiave in REPO:
        for codice, voce in fonti[chiave].items():
            if codice not in aeroporti:
                area.supplenti[codice] = voce
    for chiave in REPO:
        analisi[chiave] = analizza_file(fonti[chiave], area)
        analisi[chiave]["aeroporti_con_rotte_set"] = {o for o, _ in analisi[chiave]["rotte"]}

    print("Scarico i file giornalieri di omaxim...")
    giornate = carica_giornalieri(aggiorna)
    ricostruzione = ricostruisci_settimana(giornate, area)
    conv = convenzione_giorni(analisi["omaxim"]["rotte"], ricostruzione["rotte"])

    print("Leggo Wikipedia (una richiesta al secondo, la prima volta richiede qualche minuto)...")
    wiki = test_wikipedia(area, ricostruzione["rotte"], analisi["omaxim"]["rotte"], aggiorna)

    dati = [f"*Numeri calcolati da `test_fonti.py` il {OGGI}.*", ""]
    riepilogo_campioni, allegato = sezione_campioni(analisi, ricostruzione, aeroporti, fonti)
    dati += sezione_file(info, analisi, percorsi, giornate, ricostruzione, conv, aeroporti, area, fonti)
    dati += riepilogo_campioni
    dati += sezione_low_cost(analisi, ricostruzione)
    dati += sezione_wikipedia(wiki, analisi["omaxim"]["aeroporti_con_rotte"])
    stima = stima_file_finale(analisi, ricostruzione, aeroporti, area, fonti)
    data_oa = json_con_cache("https://api.github.com/repos/davidmegginson/ourairports-data/commits?per_page=1",
                             DATI / "github" / "ourairports_ultimo_commit.json", aggiorna)
    dati += ["## Misure per il formato dati", "",
             f"- OurAirports, ultimo aggiornamento: {data_oa[0]['commit']['committer']['date'][:10]}.",
             f"- Prova del file finale con {punti(stima['rotte'])} rotte e {stima['compagnie']} compagnie: "
             f"{stima['mb']:.1f} MB, che compressi (come li spedisce GitHub Pages) sono {stima['gz_mb']:.2f} MB.",
             f"- Compagnie delle giornate senza un nome nel file di ottobre: {len(stima['senza_nome'])}"
             f" ({', '.join(stima['senza_nome'][:30]) or 'nessuna'}).", ""]
    dati += allegato
    testo_dati = "\n".join(dati)

    if NOTE.exists():
        note = NOTE.read_text(encoding="utf-8")
        testo = note.replace(SEGNAPOSTO, testo_dati) if SEGNAPOSTO in note else note + "\n\n" + testo_dati
    else:
        testo = "# Report fonti Dove_Volo\n\n" + testo_dati
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(testo + "\n", encoding="utf-8")
    print(f"Fatto: {REPORT}")


if __name__ == "__main__":
    main()
