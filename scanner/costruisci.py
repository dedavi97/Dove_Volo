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
    if rotta.get("stagionale_wiki") or entro_12_mesi(rotta["vista_ultima"], oggi):
        return "stagionale"
    return "nascosta"


def _senza_frequenze(compagnie):
    return [{"iata": c["iata"], "voli_sett": None, "giorni": None} for c in compagnie]


def costruisci(area, conosciuti, giornate, precedente, storico, oggi):
    """Produce il contenuto del file dati.

    giornate:   file giornalieri di omaxim, o None se omaxim non e' disponibile
    precedente: il file dati precedente, o None alla prima esecuzione
    storico:    risultato di importa_storico, usato solo se non c'e' un file precedente
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
    for chiave in sorted(set(vecchie) | set(correnti)):
        vecchia, attuale = vecchie.get(chiave), correnti.get(chiave)
        voce = {
            "da": chiave[0], "a": chiave[1], "stato": None,
            "stagionale_wiki": bool(vecchia and vecchia.get("stagionale_wiki")),
            "km": km_tra(area[chiave[0]], area[chiave[1]]),
            "durata_min": vecchia.get("durata_min") if vecchia else None,
            "compagnie": [],
            "periodo": vecchia.get("periodo") if vecchia else None,
            "vista_ultima": vecchia["vista_ultima"] if vecchia else data_vista,
            "fonte": "omaxim",
        }
        if attuale:
            voce["stato"] = "attiva"
            voce["vista_ultima"] = data_vista
            if attuale["durate"]:
                voce["durata_min"] = int(statistics.median(attuale["durate"]))
            voce["compagnie"] = [
                {"iata": sigla, "voli_sett": c["voli"], "giorni": giorni_in_testo(c["giorni"])}
                for sigla, c in sorted(attuale["compagnie"].items())
            ]
        else:
            voce["compagnie"] = _senza_frequenze(vecchia["compagnie"])
            voce["stato"] = _stato_assente(voce, oggi)
            if not settimana and voce["stato"] == "stagionale" and vecchia["stato"] != "nascosta":
                # Senza omaxim non sappiamo se la rotta vola: resta com'era finche' non invecchia troppo.
                voce["stato"] = vecchia["stato"]
        rotte.append(voce)

    copertura = settimana["copertura"] if settimana else {}
    aeroporti = {}
    for codice in sorted({r["da"] for r in rotte} | {r["a"] for r in rotte}):
        c = copertura.get(codice)
        aeroporti[codice] = {**area[codice],
                             "citta": citta.get(codice) or area[codice]["citta"],
                             "settimana_dal": c["dal"] if c else None,
                             "settimana_completa": c["completa"] if c else False}

    sigle = sorted({c["iata"] for r in rotte for c in r["compagnie"]})
    fonti = [{**FONTE_OURAIRPORTS, "data": oggi.isoformat()}]
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
