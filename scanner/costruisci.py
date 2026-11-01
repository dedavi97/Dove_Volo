"""Unisce settimana ricostruita e storico nel contenuto del file dati."""
import math
import statistics
from datetime import date

from .area import codice_unico
from .dati_file import TIPO, VERSIONE_FORMATO
from .settimana import giorni_in_testo, ricostruisci

DATA_STORICO = "2026-10-04"
FONTE_OMAXIM = {"nome": "omaxim/airline-route-data", "url": "https://github.com/omaxim/airline-route-data",
                "licenza": "Nessuna licenza indicata"}
FONTE_OURAIRPORTS = {"nome": "OurAirports", "url": "https://ourairports.com/data/", "licenza": "Pubblico dominio"}
FONTE_WIKIPEDIA = {"nome": "Wikipedia", "url": "https://en.wikipedia.org/", "licenza": "CC BY-SA"}


def km_tra(a, b):
    """Distanza in linea d'aria tra due aeroporti."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return round(2 * 6371 * math.asin(math.sqrt(h)))


def entro_12_mesi(data_testo, oggi):
    """True se la data non e' piu' vecchia di 12 mesi rispetto a oggi."""
    giorno = date.fromisoformat(data_testo)
    try:
        limite = oggi.replace(year=oggi.year - 1)
    except ValueError:  # 29 febbraio
        limite = oggi.replace(year=oggi.year - 1, day=28)
    return giorno >= limite


def importa_storico(file_omaxim, area):
    """Trasforma il file omaxim del 4 ottobre in rotte storiche.

    Quel file ha voli e giorni per rotta, non per compagnia: restano solo le compagnie.
    Restituisce (rotte, nomi_compagnie, citta). Le citta' di omaxim servono alla ricerca:
    per Malpensa dice "Milan", mentre OurAirports dice "Ferno".
    """
    rotte, nomi, citta = {}, {}, {}
    for codice, aeroporto in file_omaxim.items():
        origine = codice_unico(codice)
        if origine not in area:
            continue
        if codice == origine and aeroporto.get("city_name"):
            citta[origine] = aeroporto["city_name"]
        for rotta in aeroporto.get("routes", []):
            meta = codice_unico(rotta.get("iata"))
            if meta not in area or meta == origine:
                continue
            voce = rotte.setdefault((origine, meta), {
                "da": origine, "a": meta, "stato": "stagionale", "stagionale_wiki": False,
                "durata_min": rotta.get("min") or None, "compagnie": [], "periodo": None,
                "vista_ultima": DATA_STORICO, "fonte": "omaxim",
            })
            for compagnia in rotta.get("carriers", []):
                sigla = compagnia.get("iata")
                if not sigla:
                    continue
                if compagnia.get("name"):
                    nomi[sigla] = compagnia["name"]
                if all(c["iata"] != sigla for c in voce["compagnie"]):
                    voce["compagnie"].append({"iata": sigla, "voli_sett": None, "giorni": None})
    return rotte, nomi, citta


def _stato_assente(rotta, oggi):
    """Regola stagionali: una rotta assente resta visibile se Wikipedia o gli ultimi 12 mesi la sostengono."""
    vista = rotta["vista_ultima"]
    if rotta.get("stagionale_wiki") or (vista and entro_12_mesi(vista, oggi)):
        return "stagionale"
    return "nascosta"


def _periodo_valido(periodo, oggi):
    """Un periodo gia' finito non serve piu'."""
    if periodo and periodo.get("al") and periodo["al"] < oggi.isoformat():
        return None
    return periodo


def _compagnie_da_wikipedia(nomi_wiki, nomi):
    """Wikipedia da' i nomi, non i codici: il codice c'e' solo se il nome e' gia' conosciuto."""
    per_nome = {n.lower(): s for s, n in nomi.items() if n}
    compagnie = []
    for nome in nomi_wiki:
        sigla = per_nome.get(nome.lower())
        voce = {"iata": sigla, "voli_sett": None, "giorni": None}
        if not sigla:
            voce["nome"] = nome
        compagnie.append(voce)
    return compagnie


def _senza_frequenze(compagnie):
    return [{**c, "voli_sett": None, "giorni": None} for c in compagnie]


def _wikipedia_basta(settimana, origine):
    """Una rotta "normale" solo su Wikipedia e' attiva se omaxim manca, o se all'aeroporto mancano dei giorni.

    Se omaxim ha la settimana completa la rotta non vola. Se non ha mai visto l'aeroporto non c'e' conferma:
    le pagine possono elencare rotte ferme da anni.
    """
    if not settimana:
        return True
    copertura = settimana["copertura"].get(origine)
    return bool(copertura) and not copertura["completa"]


def _stato_senza_voli(voce, vecchia, wiki, settimana, oggi):
    """Lo stato di una rotta che non vola nei dati di questa settimana."""
    if wiki:
        if wiki["annunciata"]:
            return "annunciata"
        if wiki["normale"] and _wikipedia_basta(settimana, voce["da"]):
            return "attiva"
    stato = _stato_assente(voce, oggi)
    if vecchia and not settimana and not wiki and stato == "stagionale" and vecchia["stato"] != "nascosta":
        # Senza omaxim e senza Wikipedia non sappiamo nulla: resta com'era finche' non invecchia troppo.
        return vecchia["stato"]
    if vecchia and vecchia["stato"] == "annunciata" and wiki is None and (vecchia.get("periodo") or {}).get("dal", "") > oggi.isoformat():
        return "annunciata"
    return stato


