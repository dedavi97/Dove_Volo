"""Legge da Wikipedia quali rotte sono stagionali e quali annunciate. Solo API ufficiali e richieste lente."""
import json
import re
import time
import urllib.parse
from datetime import date, datetime

from .area import codice_unico

URL_WIKIDATA = "https://query.wikidata.org/sparql"
URL_WIKIPEDIA = "https://en.wikipedia.org/w/api.php"
# Tutti i codici IATA con la loro pagina inglese, in una richiesta sola.
QUERY_CODICI = """SELECT ?iata ?titolo WHERE {
  ?aeroporto wdt:P238 ?iata .
  ?pagina schema:about ?aeroporto ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?titolo .
}"""
PAUSA = 1.0  # secondi tra una richiesta e l'altra
TITOLI_PER_RICHIESTA = 50
PAGINE_PER_RICHIESTA = 20  # le pagine degli aeroporti sono lunghe

RE_COMMENTO = re.compile(r"<!--.*?-->", re.S)
RE_REF = re.compile(r"<ref\b[^>/]*/>|<ref\b[^>]*>.*?</ref>", re.S | re.I)
RE_LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]")
RE_NOTA = re.compile(r"\b(begins|resumes|ends)\b\s*([^)}\n,<]*)", re.I)
RE_ETICHETTA = re.compile(r"'''\s*([^']+?)\s*:?\s*'''\s*:?")
# Alcune pagine dicono "voli sospesi" e poi elencano le rotte di allora: quelle rotte non valgono.
RE_VOLI_SOSPESI = re.compile(r"suspended|no longer|no (?:scheduled|commercial|passenger)|ceased|closed", re.I)


def _blocchi_template(testo):
    """Il contenuto di ogni tabella delle destinazioni, rispettando le graffe annidate."""
    blocchi = []
    for trovato in re.finditer(r"\{\{\s*Airport[- ]dest(?:ination)?[- ]list", testo, re.I):
        inizio = i = trovato.end()
        profondita = 1
        while i < len(testo) and profondita:
            if testo.startswith("{{", i):
                profondita += 1
                i += 2
            elif testo.startswith("}}", i):
                profondita -= 1
                i += 2
            else:
                i += 1
        blocchi.append(testo[inizio:i - 2])
    return blocchi


def _separa_pipe(testo):
    """Divide sui | fuori da link e template."""
    parti, attuale, graffe, quadre, i = [], [], 0, 0, 0
    while i < len(testo):
        coppia = testo[i:i + 2]
        if coppia in ("{{", "}}", "[[", "]]"):
            graffe += {"{{": 1, "}}": -1}.get(coppia, 0)
            quadre += {"[[": 1, "]]": -1}.get(coppia, 0)
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


def leggi_data(testo):
    """La data di una nota, in formato ISO. "March 2027" diventa il primo del mese. None se non si capisce."""
    pulito = re.sub(r"[{}|\[\]]", " ", testo)
    for formato, schema in (("%d %B %Y", r"\d{1,2} [A-Z][a-z]+ \d{4}"),
                            ("%B %d %Y", r"[A-Z][a-z]+ \d{1,2},? \d{4}"),
                            ("%B %Y", r"[A-Z][a-z]+ \d{4}")):
        trovata = re.search(schema, pulito)
        if trovata:
            try:
                return datetime.strptime(trovata.group(0).replace(",", ""), formato).date().isoformat()
            except ValueError:
                continue
    return None


def _sezione_passeggeri(testo):
    """La sezione delle destinazioni, senza il cargo."""
    inizio = re.search(r"^==+\s*Airlines and destinations\s*==+\s*$", testo, re.M | re.I)
    if not inizio:
        return None
    resto = testo[inizio.end():]
    fine = re.search(r"^==[^=].*==\s*$", resto, re.M)
    sezione = resto[:fine.start()] if fine else resto
    cargo = re.search(r"^===+\s*Cargo.*$", sezione, re.M | re.I)
    return sezione[:cargo.start()] if cargo else sezione


