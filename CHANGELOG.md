# Changelog · Dove_Volo

Cosa cambia a ogni versione, in parole semplici.

## 0.6.0 · 1° novembre 2026

Le rotte stagionali e annunciate ora vengono anche da Wikipedia.

- Una rotta può risultare stagionale perché Wikipedia la segna così, oltre che perché è stata vista di recente. Se è noto, trovi anche il periodo.
- Nuovo stato "annunciata": rotte con una data di inizio futura. Ad esempio Bucarest-Tbilisi, annunciata dal 27 giugno 2027.
- Una rotta che vola adesso ma è stagionale lo dice: "stagionale, vola adesso".
- Dove i dati coprono solo una parte della settimana, Wikipedia evita di far passare per stagionali delle rotte attive.
- Se la fonte dei voli si ferma, il sito può vivere con i soli aeroporti e Wikipedia, mostrando solo le compagnie.
- Non vengono mostrate come attive le rotte di aeroporti con voli sospesi, come quelli ucraini.

## 0.5.0 · 1° novembre 2026

Più ordine, e nuove schede.

- Il rientro si può annullare: "Annulla il rientro" compare sia mentre scegli il ritorno sia nel riepilogo.
- Il riepilogo mostra chilometri e tempo in volo per ogni tratta e i totali. I totali sono anche in alto, accanto alle tappe.
- Le città con più aeroporti mostrano quale: Milano Malpensa, Milano Linate, Londra Heathrow, Parigi Orly.
- La barra in alto è più compatta: da due tappe in poi la catena prende il posto del campo di ricerca e la mappa ha più spazio.
- Nuove schede: Opzioni (raggio predefinito, rotte stagionali), Aiuto e Info (fonti, licenze e novità).

## 0.4.0 · 1° novembre 2026

Il giro ora si chiude.

- Con almeno due tappe compare "Chiudi il giro": un cursore sceglie quanto lontano dalla partenza puoi atterrare, da 0 a 400 km, con un cerchio verde sulla mappa.
- I voli di ritorno nel raggio sono verdi e in lista, con la distanza dalla partenza; gli altri sono grigi. Si sceglie col pulsante "Scegli" o toccando il punto verde.
- Il riepilogo mostra ogni tratta con compagnie, voli a settimana, giorni e distanza, più i km totali e dove atterri rispetto alla partenza.
- Dal riepilogo si può cambiare il ritorno, togliere una tappa o aggiungerne altre.
- Lo sfondo della mappa è il mondo intero, non più solo la zona delle rotte.

## 0.3.0 · 1° novembre 2026

Ora si costruisce il giro.

- Il pulsante "+" di una meta la aggiunge come tappa, e lo stesso fa un tocco sul suo punto in mappa. Poi compaiono le mete dirette da lì.
- In alto c'è la catena delle tappe, con una "×" su ognuna e il pulsante "Ricomincia". Sulla mappa il giro è bianco e spesso.
- Se togli una tappa e tra le due vicine non c'è un volo diretto, il giro si taglia da lì in poi e il sito lo scrive.
- Si possono trovare per nome Bergamo, Treviso, Charleroi, Beauvais e Weeze, che ora si chiamano così anche nelle liste. Prima la ricerca di "Bergamo" non trovava nulla.
- Da telefono la partenza non finisce più sotto i pulsanti della mappa: lì si ingrandisce con due dita.

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
