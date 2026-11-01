# Backlog · Dove_Volo

Ogni punto ha un numero fisso. Peso: P piccolo, M medio, G grande.

## Aperti

| N. | Data | Area | Tipo | Stato | Peso | Descrizione |
|---|---|---|---|---|---|---|
| 1 | 2026-11-01 | Dati | Verifica | Aperto, tocca a Davide | P | Controllare le rotte di Torino nell'allegato del report sul PC di casa. Non blocca la 0.1.0. |
| 3 | 2026-11-01 | Scanner | Funzione | Aperto | G | **0.1.0** Scanner: giornate di omaxim + OurAirports, settimana ricostruita, filtro area, storico dal 4 ottobre, JSON nel formato aggiornato, `Aggiorna_Dati.bat`. Test: file senza frequenze, settimana incompleta, rotta sparita da più di 12 mesi. |
| 4 | 2026-11-01 | Scanner | Funzione | Aperto | P | Unire `MLH` a `BSL`: sono lo stesso aeroporto. Da fare con la 0.1.0. |
| 11 | 2026-11-01 | Scanner | Funzione | Aperto | P | Togliere le rotte in elicottero: `type` = `heliport` in OurAirports più `AEI` e `VIF`. Da fare con la 0.1.0, con test. |
| 5 | 2026-11-01 | Sito | Funzione | Aperto | G | **0.2.0** Sito base: mappa scura Leaflet, scelta partenza, archi, lista, filtri, legenda, versione visibile. |
| 6 | 2026-11-01 | Sito | Funzione | Aperto | M | **0.3.0** Multi-tratta: catena di tappe, aggiungi e togli tappe. |
| 7 | 2026-11-01 | Sito | Funzione | Aperto | M | **0.4.0** Chiudi il giro: raggio, ritorni, riepilogo. |
| 8 | 2026-11-01 | Scanner e sito | Funzione | Aperto | G | **0.5.0** Stagionali: Wikipedia + storico nello scanner, stato `annunciata`, linee tratteggiate, prova del file con OurAirports + Wikipedia. |
| 9 | 2026-11-01 | Sito | Funzione | Aperto | M | **0.6.0** Impostazioni, Aiuto, Informazioni con fonti e changelog, rifiniture mobile. |
| 10 | 2026-11-01 | Dati | Miglioria | Aperto | P | Completare a mano i nomi delle 10 compagnie senza nome: ATV, B0, DCT, FNA, GPX, HBR, HTY, LID, LTR, TOM. |

## Chiusi

| N. | Data | Area | Tipo | Stato | Peso | Descrizione |
|---|---|---|---|---|---|---|
| 2 | 2026-11-01 | Dati | Decisione | Chiuso | P | Elicotteri: Davide ha deciso di toglierli tutti, Ceuta (JCU) compresa. Il lavoro è al punto 11. |
