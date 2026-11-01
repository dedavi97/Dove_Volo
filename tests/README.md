# Test · Dove_Volo

Per eseguirli avvia `Esegui_Test.bat`, oppure `python -m unittest discover -s tests -t .`. Serve solo Python, e nessun test usa la rete.

`test_scanner.py` controlla lo scanner:

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

Il test delle fonti in `tools/test_fonti/` è uno strumento della Tappa 1, non un test automatico.
