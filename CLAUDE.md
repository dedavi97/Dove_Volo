# CLAUDE.md · Dove_Volo

Ponte tra il PC di casa e quello di lavoro: qui c'è tutto ciò che serve per lavorare al progetto.

**File solo sul PC di casa, mai nel repo (scelta di Davide):** `HANDOFF_Dove_Volo_v1.md`, `docs/REPORT_FONTI.md`, `tools/test_fonti/note_report.md`. Sono in `.gitignore`: non caricarli. Dove l'handoff non coincide con questo file, vale questo file.

## Regole di lavoro

- Davide non è uno sviluppatore: spiega ogni scelta e ogni problema in parole semplici, con esempi. Si scrive in italiano.
- Tappe piccole, una alla volta: commit dedicato, test verdi, numero di versione, report a Davide.
- **Push solo dopo conferma esplicita di Davide.**
- Se qualcosa non torna o manca, chiedi a Davide prima di inventare. Le decisioni qui sotto non si riaprono.
- SemVer: PATCH per fix e piccole modifiche, MINOR per una nuova funzione. Il numero sale a ogni commit che tocca codice eseguito, mai per sola documentazione. Prima versione di codice: `0.1.0`. Tag `vX.Y.Z` per ogni versione.
- Versione in un solo punto del codice e sempre visibile nel sito.
- A ogni versione aggiorna README, STATUS_REPORT, BACKLOG, CHANGELOG, `tests/README.md` e questo file.
- Mai `git add -A` alla cieca: controlla `git status` e committa solo i file del progetto. Niente credenziali in file o in chat.
- Tutto ciò che si avvia da riga di comando ha il suo `.bat`.

## Il progetto

Sito per costruire viaggi multi-tratta con voli diretti in Europa. Esempio: scelgo Torino (TRN) e la mappa mostra le mete dirette; tocco Bucarest (OTP), poi Tbilisi (TBS); "Chiudi il giro" evidenzia i voli che tornano a TRN o entro X km (BGY, MXP); in basso il riepilogo TRN > OTP > TBS > BGY con compagnie e giorni.

**Nella v1:** qualsiasi aeroporto di partenza; per ogni tratta compagnie, voli a settimana e giorni; stagionali tratteggiate, con periodo se noto; raggio di ritorno impostabile (default 150 km).

**Fuori dalla v1:** prezzi, treni, elicotteri. Rimandati alla v2: compatibilità dei giorni tra tratte, link condivisibile, scali, export.

## Architettura

- **Scanner Python locale:** scarica i dati e produce **un solo file JSON** con tipo, versione del formato e data. Un solo punto del codice legge e scrive quel file.
- **Sito statico:** vanilla JS, HTML e CSS, con Leaflet. Niente framework, build o server. Pubblicato su GitHub Pages.
- **`Aggiorna_Dati.bat`:** scansione > riepilogo delle differenze col file precedente (rotte nuove, sparite, cambiate) > "Pubblico? S/N" > commit e push **del solo file dati**.
- Noi non facciamo scraping: scarichiamo file pubblici e usiamo l'API ufficiale di Wikipedia, con User-Agent descrittivo e richieste lente.
- Le chiamate dal browser verso siti di prenotazione vengono rifiutate (CORS): i dati live richiederebbero un server, che non vogliamo.
- Blocchi anti-bot: non si aggirano mai. Se una fonte blocca, si segnala e si cerca un'alternativa aperta.
- Fonti sempre citate nel sito con la licenza, in Informazioni.

## Struttura