def leggi_pagina(wikitesto):
    """Dal testo di una pagina ricava le mete: pagina di destinazione, compagnia, seasonal, charter, nota, data.

    Restituisce None se la pagina non ha una tabella leggibile, una lista vuota se i voli sono sospesi.
    """
    testo = RE_REF.sub("", RE_COMMENTO.sub("", wikitesto))
    sezione = _sezione_passeggeri(testo)
    blocchi = _blocchi_template(sezione) if sezione else []
    if not blocchi:
        return None
    if RE_VOLI_SOSPESI.search(sezione[:sezione.lower().find("{{airport")]):
        return []
    voci = []
    for blocco in blocchi:
        parti = [p for p in _separa_pipe(blocco) if p and not re.match(r"^\w+\s*=\s*\S*$", p)]
        for compagnia, destinazioni in zip(parti[0::2], parti[1::2]):
            link_compagnia = RE_LINK.search(compagnia)
            nome = (link_compagnia.group(2) or link_compagnia.group(1)) if link_compagnia else compagnia
            for segmento in re.split(r"<br\s*/?>", destinazioni, flags=re.I):
                etichetta = RE_ETICHETTA.search(segmento)
                tipo = etichetta.group(1).lower() if etichetta else ""
                if "suspended" in tipo:
                    continue
                collegamenti = [l for l in RE_LINK.finditer(segmento)
                                if not l.group(1).lower().startswith(("file:", "image:"))]
                for pos, link in enumerate(collegamenti):
                    fine = collegamenti[pos + 1].start() if pos + 1 < len(collegamenti) else len(segmento)
                    nota = RE_NOTA.search(segmento[link.end():fine])
                    voci.append({
                        "pagina": link.group(1).strip(),
                        "compagnia": nome.strip(),
                        "stagionale": "seasonal" in tipo,
                        "charter": "charter" in tipo,
                        "nota": nota.group(1).lower() if nota else None,
                        "data": leggi_data(nota.group(2)) if nota else None,
                    })
    return voci


def riassumi_rotta(voci, oggi):
    """Da tutte le voci di una rotta decide cosa dice Wikipedia. I charter non contano.

    Restituisce None se la rotta non e' piu' valida, per esempio se e' finita.
    """
    oggi_testo = oggi.isoformat()
    normali, stagionali, annunciate, inizi, fini = [], [], [], [], []
    for voce in voci:
        if voce["charter"]:
            continue
        nota, data = voce["nota"], voce["data"]
        if nota == "ends" and data and data < oggi_testo:
            continue  # finita
        futura = nota in ("begins", "resumes") and (data is None or data > oggi_testo)
        if futura and data:
            inizi.append(data)
        if nota == "ends" and data:
            fini.append(data)
        if voce["stagionale"]:
            stagionali.append(voce)
        elif futura:
            annunciate.append(voce)
        else:
            normali.append(voce)
    tutte = normali + stagionali + annunciate
    if not tutte:
        return None
    # La stagione vale per la rotta solo se nessuna compagnia ci vola tutto l'anno.
    annunciata = not normali and not stagionali
    periodo = None
    if not normali and (inizi or fini):
        periodo = {"dal": min(inizi) if inizi else None, "al": max(fini) if fini else None}
    return {
        "normale": bool(normali),
        "stagionale": bool(stagionali) and not normali,
        "annunciata": annunciata,
        "periodo": periodo,
        "compagnie": sorted({v["compagnia"] for v in tutte}),
    }


def rotte_da_pagine(pagine, titolo_a_iata, area, oggi):
    """Da {aeroporto: voci} a {(da, a): riassunto}, solo tra aeroporti dell'area."""
    per_rotta = {}
    for origine, voci in pagine.items():
        for voce in voci:
            codice = titolo_a_iata.get(_titolo_pulito(voce["pagina"]))
            meta = codice_unico(codice) if codice else None
            if meta in area and meta != origine:
                per_rotta.setdefault((origine, meta), []).append(voce)
    rotte = {}
    for chiave, voci in per_rotta.items():
        riassunto = riassumi_rotta(voci, oggi)
        if riassunto:
            rotte[chiave] = riassunto
    return rotte


def _titolo_pulito(titolo):
    titolo = titolo.replace("_", " ").strip()
    return titolo[:1].upper() + titolo[1:]


