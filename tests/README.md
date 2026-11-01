# Test · Dove_Volo

Per eseguirli tutti avvia `Esegui_Test.bat`. Nessun test usa la rete.

## Scanner: `test_scanner.py`

Serve solo Python: `python -m unittest discover -s tests -t .`

| Gruppo | Cosa controlla |
|---|---|
| Area | Paesi inclusi ed esclusi, Russia solo europea, eliporti e aeroporti chiusi fuori |
| Settimana | Conteggi, giorni da lunedì, giornata più recente, cambio d'orario, settimana incompleta, durate, unione `MLH`-`BSL` |
| Storico | Import del file del 4 ottobre, città, rotte estive stagionali |
| Regola stagionali | Limite dei 12 mesi, rotta sparita da più tempo nascosta ma nel file, ritorno di una rotta |
| Senza frequenze | File senza omaxim: voli e giorni vuoti, mai zero, e file comunque valido |
| Formato | Contenuto, scrittura e rilettura, file non valido rifiutato |
| Differenze | Rotte nuove, sparite, tornate e cambiate, avviso per un calo forte |
| Pubblica | Con un vero git e un finto GitHub: esce solo il file dati, e si blocca se pubblicherebbe altro |

## Sito: `sito.test.mjs`

Serve Node: `node --test "tests/*.test.mjs"`. Prova `sito/logica.js`, senza browser:

- ricerca in italiano e in inglese, per codice e per nome dell'aeroporto;
- mete, somma dei voli e unione dei giorni;
- rotte nascoste invisibili, frequenze vuote e mai zero;
- filtri, testi, linee curve e file dati sbagliato;
- togliere una tappa: ultima, in mezzo con e senza volo diretto, partenza, A > B > A;
- il vero `dati/dove_volo.json`: lettura e ricerche con le parole di una persona (Bergamo, Malpensa, Londra).

## Cosa i test automatici non coprono

Mappa, tocchi e pannello si controllano in un browser vero. Per ogni versione del sito fin qui è stato fatto con Chrome a schermo telefono e computer, con uno script non incluso nel repo: tocchi simulati, controllo che ogni tappa resti in vista, e soprattutto le schermate da guardare. Non è stato provato su un telefono vero. Vale la pena ripeterlo a ogni versione.

Il test delle fonti in `tools/test_fonti/` è uno strumento della Tappa 1, non un test automatico.