| Percorso | Cosa contiene |
|---|---|
| `VERSIONE` | L'unico punto in cui è scritta la versione |
| `dati/dove_volo.json` | Il file dati, creato alla prima pubblicazione. Il lato Python lo legge e scrive solo da `scanner/dati_file.py` |
| `scanner/fonti.py` | Download e cache |
| `scanner/area.py` | Aeroporti dell'area, eliporti, alias `MLH` |
| `scanner/settimana.py` | Ricostruzione della settimana |
| `scanner/costruisci.py` | Storico, stati e contenuto del file |
| `scanner/differenze.py` | Riepilogo delle differenze |
| `scanner/pubblica.py` | Commit e push del solo file dati |
| `scanner/__main__.py` | Il flusso completo |
| `cache/` | File scaricati dallo scanner, ignorati da git |
| `tools/test_fonti/` | Test delle fonti della Tappa 1: `test_fonti.py`, `Test_Fonti.bat` |
| `tools/test_fonti/dati_scaricati/` | File scaricati (156 MB), ignorati da git, riscaricabili |
| `tests/` | Test del progetto, vedi `tests/README.md` |

Il sito non esiste ancora.

## Comandi

- Aggiornare i dati: `Aggiorna_Dati.bat`. Opzioni: `--prova FILE` scrive in FILE senza toccare git, `--senza-omaxim` produce un file senza frequenze.
- Test automatici: `Esegui_Test.bat`. Scanner e test usano solo la libreria standard di Python.
- Test delle fonti: `tools\test_fonti\Test_Fonti.bat`. Aggiungi `--aggiorna` per riscaricare tutto. Usa solo la libreria standard di Python.
- Per la parte a parole del report si cambia `note_report.md`, non `docs/REPORT_FONTI.md`, che viene riscritto a ogni esecuzione. Senza `note_report.md` (PC di lavoro) lo script scrive solo le tabelle.

## Decisioni del 1° novembre 2026

1. **Fonte principale: i file giornalieri di omaxim** (`days/`), sommati da noi. Non il file settimanale, che è fermo. Noi scarichiamo solo file pubblici. Davide conosce il modo in cui omaxim ottiene i dati e ha accettato.
2. **Jonty è tolto dalle fonti:** ha la stessa origine di omaxim, quindi non è una riserva.
3. **Wikipedia fa da rete di sicurezza.**
4. **flightsfrom non si usa e non si contatta.**
5. **Il sito non dipende mai dalle frequenze.** `voli_sett` e `giorni` possono mancare: vuoti, mai zero. Senza omaxim lo scanner produce comunque un file e il sito mostra solo le compagnie.
6. **Regola stagionali:** una rotta assente adesso resta visibile come `stagionale` se Wikipedia la segna Seasonal oppure se è stata vista negli ultimi 12 mesi. Altrimenti si nasconde, ma resta nel file.
7. **Storico iniziale:** alla prima esecuzione lo scanner importa il file omaxim del 4 ottobre 2026 (orario estivo), con `vista_ultima` uguale alla sua data.
8. **Niente elicotteri:** fuori tutte le rotte da e per gli eliporti, Ceuta compresa, vedi sotto.
9. **Compagnie senza nome** (ATV, B0, DCT, FNA, GPX, HBR, HTY, LID, LTR, TOM): per ora si mostra il codice.

### Come si applicano prima della 0.5.0

Wikipedia entra nello scanner solo con la 0.5.0 (confermato da Davide). Quindi:
- la 0.1.0 prova la tolleranza con un file **senza frequenze**; il file con OurAirports + Wikipedia si prova dalla 0.5.0;
- fino alla 0.5.0 una rotta è `stagionale` solo se vista negli ultimi 12 mesi, e lo stato `annunciata` non esiste ancora.

### Storico iniziale: due dettagli

- Il file del 4 ottobre si scarica dal suo commit preciso, non dall'ultima versione: se omaxim riparte e lo sovrascrive, lo storico iniziale non cambia.
- Quel file ha voli e giorni per rotta, non per compagnia. Le rotte importate hanno quindi solo le compagnie, con `voli_sett` e `giorni` vuoti.

## Area: Europa larga

Una rotta vale solo se **entrambi** gli aeroporti sono nell'area. Paesi inclusi (codici ISO):
- UE27, GB, IE, NO, IS, CH, LI
- Balcani: AL, BA, ME, RS, MK, XK
- MD, UA, BY
- TR (intera), GE, AM, AZ, CY
- Territori: FO, GI, IM, JE, GG, SJ
- Russia solo europea: RU con longitudine < 60° E