class Wikipedia:
    """Le richieste vere. `leggi` e' la funzione che scarica un indirizzo e restituisce i byte."""

    def __init__(self, leggi, pausa=PAUSA):
        self.leggi = leggi
        self.pausa = pausa

    def _json(self, url):
        for tentativo in range(5):
            dati = json.loads(self.leggi(url))
            time.sleep(self.pausa)
            if not (isinstance(dati, dict) and dati.get("error", {}).get("code") == "maxlag"):
                break
            time.sleep(10 * (tentativo + 1))
        if isinstance(dati, dict) and "error" in dati:
            raise ValueError(f"Wikipedia ha risposto {dati['error'].get('code')}")
        return dati

    def _api(self, **parametri):
        return self._json(f"{URL_WIKIPEDIA}?" + urllib.parse.urlencode(
            {"action": "query", "format": "json", "formatversion": 2, "maxlag": 5, **parametri}))

    def codici(self):
        """{titolo: codice} e {codice: titolo}. Con piu' pagine per un codice vince quella di un aeroporto."""
        url = f"{URL_WIKIDATA}?" + urllib.parse.urlencode({"format": "json", "query": QUERY_CODICI})
        righe = self._json(url)["results"]["bindings"]
        titolo_a_iata, iata_a_titolo = {}, {}
        for riga in righe:
            codice, titolo = riga["iata"]["value"], riga["titolo"]["value"]
            titolo_a_iata.setdefault(titolo, codice)
            if codice not in iata_a_titolo or ("airport" in titolo.lower() and "airport" not in iata_a_titolo[codice].lower()):
                iata_a_titolo[codice] = titolo
        return titolo_a_iata, iata_a_titolo

    def testi(self, titoli):
        """{titolo: wikitesto}, a blocchi."""
        titoli = sorted(set(titoli))
        risultato = {}
        for i in range(0, len(titoli), PAGINE_PER_RICHIESTA):
            gruppo = titoli[i:i + PAGINE_PER_RICHIESTA]
            continua = {}
            while True:
                risposta = self._api(redirects=1, prop="revisions", rvprop="content", rvslots="main",
                                     titles="|".join(gruppo), **continua)
                rinominati = {v["to"]: v["from"] for v in risposta["query"].get("redirects", [])}
                for pagina in risposta["query"]["pages"]:
                    if pagina.get("revisions"):
                        titolo = rinominati.get(pagina["title"], pagina["title"])
                        risultato[titolo] = pagina["revisions"][0]["slots"]["main"]["content"]
                if "continue" not in risposta:
                    break
                continua = {k: v for k, v in risposta["continue"].items()}
        return risultato

    def segui_rinvii(self, titoli, titolo_a_iata):
        """Aggiunge i titoli che sono rinvii a una pagina con un codice: [[Malpensa Airport]] e simili."""
        ignoti = sorted({t for t in titoli if t not in titolo_a_iata})
        for i in range(0, len(ignoti), TITOLI_PER_RICHIESTA):
            gruppo = ignoti[i:i + TITOLI_PER_RICHIESTA]
            risposta = self._api(redirects=1, titles="|".join(gruppo))["query"]
            for voce in risposta.get("redirects", []):
                codice = titolo_a_iata.get(voce["to"])
                if codice:
                    titolo_a_iata[voce["from"]] = codice

    def rotte(self, area, oggi):
        """Restituisce (rotte, statistiche) per gli aeroporti dell'area."""
        titolo_a_iata, iata_a_titolo = self.codici()
        titoli = {iata_a_titolo[c]: c for c in area if c in iata_a_titolo}
        testi = self.testi(titoli)
        pagine, senza_tabella = {}, []
        for titolo, codice in titoli.items():
            voci = leggi_pagina(testi[titolo]) if titolo in testi else None
            if voci is None:
                senza_tabella.append(codice)
            else:
                pagine[codice] = voci
        tutti = {_titolo_pulito(v["pagina"]) for voci in pagine.values() for v in voci}
        self.segui_rinvii(tutti, titolo_a_iata)
        rotte = rotte_da_pagine(pagine, titolo_a_iata, area, oggi)
        voci_totali = sum(len(v) for v in pagine.values())
        senza_codice = sum(1 for voci in pagine.values() for v in voci
                           if _titolo_pulito(v["pagina"]) not in titolo_a_iata)
        return rotte, {"pagine": len(pagine), "senza_tabella": len(senza_tabella),
                       "voci": voci_totali, "senza_codice": senza_codice, "rotte": len(rotte),
                       "sospese": sorted(c for c, v in pagine.items() if not v)}


def carica_con_cache(wikipedia, area, oggi, cartella, avvisi):
    """Le rotte di Wikipedia, salvate per la giornata: rilanciare lo scanner non ripete le richieste.

    Restituisce None se Wikipedia non e' raggiungibile: lo scanner prosegue senza.
    """
    percorso = cartella / f"wikipedia_{oggi.isoformat()}.json"
    if percorso.exists():
        salvate = json.loads(percorso.read_text(encoding="utf-8"))
        rotte = {tuple(k.split(">")): v for k, v in salvate["rotte"].items()}
        statistiche = salvate["statistiche"]
    else:
        try:
            rotte, statistiche = wikipedia.rotte(area, oggi)
        except (OSError, ValueError, KeyError, TypeError) as errore:
            avvisi.append(f"Wikipedia non disponibile ({errore}): stagionali solo dallo storico.")
            return None
        for vecchio in cartella.glob("wikipedia_*.json"):
            vecchio.unlink()
        cartella.mkdir(parents=True, exist_ok=True)
        percorso.write_text(json.dumps({"statistiche": statistiche, "rotte": {f"{a}>{b}": v for (a, b), v in rotte.items()}},
                                       ensure_ascii=False), encoding="utf-8")
    sospese = statistiche.get("sospese", [])
    avvisi.append(f"Wikipedia: {statistiche['pagine']} pagine lette, {statistiche['senza_tabella']} senza tabella, "
                  f"{len(sospese)} con voli sospesi ({', '.join(sospese) or 'nessuna'}), "
                  f"{statistiche['rotte']} rotte nell'area, {statistiche['senza_codice']} voci su "
                  f"{statistiche['voci']} senza codice aeroporto.")
    return rotte
