"""Scarica i file pubblici. Una cartella di cache evita di riscaricare cio' che non e' cambiato."""
import csv
import gzip
import io
import json
import urllib.error
import urllib.request

UA = "Dove_Volo/{} (progetto personale, non commerciale; https://github.com/dedavi97/Dove_Volo)"
URL_AEROPORTI = "https://davidmegginson.github.io/ourairports-data/airports.csv"
URL_ELENCO_GIORNI = "https://api.github.com/repos/omaxim/airline-route-data/contents/days"
# Il file del 4 ottobre 2026 preso dal suo commit: se omaxim lo sovrascrive, lo storico non cambia.
COMMIT_STORICO = "a7a0ceb1e6d69c13e68c591072ec7a8bb10d4db4"
URL_STORICO = f"https://raw.githubusercontent.com/omaxim/airline-route-data/{COMMIT_STORICO}/airline_routes.json"

ERRORI_RETE = (urllib.error.URLError, TimeoutError, OSError)


class Scaricatore:
    def __init__(self, cache, versione):
        self.cache = cache
        self.ua = UA.format(versione)

    def _leggi(self, url, secondi=180):
        richiesta = urllib.request.Request(url, headers={"User-Agent": self.ua})
        with urllib.request.urlopen(richiesta, timeout=secondi) as risposta:
            return risposta.read()

    def _salva(self, nome, contenuto):
        percorso = self.cache / nome
        percorso.parent.mkdir(parents=True, exist_ok=True)
        percorso.write_bytes(contenuto)
        return percorso

    def aeroporti(self, avvisi):
        """Righe di OurAirports. Se la rete manca usa l'ultima copia; senza copia l'errore sale."""
        try:
            percorso = self._salva("airports.csv", self._leggi(URL_AEROPORTI))
        except ERRORI_RETE as errore:
            percorso = self.cache / "airports.csv"
            if not percorso.exists():
                raise
            avvisi.append(f"OurAirports non raggiungibile ({errore}): uso l'ultima copia scaricata.")
        return list(csv.DictReader(io.StringIO(percorso.read_text(encoding="utf-8"), newline="")))

    def giornate(self, avvisi):
        """File giornalieri di omaxim, o None se non si riescono a scaricare."""
        try:
            elenco = json.loads(self._leggi(URL_ELENCO_GIORNI, 60))
            nomi = {v["name"] for v in elenco}
            risultato = []
            for voce in elenco:
                percorso = self.cache / "days" / voce["name"]
                if not percorso.exists() or percorso.stat().st_size != voce["size"]:
                    percorso = self._salva(f"days/{voce['name']}", self._leggi(voce["download_url"]))
                try:
                    with gzip.open(percorso, "rt", encoding="utf-8") as f:
                        risultato.append(json.load(f))
                except (OSError, ValueError, EOFError) as errore:
                    avvisi.append(f"Giornata {voce['name']} illeggibile, saltata: {errore}")
            for vecchio in (self.cache / "days").glob("*.gz"):
                if vecchio.name not in nomi:
                    vecchio.unlink()
        except (*ERRORI_RETE, ValueError, KeyError, TypeError) as errore:
            avvisi.append(f"File giornalieri di omaxim non disponibili ({errore}).")
            return None
        if not risultato:
            avvisi.append("Nessun file giornaliero di omaxim trovato.")
            return None
        return risultato

    def storico(self, avvisi):
        """Il file omaxim del 4 ottobre, o None se non si riesce a scaricare."""
        percorso = self.cache / f"storico_{COMMIT_STORICO[:8]}.json"
        try:
            if not percorso.exists():
                self._salva(percorso.name, self._leggi(URL_STORICO, 300))
            return json.loads(percorso.read_text(encoding="utf-8"))
        except (*ERRORI_RETE, ValueError) as errore:
            avvisi.append(f"Storico iniziale non disponibile ({errore}).")
            return None