Canarie, Azzorre e Madeira sono già dentro ES e PT. Melilla (MLN) resta dentro. Il paese si prende da OurAirports: BON, CUR, SXM e simili, che omaxim segna come Europa, restano fuori.

### Eliporti e codici particolari

Verificati il 1° novembre 2026.

| Codice | Cos'è | Esito |
|---|---|---|
| `MLH` | EuroAirport Basilea-Mulhouse-Friburgo, ICAO `LFSB`: lo stesso aeroporto di `BSL` con un secondo codice | Da unire a `BSL` nello scanner, altrimenti sulla mappa compare due volte |
| `AEI` | Eliporto di Algeciras, che omaxim chiama "Airport". OurAirports non lo conosce | Fuori |
| `VIF` | Eliporto di Vieste. OurAirports non lo conosce | Fuori |
| `JCU` | Eliporto di Ceuta: ha solo rotte in elicottero | Fuori |
| `TQR` | Eliporto delle Tremiti | Fuori |
| `VRY` | Eliporto di Værøy | Fuori |

Regola per lo scanner: fuori ogni aeroporto con `type` = `heliport` in OurAirports, più l'elenco fisso `AEI`, `VIF`. Il controllo ha guardato tipo e nome: se ne emergono altri, si aggiungono all'elenco.

## Formato del file dati

Regola generale: `giorni` = 7 caratteri da lunedì a domenica, `1` = vola. Esempio di riferimento:

```json
{
  "tipo": "dove_volo_dati",
  "versione_formato": 1,
  "aggiornato": "2026-11-08",
  "fonti": [{"nome": "...", "url": "...", "licenza": "...", "data": "..."}],
  "compagnie": {"W6": "Wizz Air"},
  "aeroporti": {
    "TRN": {"nome": "Torino Caselle", "citta": "Torino", "paese": "IT", "lat": 45.20, "lon": 7.65,
            "settimana_dal": "2026-11-02", "settimana_completa": true}
  },
  "rotte": [
    {"da": "TRN", "a": "OTP", "stato": "attiva", "stagionale_wiki": false, "km": 1400, "durata_min": 135,
     "compagnie": [{"iata": "W6", "voli_sett": 4, "giorni": "1010101"}],
     "periodo": null, "vista_ultima": "2026-11-08", "fonte": "omaxim"}
  ]
}
```

- `stato`: `attiva` (presente nella settimana ricostruita), `stagionale` (vedi regola), `annunciata` (su Wikipedia con "begins" e data futura), `nascosta` (sparita da più di 12 mesi: resta nel file, il sito non la mostra). `nascosta` è il modo in cui si applica la regola stagionali.
- `citta` viene da omaxim, perché OurAirports dà il comune ("Ferno" per Malpensa). Si importa alla prima esecuzione e poi si conserva dal file precedente; per un aeroporto nuovo si usa OurAirports.
- `compagnie` in cima può avere un nome vuoto: il sito mostra il codice.
- `vista_ultima` non supera mai la data di oggi, anche se le giornate di omaxim guardano una settimana avanti.
- Con `settimana_completa: false` uno `0` in `giorni` vuol dire "non visto", non "non vola".
- `stagionale_wiki` è separato da `stato`, perché una rotta può volare adesso ed essere stagionale.
- `periodo` ha `dal` e `al`, da begins, resumes ed ends.
- `km` si calcola dalle coordinate; `durata_min` è la mediana calcolata dagli orari.
- `voli_sett` e `giorni` sono per compagnia; `vista_ultima` si salva dalla 0.1.0.

## Come si ricostruisce la settimana

Per ogni aeroporto e giorno della settimana si prende la giornata più recente che lo contiene, poi si contano i voli per rotta e compagnia. Si usano solo le giornate dall'ultimo cambio d'orario (ultima domenica di marzo e di ottobre), al massimo 21; se sono meno di 7, le ultime 7.

