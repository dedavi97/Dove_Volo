# Changelog · Dove_Volo

Cosa cambia a ogni versione, in parole semplici.

## 0.2.1 · 1° novembre 2026

- Una "✕" nel campo Partenza toglie l'aeroporto scelto e riporta la mappa all'inizio. Prima non c'era modo di tornare indietro.

## 0.2.0 · 1° novembre 2026

Prima versione del sito: si vede la mappa.

- Scegli la partenza scrivendo una città o un codice, anche in italiano (Torino, Londra), o toccando un punto sulla mappa.
- La mappa mostra le mete dirette: linee blu per le rotte attive, arancioni tratteggiate per le stagionali.
- La lista mostra per ogni meta compagnie, voli a settimana, giorni, distanza e durata.
- Filtri per rotte attive, stagionali e paese.
- Da telefono il pannello si trascina; da computer diventa una colonna a sinistra.
- Lo sfondo della mappa è salvato nel sito e non dipende da servizi esterni.
- `Apri_Sito.bat` apre il sito sul PC.

## 0.1.0 · 1° novembre 2026

Prima versione: il programma che raccoglie i dati. Il sito non c'è ancora.

- Scarica aeroporti e voli e ricostruisce una settimana di voli per ogni aeroporto: compagnie, voli a settimana e giorni.
- Tiene solo l'Europa larga, senza elicotteri. Basilea-Mulhouse conta come un solo aeroporto.
- Parte già con le rotte dell'estate 2026, segnate come stagionali.
- Una rotta sparita da più di 12 mesi viene nascosta, ma resta nel file.
- Funziona anche se la fonte dei voli si ferma: il file esce senza frequenze.
- `Aggiorna_Dati.bat` mostra le differenze e chiede conferma prima di pubblicare, e pubblica solo il file dei dati.
