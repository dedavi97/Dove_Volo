"""Ricostruisce una settimana di voli sommando i file giornalieri di omaxim."""
from datetime import date, timedelta

from .area import codice_unico

MAX_GIORNI_FINESTRA = 21


def ultimo_cambio_orario(giorno):
    """L'orario cambia l'ultima domenica di marzo e di ottobre: restituisce il cambio piu' recente."""
    def ultima_domenica(anno, mese):
        d = date(anno, mese, 31)
        return d - timedelta(days=d.isoweekday() % 7)

    cambi = [ultima_domenica(a, m) for a in (giorno.year - 1, giorno.year) for m in (3, 10)]
    return max(c for c in cambi if c <= giorno)


def finestra(giornate):
    """Sceglie le giornate da usare: stesso orario stagionale, massimo 3 settimane.

    Subito dopo un cambio d'orario le giornate nuove sono meno di 7: allora si prendono le ultime 7.
    """
    if not giornate:
        return []
    ordinate = sorted(giornate, key=lambda g: g["date"])
    ultima = date.fromisoformat(ordinate[-1]["date"])
    inizio = max(ultimo_cambio_orario(ultima), ultima - timedelta(days=MAX_GIORNI_FINESTRA - 1))
    scelte = [g for g in ordinate if date.fromisoformat(g["date"]) >= inizio]
    return scelte if len(scelte) >= 7 else ordinate[-7:]


def durata_minuti(volo):
    """Durata di un volo dagli orari e dai fusi. None se non si capisce."""
    try:
        ore_p, min_p = map(int, volo[3].split(":"))
        ore_a, min_a = map(int, volo[4].split(":"))
        minuti = ((ore_a * 60 + min_a - int(volo[6])) - (ore_p * 60 + min_p - int(volo[5]))) % 1440
    except (ValueError, IndexError, AttributeError):
        return None
    return minuti or None


def ricostruisci(giornate, area, conosciuti):
    """Per ogni aeroporto e giorno della settimana usa la giornata piu' recente che lo contiene.

    Restituisce {"rotte", "copertura", "mete_ignote", "ultima"}. Una rotta e'
    {"compagnie": {iata: {"voli", "giorni"}}, "durate": [...]}, con i giorni da 1 (lunedi') a 7.
    """
    usate = finestra(giornate)
    scelta = {}  # (codice grezzo, giorno) -> giornata: in ordine di data, la piu' recente sovrascrive
    for giornata in usate:
        giorno = date.fromisoformat(giornata["date"]).isoweekday()
        for codice in giornata.get("flights", {}):
            if codice_unico(codice) in area:
                scelta[(codice, giorno)] = giornata

    rotte, copertura, mete_ignote, visti = {}, {}, set(), set()
    for (codice, giorno), giornata in scelta.items():
        origine = codice_unico(codice)
        voce = copertura.setdefault(origine, {"dal": giornata["date"], "giorni": set()})
        voce["giorni"].add(giorno)
        voce["dal"] = min(voce["dal"], giornata["date"])
        for volo in giornata["flights"][codice]:
            if len(volo) < 4:
                continue
            meta, compagnia = codice_unico(volo[0]), volo[1]
            chiave_volo = (origine, giorno, meta, compagnia, volo[2], volo[3])
            if chiave_volo in visti:
                continue
            visti.add(chiave_volo)
            if meta not in area or meta == origine:
                if meta not in conosciuti:
                    mete_ignote.add(meta)
                continue
            rotta = rotte.setdefault((origine, meta), {"compagnie": {}, "durate": []})
            dati_compagnia = rotta["compagnie"].setdefault(compagnia, {"voli": 0, "giorni": set()})
            dati_compagnia["voli"] += 1
            dati_compagnia["giorni"].add(giorno)
            minuti = durata_minuti(volo)
            if minuti:
                rotta["durate"].append(minuti)

    return {
        "rotte": rotte,
        "copertura": {c: {"dal": v["dal"], "completa": len(v["giorni"]) == 7} for c, v in copertura.items()},
        "mete_ignote": mete_ignote,
        "ultima": usate[-1]["date"] if usate else None,
    }


def giorni_in_testo(giorni):
    """{1, 3} -> "1010000": sette caratteri da lunedi' a domenica."""
    return "".join("1" if i in giorni else "0" for i in range(1, 8))