Formato di un volo nei file giornalieri: `[meta, compagnia, numero, partenza, arrivo, fuso_partenza, fuso_arrivo]`, con i fusi in minuti. Esempio: `["FRA", "EN", "EN297", "06:00", "07:25", "60", "60"]`.

## Sito: come deve essere

Tema scuro, mobile first, font Inter (codici IATA in JetBrains Mono), touch target di almeno 44 px. Colori come variabili CSS, un colore = un significato:
- sfondo `#0E1116`, superfici `#161B22`, bordi `#2A313C`, testo `#E6EDF3`, secondario `#9AA4B2`
- blu `#4FA3FF` = rotta attiva
- arancio `#F2A33A` tratteggiato = stagionale o annunciata
- bianco spesso = tratte già nel giro
- verde `#3DD68C` = ritorni dentro il raggio; grigio = possibili ma fuori raggio

Tre momenti nella stessa pagina:
1. **Partenza:** header "Dove_Volo" + versione; campo "Partenza" con ricerca per città o codice; mappa con archi dall'aeroporto scelto; legenda; pannello in basso trascinabile con "N mete dirette", filtri a pillola (Attive, Stagionali, Paese) e lista: codice, città, voli/sett, compagnie, pallini dei 7 giorni, pulsante "+". Toccare un punto sulla mappa equivale al "+".
2. **Tappe successive:** in alto la catena a pillole (TRN > OTP > "scegli tappa 3") e "Ricomincia"; mappa con il giro in bianco e gli archi dall'ultima tappa; stessa lista.
3. **Chiudi il giro:** cursore "Ritorno entro X km da [partenza]" (0-400, passo 10) con cerchio verde sulla mappa; lista dei ritorni nel raggio con distanza dalla partenza; card riepilogo con ogni tratta, compagnia e giorni. Deve essere possibile togliere una tappa.

Sempre raggiungibili: Impostazioni (raggio predefinito, ecc.), Aiuto, Informazioni (versione, changelog in parole semplici, fonti e licenze, data dei dati). Stati vuoti che spiegano il perché: "Da qui nessun volo diretto nell'area", "Nessun ritorno entro 150 km: prova ad allargare il raggio".

## Trappole

- **Nessuna giornata di omaxim è completa.** Sommandole, nel test 426 aeroporti dell'area su 582 hanno tutti e 7 i giorni. Per gli altri i numeri sono bassi: è il motivo di `settimana_completa`.
- **Il file settimanale di omaxim è fermo al 4 ottobre 2026** e ha ancora l'orario estivo.
- **omaxim può fermarsi all'improvviso:** è il lavoro di una sola persona.
- **Wikipedia:** il modello si chiama sia `Airport-dest-list` sia `Airport destination list`. La mappa da nome pagina a codice IATA passa da Wikidata (proprietà P238).
- **Wikimedia può rispondere `maxlag`:** bisogna aspettare e riprovare, e non salvare l'errore nella cache.
- **Rotte assenti da aeroporti con settimana incompleta:** diventano `stagionale` anche se magari volano in un giorno che manca. Nella prima prova 180 aeroporti su 603 non hanno la settimana completa.
- **Senza omaxim** le rotte conservano lo stato precedente finché non superano i 12 mesi: non sappiamo se volano, quindi non le segniamo come sparite.
- **Il push di `Aggiorna_Dati.bat`** spinge tutto il ramo: per questo lo scanner si ferma prima di iniziare se ci sono commit non pubblicati o se GitHub è più avanti.
- **Durate sporche:** nella prima prova 4 rotte su 17.520 hanno una durata assurda rispetto ai km (es. MRV>SUI, 219 km e 1435 minuti). Vengono dalla fonte e non sono corrette.
- **Cronologia git:** un file già committato resta nella cronologia anche se lo cancelli dopo. Prima di ogni commit controlla che i file solo locali non ci siano.
