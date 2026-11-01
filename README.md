# Dove_Volo

Un sito per costruire viaggi in più tappe con **voli diretti in Europa**: parti da A, voli a B, poi a C, poi torni ad A o a un aeroporto vicino. È il fratello di [Dove_Arrivo](https://github.com/dedavi97/Dove_Arrivo), che fa lo stesso con i treni regionali italiani.

**Stato:** versione 0.5.0, in costruzione. Si sceglie una partenza, si aggiungono tappe e si chiude il giro con un ritorno alla partenza o vicino, con chilometri e tempi nel riepilogo. Vedi [STATUS_REPORT.md](STATUS_REPORT.md).

## Come funziona

Un programma Python sul PC raccoglie i dati in un unico file JSON. Il sito è statico: legge quel file, senza server e senza account.

## Aprire il sito sul PC

Serve Python 3, senza installare altro. Avvia `Apri_Sito.bat`: il sito si apre nel browser. Il doppio clic su `index.html` non basta, perché i browser non gli lasciano leggere i dati.

## Fonti dei dati

| Dato | Fonte | Licenza |
|---|---|---|
| Rotte, voli a settimana, giorni | File giornalieri di [omaxim/airline-route-data](https://github.com/omaxim/airline-route-data), ricavati da flightsfrom.com | Nessuna licenza indicata |
| Aeroporti | [OurAirports](https://ourairports.com/data/) | Pubblico dominio |
| Sfondo della mappa | [Natural Earth](https://www.naturalearthdata.com/), disegnato con [Leaflet](https://leafletjs.com/) | Pubblico dominio; Leaflet BSD-2 |
| Rotte stagionali e annunciate (dalla 0.6.0) | Pagine degli aeroporti su [Wikipedia](https://en.wikipedia.org/) | CC BY-SA |

Dove_Volo è un progetto personale, aperto e gratuito. Scarica solo file pubblici e usa l'API ufficiale di Wikipedia.

## Aggiornare i dati

Serve Python 3, senza installare altro. Avvia `Aggiorna_Dati.bat`: scarica i dati, mostra cosa cambia e chiede "Pubblico? S/N". Se rispondi `S` pubblica solo il file `dati/dove_volo.json`; con qualsiasi altra risposta non cambia nulla.

Per i test automatici avvia `Esegui_Test.bat`. I test del sito richiedono Node; senza Node vengono saltati e te lo dice.

## Provare il test delle fonti

Serve Python 3, senza installare altro. Avvia `tools/test_fonti/Test_Fonti.bat`: scarica i file e scrive i risultati in `docs/REPORT_FONTI.md`, che resta sul tuo PC e non viene caricato nel repo.

## Documenti

- [STATUS_REPORT.md](STATUS_REPORT.md): a che punto siamo
- [BACKLOG.md](BACKLOG.md): cose da fare
- [CHANGELOG.md](CHANGELOG.md): cosa cambia a ogni versione
- [CLAUDE.md](CLAUDE.md): decisioni e note tecniche
