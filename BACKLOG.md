# Backlog · Dove_Volo

Ogni punto ha un numero fisso. Peso: P piccolo, M medio, G grande.

## Aperti

| N. | Data | Area | Tipo | Stato | Peso | Descrizione |
|---|---|---|---|---|---|---|
| 17 | 2026-11-01 | Sito | Funzione | Aperto | M | Chiudere il giro con una tappa intermedia: quando scegli il rientro, mostrare anche gli aeroporti raggiungibili dall'ultima tappa che hanno un volo diretto verso la base (la partenza o un aeroporto nel raggio). Richiesta di Davide. |
| 1 | 2026-11-01 | Dati | Verifica | Aperto, tocca a Davide | P | Controllare le rotte di Torino nell'allegato del report sul PC di casa. Non blocca la 0.1.0. |
| 15 | 2026-11-01 | Dati | Miglioria | Aperto | P | Rotte normali su Wikipedia da aeroporti che omaxim non vede mai (circa 340 nell'ultima prova): oggi sono escluse, perché senza conferma possono essere vecchie. Si perdono alcune rotte vere di aeroporti piccoli. |
| 16 | 2026-11-01 | Dati | Miglioria | Aperto | P | Filtro "voli sospesi" di Wikipedia: scarta anche pagine con sospensioni parziali (LED, MSQ, DME, LGG...), che perdono solo le stagionali da Wikipedia. Restano alcune stagionali ucraine (11) da pagine che non lo dichiarano. |
| 14 | 2026-11-01 | Sito | Verifica | Aperto | P | Rifiniture dopo la prova su un telefono vero: finora solo simulazione in Chrome. |
| 10 | 2026-11-01 | Dati | Miglioria | Aperto | P | Completare a mano i nomi delle compagnie senza nome. Nel file attuale: ATV, B0, DCT, FNA, GPX, HBR, TOM. |
| 13 | 2026-11-01 | Sito | Miglioria | Aperto | P | Allungare l'elenco dei nomi italiani in `sito/logica.js`: oggi copre le città principali, le altre restano come nei dati. |

## Chiusi

| N. | Data | Area | Tipo | Stato | Peso | Descrizione |
|---|---|---|---|---|---|---|
| 8 | 2026-11-01 | Scanner e sito | Funzione | Chiuso in 0.6.0 | G | Stagionali: Wikipedia + storico nello scanner, stato `annunciata`, prova del file con OurAirports + Wikipedia. |
| 9 | 2026-11-01 | Sito | Funzione | Chiuso in 0.5.0 | M | Impostazioni, Aiuto, Informazioni con fonti e changelog. Anticipato su richiesta di Davide, insieme a barra compatta, totali e nomi degli aeroporti. |
| 7 | 2026-11-01 | Sito | Funzione | Chiuso in 0.4.0 | M | Chiudi il giro: raggio, ritorni, riepilogo. |
| 6 | 2026-11-01 | Sito | Funzione | Chiuso in 0.3.0 | M | Multi-tratta: catena di tappe, aggiungi e togli tappe. |
| 5 | 2026-11-01 | Sito | Funzione | Chiuso in 0.2.0 | G | Sito base: mappa scura Leaflet, scelta partenza, archi, lista, filtri, legenda, versione visibile. |
| 12 | 2026-11-01 | Sito | Funzione | Chiuso in 0.2.0 | P | Ricerca con i nomi italiani: si può cercare "Torino" e "Milano". |
| 3 | 2026-11-01 | Scanner | Funzione | Chiuso in 0.1.0 | G | Scanner: giornate di omaxim + OurAirports, settimana ricostruita, filtro area, storico dal 4 ottobre, JSON nel formato aggiornato, `Aggiorna_Dati.bat`, con test. |
| 4 | 2026-11-01 | Scanner | Funzione | Chiuso in 0.1.0 | P | Unire `MLH` a `BSL`: sono lo stesso aeroporto. |
| 11 | 2026-11-01 | Scanner | Funzione | Chiuso in 0.1.0 | P | Togliere le rotte in elicottero: `type` = `heliport` in OurAirports più `AEI` e `VIF`. |
| 2 | 2026-11-01 | Dati | Decisione | Chiuso | P | Elicotteri: Davide ha deciso di toglierli tutti, Ceuta (JCU) compresa. Il lavoro è al punto 11. |
