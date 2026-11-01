"""L'unico punto del codice Python che legge e scrive il file dati."""
import json
import os

TIPO = "dove_volo_dati"
VERSIONE_FORMATO = 1
STATI = {"attiva", "stagionale", "annunciata", "nascosta"}


def valida(dati):
    """Solleva ValueError se il contenuto non rispetta il formato."""
    if dati.get("tipo") != TIPO:
        raise ValueError(f"Non e' un file di Dove_Volo: tipo {dati.get('tipo')!r}")
    if dati.get("versione_formato") != VERSIONE_FORMATO:
        raise ValueError(f"Versione del formato non gestita: {dati.get('versione_formato')!r}")
    for sezione in ("aggiornato", "fonti", "compagnie", "aeroporti", "rotte"):
        if sezione not in dati:
            raise ValueError(f"Manca la sezione {sezione}")
    for rotta in dati["rotte"]:
        nome = f"{rotta.get('da')}>{rotta.get('a')}"
        if rotta.get("da") not in dati["aeroporti"] or rotta.get("a") not in dati["aeroporti"]:
            raise ValueError(f"Rotta {nome}: aeroporto non presente nel file")
        if rotta.get("stato") not in STATI:
            raise ValueError(f"Rotta {nome}: stato {rotta.get('stato')!r}")
        for compagnia in rotta.get("compagnie", []):
            voli, giorni = compagnia.get("voli_sett"), compagnia.get("giorni")
            if voli is not None and voli < 1:
                raise ValueError(f"Rotta {nome}: voli a settimana devono essere vuoti, mai zero")
            if giorni is not None and (len(giorni) != 7 or set(giorni) - {"0", "1"} or "1" not in giorni):
                raise ValueError(f"Rotta {nome}: giorni {giorni!r}")


def leggi(percorso):
    """Legge il file dati. Restituisce None se non esiste."""
    if not percorso.exists():
        return None
    dati = json.loads(percorso.read_text(encoding="utf-8"))
    valida(dati)
    return dati


def _riga(valore):
    return json.dumps(valore, ensure_ascii=False, separators=(",", ":"))


def in_testo(dati):
    """Una riga per aeroporto e per rotta: gli aggiornamenti restano piccoli nella cronologia git."""
    aeroporti = ",\n".join(f"{_riga(c)}:{_riga(v)}" for c, v in dati["aeroporti"].items())
    rotte = ",\n".join(_riga(r) for r in dati["rotte"])
    testa = {k: dati[k] for k in ("tipo", "versione_formato", "aggiornato", "fonti", "compagnie")}
    return f'{_riga(testa)[:-1]},\n"aeroporti":{{\n{aeroporti}\n}},\n"rotte":[\n{rotte}\n]}}\n'


def scrivi(dati, percorso):
    """Controlla il contenuto e sostituisce il file in un colpo solo."""
    valida(dati)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    temporaneo = percorso.with_name(percorso.name + ".tmp")
    temporaneo.write_text(in_testo(dati), encoding="utf-8", newline="\n")
    os.replace(temporaneo, percorso)