def costruisci(area, conosciuti, giornate, precedente, storico, oggi, rotte_wiki=None):
    """Produce il contenuto del file dati.

    giornate:   file giornalieri di omaxim, o None se omaxim non e' disponibile
    precedente: il file dati precedente, o None alla prima esecuzione
    storico:    risultato di importa_storico, usato solo se non c'e' un file precedente
    rotte_wiki: riassunti da Wikipedia per rotta, o None se Wikipedia non e' disponibile
    Restituisce (dati, avvisi).
    """
    avvisi = []
    if precedente:
        vecchie = {(r["da"], r["a"]): r for r in precedente["rotte"]
                   if r["da"] in area and r["a"] in area}
        nomi = dict(precedente.get("compagnie", {}))
        citta = {c: a["citta"] for c, a in precedente["aeroporti"].items()}
    elif storico:
        vecchie, nomi, citta = storico
    else:
        vecchie, nomi, citta = {}, {}, {}

    settimana = ricostruisci(giornate, area, conosciuti) if giornate else None
    if settimana and settimana["mete_ignote"]:
        avvisi.append("Codici sconosciuti a OurAirports, rotte scartate: "
                      + ", ".join(sorted(settimana["mete_ignote"])))
    data_vista = oggi.isoformat()
    if settimana:
        data_vista = min(data_vista, settimana["ultima"])

    rotte = []
    correnti = settimana["rotte"] if settimana else {}
    copertura = settimana["copertura"] if settimana else {}
    wiki_disponibile = rotte_wiki is not None
    da_wiki = rotte_wiki or {}
    chiavi = set(vecchie) | set(correnti)
    for chiave, wiki in da_wiki.items():
        # Una rotta nuova entra solo se dice qualcosa che omaxim non puo' sapere.
        if wiki["annunciata"] or wiki["stagionale"] or _wikipedia_basta(settimana, chiave[0]):
            chiavi.add(chiave)
    for chiave in sorted(chiavi):
        vecchia, attuale, wiki = vecchie.get(chiave), correnti.get(chiave), da_wiki.get(chiave)
        if wiki_disponibile:
            stagionale_wiki = bool(wiki and wiki["stagionale"])
            periodo = wiki["periodo"] if wiki else None
        else:
            stagionale_wiki = bool(vecchia and vecchia.get("stagionale_wiki"))
            periodo = vecchia.get("periodo") if vecchia else None
        voce = {
            "da": chiave[0], "a": chiave[1], "stato": None,
            "stagionale_wiki": stagionale_wiki,
            "km": km_tra(area[chiave[0]], area[chiave[1]]),
            "durata_min": vecchia.get("durata_min") if vecchia else None,
            "compagnie": [],
            "periodo": _periodo_valido(periodo, oggi),
            "vista_ultima": vecchia["vista_ultima"] if vecchia else None,
            "fonte": (vecchia or {}).get("fonte", "wikipedia"),
        }
        if attuale:
            voce["stato"] = "attiva"
            voce["vista_ultima"] = data_vista
            voce["fonte"] = "omaxim"
            if attuale["durate"]:
                voce["durata_min"] = int(statistics.median(attuale["durate"]))
            voce["compagnie"] = [
                {"iata": sigla, "voli_sett": c["voli"], "giorni": giorni_in_testo(c["giorni"])}
                for sigla, c in sorted(attuale["compagnie"].items())
            ]
        else:
            voce["compagnie"] = _senza_frequenze(vecchia["compagnie"]) if vecchia else []
            if not voce["compagnie"] and wiki:
                voce["compagnie"] = _compagnie_da_wikipedia(wiki["compagnie"], nomi)
            voce["stato"] = _stato_senza_voli(voce, vecchia, wiki, settimana, oggi)
        rotte.append(voce)

    aeroporti = {}
    for codice in sorted({r["da"] for r in rotte} | {r["a"] for r in rotte}):
        c = copertura.get(codice)
        aeroporti[codice] = {**area[codice],
                             "citta": citta.get(codice) or area[codice]["citta"],
                             "settimana_dal": c["dal"] if c else None,
                             "settimana_completa": c["completa"] if c else False}

    sigle = sorted({c["iata"] for r in rotte for c in r["compagnie"] if c["iata"]})
    fonti = [{**FONTE_OURAIRPORTS, "data": oggi.isoformat()}]
    if wiki_disponibile:
        fonti.insert(0, {**FONTE_WIKIPEDIA, "data": oggi.isoformat()})
    if settimana:
        fonti.insert(0, {**FONTE_OMAXIM, "data": settimana["ultima"]})

    return {
        "tipo": TIPO,
        "versione_formato": VERSIONE_FORMATO,
        "aggiornato": oggi.isoformat(),
        "fonti": fonti,
        "compagnie": {s: nomi.get(s) for s in sigle},
        "aeroporti": aeroporti,
        "rotte": rotte,
    }, avvisi
