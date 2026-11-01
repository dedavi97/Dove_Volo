# Changelog · Dove_Volo

Cosa cambia a ogni versione, in parole semplici.

## 0.1.0 · 1° novembre 2026

Prima versione: il programma che raccoglie i dati. Il sito non c'è ancora.

- Scarica aeroporti e voli e ricostruisce una settimana di voli per ogni aeroporto: compagnie, voli a settimana e giorni.
- Tiene solo l'Europa larga, senza elicotteri. Basilea-Mulhouse conta come un solo aeroporto.
- Parte già con le rotte dell'estate 2026, segnate come stagionali.
- Una rotta sparita da più di 12 mesi viene nascosta, ma resta nel file.
- Funziona anche se la fonte dei voli si ferma: il file esce senza frequenze.
- `Aggiorna_Dati.bat` mostra le differenze e chiede conferma prima di pubblicare, e pubblica solo il file dei dati.
