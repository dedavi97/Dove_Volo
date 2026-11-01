"""Aggiorna i dati: scansione, riepilogo, domanda, pubblicazione del solo file dati.

    python -m scanner                  uso normale, chiede conferma prima di pubblicare
    python -m scanner --prova FILE     scrive il risultato in FILE, senza toccare git
    python -m scanner --senza-omaxim   produce un file senza frequenze
    python -m scanner --senza-wikipedia  salta Wikipedia
"""
import argparse
import sys
from datetime import date
from pathlib import Path

from . import RADICE, versione
from .area import leggi_aeroporti
from .costruisci import costruisci, importa_storico
from .dati_file import leggi, scrivi
from .differenze import riepilogo
from .fonti import ERRORI_RETE, Scaricatore
from .pubblica import motivo_blocco, pubblica
from .wikipedia import Wikipedia, carica_con_cache

FILE_DATI = RADICE / "dati" / "dove_volo.json"
CACHE = RADICE / "cache"
GIORNI_OMAXIM_FERMO = 14


def prepara(scaricatore, precedente, oggi, senza_omaxim=False, senza_wikipedia=False):
    """Scarica le fonti e costruisce il nuovo contenuto. Restituisce (dati, avvisi)."""
    avvisi = []
    area, conosciuti = leggi_aeroporti(scaricatore.aeroporti(avvisi))
    giornate = None if senza_omaxim else scaricatore.giornate(avvisi)
    if giornate:
        ultima = max(g["date"] for g in giornate)
        fermo = (oggi - date.fromisoformat(ultima)).days
        if fermo > GIORNI_OMAXIM_FERMO:
            avvisi.append(f"L'ultima giornata di omaxim e' del {ultima}: sembra ferma da {fermo} giorni. "
                          "Se resta cosi', valuta --senza-omaxim.")
    storico = None
    if precedente is None:
        file_storico = scaricatore.storico(avvisi)
        if file_storico:
            storico = importa_storico(file_storico, area)
    rotte_wiki = None
    if not senza_wikipedia:
        rotte_wiki = carica_con_cache(Wikipedia(scaricatore.leggi), area, oggi, scaricatore.cache, avvisi)
    dati, altri = costruisci(area, conosciuti, giornate, precedente, storico, oggi, rotte_wiki)
    return dati, avvisi + altri


def chiedi_conferma():
    try:
        return input("Pubblico? S/N: ").strip().upper() == "S"
    except EOFError:
        return False


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="scanner", description="Aggiorna i dati di Dove_Volo")
    parser.add_argument("--prova", type=Path, help="scrive qui il risultato, senza pubblicare")
    parser.add_argument("--senza-omaxim", action="store_true", help="produce un file senza frequenze")
    parser.add_argument("--senza-wikipedia", action="store_true", help="salta Wikipedia")
    args = parser.parse_args(argv)

    print(f"Dove_Volo {versione()}: aggiornamento dati")
    if not args.prova:
        problema = motivo_blocco(RADICE, FILE_DATI)
        if problema:
            print(f"Mi fermo prima di iniziare. {problema}")
            return 1

    precedente = leggi(FILE_DATI)
    print("Scarico i dati (la prima volta richiede qualche minuto)...")
    try:
        dati, avvisi = prepara(Scaricatore(CACHE, versione()), precedente, date.today(),
                               args.senza_omaxim, args.senza_wikipedia)
    except ERRORI_RETE as errore:
        print(f"Non riesco a scaricare gli aeroporti: {errore}")
        return 1

    print()
    print(riepilogo(precedente, dati, avvisi))
    print()
    if not dati["rotte"]:
        print("Nessuna rotta nel risultato: non scrivo nulla.")
        return 1

    if args.prova:
        scrivi(dati, args.prova)
        print(f"Prova scritta in {args.prova}")
        return 0
    if not chiedi_conferma():
        print("Non pubblico: il file dati resta com'era.")
        return 0
    scrivi(dati, FILE_DATI)
    riuscito, messaggio = pubblica(RADICE, FILE_DATI, dati["aggiornato"])
    print(messaggio)
    return 0 if riuscito else 1


if __name__ == "__main__":
    sys.exit(main())
