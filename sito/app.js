// La pagina: legge i dati, disegna mappa, giro e lista, risponde ai tocchi.
import {
  cercaAeroporti, contaPartenze, controllaDati, filtraMete, leggiChangelog, leggiImpostazioni, meteDa, nomeCitta,
  nomePaese, paesiDelleMete, puntiArco, riepilogoGiro, salvaImpostazioni, testoData, testoDurata, testoGiorni, testoKm,
  testoMete, testoRitorni, testoStato, testoTappeTolte, testoTotale, testoTratte, testoVicino, togliTappa, trovaRitorni,
} from "./logica.js";

const L = window.L;
const FILE_DATI = "dati/dove_volo.json";
const FILE_MAPPA = "sito/mondo.json";
const CENTRO_EUROPA = [50, 14];
// Il mondo intero. Deve restare piu' grande di cio' che mostra un telefono allo zoom minimo:
// se e' piu' piccolo, Leaflet ricentra la mappa sul mezzo di questi limiti e sposta l'inquadratura.
const LIMITI_MAPPA = [[-85, -180], [85, 180]];
const SCHEDE = ["giro", "impostazioni", "aiuto", "informazioni"];
const CREDITI_MAPPA = [
  { nome: "Natural Earth", url: "https://www.naturalearthdata.com/", licenza: "Pubblico dominio", ruolo: "confini sulla mappa" },
  { nome: "Leaflet", url: "https://leafletjs.com/", licenza: "BSD-2", ruolo: "disegno della mappa" },
];

// La memoria del browser puo' non esistere o dare errore appena la si tocca.
let memoria = null;
try {
  memoria = window.localStorage;
} catch {
  memoria = null;
}
const impostazioni = leggiImpostazioni(memoria);

const stile = getComputedStyle(document.documentElement);
const colore = (nome) => stile.getPropertyValue(nome).trim();
const COLORI = {
  attiva: colore("--attiva"),
  stagionale: colore("--stagionale"),
  ritorno: colore("--ritorno"),
  punto: colore("--secondario"),
  giro: colore("--testo"),
  sfondo: colore("--sfondo"),
  terra: colore("--terra"),
  confine: colore("--bordo"),
};

const pagina = {
  versione: document.getElementById("versione"),
  ricerca: document.getElementById("ricerca"),
  campo: document.getElementById("partenza"),
  togli: document.getElementById("togli-partenza"),
  suggerimenti: document.getElementById("suggerimenti"),
  giro: document.getElementById("giro"),
  giroRiga: document.getElementById("giro-riga"),
  giroTotale: document.getElementById("giro-totale"),
  catena: document.getElementById("catena"),
  ricomincia: document.getElementById("ricomincia"),
  messaggioGiro: document.getElementById("messaggio-giro"),
  legenda: document.getElementById("legenda"),
  legendaAttiva: document.getElementById("legenda-attiva"),
  legendaStagionale: document.getElementById("legenda-stagionale"),
  legendaDentro: document.getElementById("legenda-dentro"),
  legendaFuori: document.getElementById("legenda-fuori"),
  legendaGiro: document.getElementById("legenda-giro"),
  chiudiGiro: document.getElementById("chiudi-giro"),
  ritorno: document.getElementById("ritorno"),
  raggio: document.getElementById("raggio"),
  raggioTesto: document.getElementById("raggio-testo"),
  azioniRientro: document.getElementById("azioni-rientro"),
  annullaRientro: document.getElementById("annulla-rientro"),
  riepilogo: document.getElementById("riepilogo"),
  riepilogoTitolo: document.getElementById("riepilogo-titolo"),
  riepilogoTratte: document.getElementById("riepilogo-tratte"),
  riepilogoTotale: document.getElementById("riepilogo-totale"),
  riepilogoFine: document.getElementById("riepilogo-fine"),
  cambiaRitorno: document.getElementById("cambia-ritorno"),
  pannello: document.getElementById("pannello"),
  maniglia: document.getElementById("maniglia"),
  titolo: document.getElementById("titolo"),
  filtri: document.getElementById("filtri"),
  filtroAttive: document.getElementById("filtro-attive"),
  filtroStagionali: document.getElementById("filtro-stagionali"),
  filtroPaese: document.getElementById("filtro-paese"),
  avviso: document.getElementById("avviso"),
  vuoto: document.getElementById("vuoto"),
  lista: document.getElementById("lista"),
  fonti: document.getElementById("fonti"),
  opzioneRaggio: document.getElementById("opzione-raggio"),
  opzioneRaggioTesto: document.getElementById("opzione-raggio-testo"),
  opzioneStagionali: document.getElementById("opzione-stagionali"),
  opzioniStato: document.getElementById("opzioni-stato"),
  infoStato: document.getElementById("info-stato"),
  infoFonti: document.getElementById("info-fonti"),
  infoChangelog: document.getElementById("info-changelog"),
};

const stato = {
  dati: null,
  partenze: {},
  tappe: [], // il giro: la prima e' la partenza, le mete si cercano dall'ultima
  fase: "tappe", // "tappe": si aggiungono tappe; "ritorno": si sceglie come tornare; "chiuso": giro finito
  raggio: impostazioni.raggio,
  ritornoAggiunto: false, // true se l'ultima tappa e' stata scelta come ritorno e non aggiunta col "+"
  mete: [],
  selezionata: null,
  filtri: { attive: true, stagionali: impostazioni.stagionali, paese: "" },
  trovati: [],
  evidenziato: -1,
};

const partenza = () => stato.tappe[0] || null;
const ultimaTappa = () => stato.tappe[stato.tappe.length - 1] || null;

function testoAeroporto(codice) {
  return `${codice} · ${nomeCitta(stato.dati.aeroporti[codice], codice)}`;
}

// ---------------------------------------------------------------- mappa

const mappa = L.map("mappa", {
  zoomControl: false,
  attributionControl: false,
  minZoom: 2,
  maxZoom: 9,
  zoomSnap: 0.25,
  maxBounds: LIMITI_MAPPA,
  maxBoundsViscosity: 0.8,
}).setView(CENTRO_EUROPA, 4);
L.control.zoom({ position: "topright" }).addTo(mappa);

// La tolleranza allarga la zona toccabile intorno ai punti piccoli.
const disegno = L.canvas({ padding: 0.3, tolerance: 12 });

// Lo sfondo sono i confini dei paesi, salvati nel sito: nessun servizio esterno da cui dipendere.
fetch(FILE_MAPPA)
  .then((r) => (r.ok ? r.json() : null))
  .then((confini) => {
    if (!confini) return;
    L.geoJSON(confini, {
      renderer: disegno, // lo stesso dei punti: un secondo strato sopra bloccherebbe i tocchi
      interactive: false,
      style: { color: COLORI.confine, weight: 1, fillColor: COLORI.terra, fillOpacity: 1 },
    }).addTo(mappa).bringToBack();
  })
  .catch(() => {});

const livelloArchi = L.layerGroup().addTo(mappa);
const livelloPunti = L.layerGroup().addTo(mappa);

function puntoCliccabile(aeroporto, opzioni, azione) {
  const punto = L.circleMarker([aeroporto.lat, aeroporto.lon], { renderer: disegno, ...opzioni });
  punto.on("click", azione);
  return punto;
}

function etichettaFissa(aeroporto, testo) {
  return L.tooltip({ permanent: true, direction: "auto", offset: [6, 0], className: "etichetta" })
    .setLatLng([aeroporto.lat, aeroporto.lon])
    .setContent(testo);
}

function disegnaTuttiGliAeroporti() {
  livelloArchi.clearLayers();
  livelloPunti.clearLayers();
  for (const [codice, aeroporto] of Object.entries(stato.dati.aeroporti)) {
    if (!stato.partenze[codice]) continue;
    puntoCliccabile(aeroporto, {
      radius: 3, stroke: false, fillColor: COLORI.punto, fillOpacity: 0.8,
    }, () => iniziaGiro(codice)).bindTooltip(testoAeroporto(codice), { className: "etichetta" })
      .addTo(livelloPunti);
  }
}

function disegnaMete(origine, visibili) {
  for (const meta of visibili) {
    const scelta = meta.codice === stato.selezionata;
    const stagionale = meta.stato !== "attiva";
    L.polyline(puntiArco(origine, meta.aeroporto), {
      renderer: disegno,
      interactive: false,
      color: stagionale ? COLORI.stagionale : COLORI.attiva,
      weight: scelta ? 3 : 1.25,
      opacity: scelta ? 1 : 0.55,
      dashArray: stagionale ? "4 6" : null,
    }).addTo(livelloArchi);
    puntoCliccabile(meta.aeroporto, {
      radius: scelta ? 6 : 4,
      stroke: false,
      fillColor: stagionale ? COLORI.stagionale : COLORI.attiva,
      fillOpacity: 1,
    }, () => aggiungiTappa(meta.codice))
      .bindTooltip(`${meta.codice} · ${meta.citta}`, { className: "etichetta" })
      .addTo(livelloPunti);
  }
}

function disegnaRitorni(origine, { dentro, fuori }) {
  const partenzaGiro = stato.dati.aeroporti[partenza()];
  if (stato.raggio > 0) {
    L.circle([partenzaGiro.lat, partenzaGiro.lon], {
      renderer: disegno, interactive: false, radius: stato.raggio * 1000,
      color: COLORI.ritorno, weight: 1.5, fillColor: COLORI.ritorno, fillOpacity: 0.1,
    }).addTo(livelloArchi);
  }
  for (const meta of fuori) {
    L.polyline(puntiArco(origine, meta.aeroporto), {
      renderer: disegno, interactive: false, color: COLORI.punto, weight: 1, opacity: 0.3,
      dashArray: meta.stato === "attiva" ? null : "4 6",
    }).addTo(livelloArchi);
    L.circleMarker([meta.aeroporto.lat, meta.aeroporto.lon], {
      renderer: disegno, radius: 3, stroke: false, fillColor: COLORI.punto, fillOpacity: 0.7,
    }).bindTooltip(`${meta.codice} · ${meta.citta}`, { className: "etichetta" }).addTo(livelloPunti);
  }
  for (const meta of dentro) {
    const scelta = meta.codice === stato.selezionata;
    L.polyline(puntiArco(origine, meta.aeroporto), {
      renderer: disegno, interactive: false, color: COLORI.ritorno, weight: scelta ? 3 : 2, opacity: 0.9,
      dashArray: meta.stato === "attiva" ? null : "4 6",
    }).addTo(livelloArchi);
    puntoCliccabile(meta.aeroporto, {
      radius: scelta ? 7 : 5, stroke: false, fillColor: COLORI.ritorno, fillOpacity: 1,
    }, () => scegliRitorno(meta.codice))
      .bindTooltip(`${meta.codice} · ${meta.citta}`, { className: "etichetta" })
      .addTo(livelloPunti);
  }
}

// Il giro va disegnato per ultimo: bianco e spesso, sopra agli archi delle mete.
function disegnaGiro() {
  const aeroporti = stato.tappe.map((codice) => stato.dati.aeroporti[codice]);
  for (let i = 1; i < aeroporti.length; i++) {
    L.polyline(puntiArco(aeroporti[i - 1], aeroporti[i]), {
      renderer: disegno, interactive: false, color: COLORI.giro, weight: 3, opacity: 1,
    }).addTo(livelloArchi);
  }
  const visti = new Set();
  stato.tappe.forEach((codice, i) => {
    const ultima = i === stato.tappe.length - 1;
    L.circleMarker([aeroporti[i].lat, aeroporti[i].lon], {
      renderer: disegno, interactive: false, radius: ultima ? 7 : 5, color: COLORI.sfondo, weight: 2,
      fillColor: COLORI.giro, fillOpacity: 1,
    }).addTo(livelloPunti);
    if (!visti.has(codice) && stato.tappe.length > 1) {
      etichettaFissa(aeroporti[i], codice).addTo(livelloPunti);
    }
    visti.add(codice);
  });
}

// Lo spazio da lasciare libero intorno alle rotte: legenda e pulsanti stanno sopra alla mappa.
function marginiMappa() {
  const dito = window.matchMedia("(pointer: coarse)").matches;
  return {
    paddingTopLeft: [28, 56],
    paddingBottomRight: [dito ? 28 : 68, spazioOccupatoDalPannello() + 24],
    maxZoom: 7,
  };
}

function disegnaRotte(adatta) {
  livelloArchi.clearLayers();
  livelloPunti.clearLayers();
  const origine = stato.dati.aeroporti[ultimaTappa()];
  let mostrate = [];
  if (stato.fase === "tappe") {
    mostrate = filtraMete(stato.mete, stato.filtri);
    disegnaMete(origine, mostrate);
  } else if (stato.fase === "ritorno") {
    const ritorni = trovaRitorni(stato.dati, stato.tappe, stato.raggio);
    mostrate = ritorni.dentro;
    disegnaRitorni(origine, ritorni);
  }
  disegnaGiro();

  const scelta = mostrate.find((m) => m.codice === stato.selezionata);
  if (scelta) etichettaFissa(scelta.aeroporto, `${scelta.codice} · ${scelta.citta}`).addTo(livelloPunti);

  if (adatta) inquadra(mostrate);
}

function inquadra(mostrate) {
  const limiti = L.latLngBounds([
    ...stato.tappe.map((codice) => stato.dati.aeroporti[codice]),
    ...mostrate.map((m) => m.aeroporto),
  ].map((a) => [a.lat, a.lon]));
  if (stato.fase === "ritorno" && stato.raggio > 0) {
    const centro = stato.dati.aeroporti[partenza()];
    limiti.extend(L.latLng(centro.lat, centro.lon).toBounds(stato.raggio * 2000));
  }
  if (limiti.getNorthEast().equals(limiti.getSouthWest())) {
    mappa.setView(limiti.getCenter(), 6);
  } else {
    mappa.fitBounds(limiti, marginiMappa());
  }
}

function spazioOccupatoDalPannello() {
  return schermoLargo() ? 0 : pagina.pannello.offsetHeight;
}

// ---------------------------------------------------------------- catena del giro

function crea(tag, classe, testo) {
  const elemento = document.createElement(tag);
  if (classe) elemento.className = classe;
  if (testo !== undefined) elemento.textContent = testo;
  return elemento;
}

// La catena e i suoi messaggi cambiano l'altezza della mappa: Leaflet va avvisato prima di inquadrare.
function aggiornaMisureMappa() {
  mappa.invalidateSize({ pan: false });
}

// Con una tappa basta il campo Partenza; da due in poi la catena prende il suo posto e lascia spazio alla mappa.
function disegnaCatena() {
  const giroVero = stato.tappe.length >= 2;
  pagina.ricerca.hidden = giroVero;
  pagina.giro.hidden = !giroVero && pagina.messaggioGiro.hidden;
  pagina.giroRiga.hidden = !giroVero;
  pagina.giroTotale.textContent = giroVero ? testoGiroInBreve() : "";
  disegnaLegenda();
  const voci = stato.tappe.map((codice, i) => {
    const voce = crea("li");
    const tappa = crea("span", "tappa");
    tappa.title = testoAeroporto(codice);
    const togli = crea("button", "tappa-togli", "×");
    togli.type = "button";
    togli.setAttribute("aria-label", `Togli ${testoAeroporto(codice)} dal giro`);
    togli.addEventListener("click", () => rimuoviTappa(i));
    tappa.append(crea("span", "codice", codice), togli);
    voce.append(tappa);
    return voce;
  });
  if (stato.fase !== "chiuso") {
    const prossima = crea("li");
    const invito = stato.fase === "ritorno" ? "scegli il ritorno" : `scegli tappa ${stato.tappe.length + 1}`;
    prossima.append(crea("span", "tappa-prossima", invito));
    voci.push(prossima);
  }
  pagina.catena.replaceChildren(...voci);
  pagina.catena.scrollLeft = pagina.catena.scrollWidth;
}

function testoGiroInBreve() {
  const riepilogo = riepilogoGiro(stato.dati, stato.tappe);
  return `${testoTratte(riepilogo.tratte.length)} · ${testoTotale(riepilogo)}`;
}

function disegnaLegenda() {
  pagina.legenda.hidden = stato.fase === "chiuso";
  pagina.legendaAttiva.hidden = stato.fase !== "tappe";
  pagina.legendaStagionale.hidden = stato.fase !== "tappe";
  pagina.legendaDentro.hidden = stato.fase !== "ritorno";
  pagina.legendaFuori.hidden = stato.fase !== "ritorno";
  pagina.legendaGiro.hidden = stato.tappe.length < 2;
}

function mostraMessaggioGiro(testo) {
  pagina.messaggioGiro.textContent = testo;
  pagina.messaggioGiro.hidden = !testo;
}

// ---------------------------------------------------------------- lista

function pallini(giorni) {
  const gruppo = crea("span", "giorni");
  gruppo.setAttribute("role", "img");
  gruppo.setAttribute("aria-label", testoGiorni(giorni));
  gruppo.title = testoGiorni(giorni);
  giorni.forEach((vola) => gruppo.append(crea("span", vola ? "giorno vola" : "giorno")));
  return gruppo;
}

function testoCompagnie(meta) {
  if (!meta.compagnie.length) return "Compagnia non indicata";
  return meta.compagnie.map((c) => (c.voli_sett ? `${c.nome} ${c.voli_sett}` : c.nome)).join(" · ");
}

function rigaMeta(meta) {
  const riga = crea("button", meta.stato === "attiva" ? "meta" : "meta stagionale");
  riga.type = "button";
  riga.dataset.codice = meta.codice;
  riga.setAttribute("aria-pressed", String(meta.codice === stato.selezionata));
  riga.addEventListener("click", () => selezionaMeta(meta.codice));

  const centro = crea("span");
  const nome = crea("span", "meta-nome", meta.citta);
  nome.append(crea("span", "meta-paese", ` · ${nomePaese(meta.aeroporto.paese)}`));
  centro.append(nome, crea("span", "meta-dettagli", testoCompagnie(meta)));

  const dettagli = [testoKm(meta.km), testoDurata(meta.durata), testoStato(meta)].filter(Boolean);
  centro.append(crea("span", "meta-dettagli", dettagli.join(" · ")));

  const destra = crea("span", "meta-destra");
  if (meta.voliSett) destra.append(crea("span", "meta-voli", `${meta.voliSett} voli/sett`));
  if (meta.giorni) destra.append(pallini(meta.giorni));
  riga.append(crea("span", "codice", meta.codice), centro, destra);

  const aggiungi = crea("button", "aggiungi", "+");
  aggiungi.type = "button";
  aggiungi.setAttribute("aria-label", `Aggiungi ${meta.citta} come tappa ${stato.tappe.length + 1}`);
  aggiungi.addEventListener("click", () => aggiungiTappa(meta.codice));

  const voce = crea("li", "riga-meta");
  voce.append(riga, aggiungi);
  return voce;
}

function rigaRitorno(meta, cittaPartenza) {
  const riga = crea("button", "meta ritorno-riga");
  riga.type = "button";
  riga.dataset.codice = meta.codice;
  riga.setAttribute("aria-pressed", String(meta.codice === stato.selezionata));
  riga.addEventListener("click", () => selezionaMeta(meta.codice));

  const centro = crea("span");
  const nome = crea("span", "meta-nome", meta.citta);
  nome.append(crea("span", "meta-paese", ` · ${nomePaese(meta.aeroporto.paese)}`));
  centro.append(nome, crea("span", "meta-vicino", testoVicino(meta.distanza, cittaPartenza)));
  centro.append(crea("span", "meta-dettagli", testoCompagnie(meta)));
  const dettagli = [testoKm(meta.km), testoDurata(meta.durata), testoStato(meta)].filter(Boolean);
  centro.append(crea("span", "meta-dettagli", dettagli.join(" · ")));

  const destra = crea("span", "meta-destra");
  if (meta.voliSett) destra.append(crea("span", "meta-voli", `${meta.voliSett} voli/sett`));
  if (meta.giorni) destra.append(pallini(meta.giorni));
  riga.append(crea("span", "codice", meta.codice), centro, destra);

  const scegli = crea("button", "scegli", "Scegli");
  scegli.type = "button";
  scegli.setAttribute("aria-label", `Torna a ${meta.citta}`);
  scegli.addEventListener("click", () => scegliRitorno(meta.codice));

  const voce = crea("li", "riga-meta");
  voce.append(riga, scegli);
  return voce;
}

function mostraVuoto(testo) {
  pagina.vuoto.textContent = testo;
  pagina.vuoto.hidden = !testo;
}

function disegnaAvviso() {
  const origine = stato.dati.aeroporti[ultimaTappa()];
  const parziale = stato.fase !== "chiuso" && !origine.settimana_completa && stato.mete.some((m) => m.voliSett);
  pagina.avviso.hidden = !parziale;
  pagina.avviso.textContent = parziale
    ? "Per questo aeroporto manca qualche giorno nei dati: voli e giorni possono essere più di così."
    : "";
}

function disegnaLista() {
  const visibili = filtraMete(stato.mete, stato.filtri);
  const attive = stato.mete.filter((m) => m.stato === "attiva").length;
  pagina.titolo.textContent = `${testoMete(visibili.length)} da ${ultimaTappa()}`;
  pagina.filtroAttive.textContent = `Attive ${attive}`;
  pagina.filtroStagionali.textContent = `Stagionali ${stato.mete.length - attive}`;
  pagina.lista.replaceChildren(...visibili.map(rigaMeta));

  pagina.filtri.hidden = !stato.mete.length;
  if (!stato.mete.length) {
    mostraVuoto("Da qui nessun volo diretto nell'area.");
  } else if (!visibili.length) {
    mostraVuoto("Nessuna meta con questi filtri: prova ad allargarli.");
  } else {
    mostraVuoto("");
  }
}

function disegnaListaRitorni() {
  const { dentro } = trovaRitorni(stato.dati, stato.tappe, stato.raggio);
  const cittaPartenza = nomeCitta(stato.dati.aeroporti[partenza()], partenza());
  pagina.titolo.textContent = testoRitorni(dentro.length, stato.raggio);
  pagina.raggioTesto.textContent = `Ritorno entro ${stato.raggio} km da ${cittaPartenza}`;
  pagina.raggio.value = stato.raggio;
  pagina.lista.replaceChildren(...dentro.map((meta) => rigaRitorno(meta, cittaPartenza)));
  mostraVuoto(dentro.length ? "" : `Nessun ritorno entro ${stato.raggio} km: prova ad allargare il raggio.`);
}

function schedaTratta({ da, a, cittaDa, meta }) {
  const voce = crea("li", "tratta");
  const testa = crea("div", "tratta-testa");
  const cittaA = meta ? meta.citta : a;
  testa.append(crea("span", "tratta-nome codice", `${da} > ${a}`));
  if (meta) {
    const tempi = [testoKm(meta.km), testoDurata(meta.durata) || "durata non nota"].join(" · ");
    testa.append(crea("span", "tratta-tempi", tempi));
  }
  voce.append(testa, crea("span", "tratta-citta", `${cittaDa} - ${cittaA}`));
  if (!meta) {
    voce.append(crea("span", "tratta-dettagli", "Questa tratta non è più nei dati."));
    return voce;
  }
  const compagnie = crea("span", "tratta-dettagli", testoCompagnie(meta));
  if (meta.voliSett) compagnie.append(` · ${meta.voliSett} voli/sett`);
  if (testoStato(meta)) compagnie.append(crea("span", "tratta-stagionale", ` · ${testoStato(meta)}`));
  voce.append(compagnie);
  if (meta.giorni) voce.append(pallini(meta.giorni));
  return voce;
}

function disegnaRiepilogo() {
  const riepilogo = riepilogoGiro(stato.dati, stato.tappe);
  const cittaPartenza = nomeCitta(stato.dati.aeroporti[partenza()], partenza());
  const cittaFine = nomeCitta(stato.dati.aeroporti[ultimaTappa()], ultimaTappa());
  const chiuso = stato.fase === "chiuso";
  pagina.riepilogoTitolo.textContent = chiuso ? "Il tuo giro" : "Il giro finora";
  pagina.riepilogoTratte.replaceChildren(...riepilogo.tratte.map(schedaTratta));
  pagina.riepilogoTotale.replaceChildren(
    crea("span", null, `Totale: ${testoTratte(riepilogo.tratte.length)}`),
    crea("span", null, testoTotale(riepilogo)),
  );
  pagina.riepilogoFine.hidden = !chiuso;
  pagina.riepilogoFine.textContent = riepilogo.distanzaFinale === 0
    ? `Torni a ${cittaPartenza}.`
    : `Torni a ${cittaFine}, a ${testoKm(riepilogo.distanzaFinale)} da ${cittaPartenza}.`;
  pagina.cambiaRitorno.hidden = !chiuso;
  pagina.azioniRientro.hidden = stato.fase === "tappe";
  if (chiuso) pagina.titolo.textContent = "Giro chiuso";
}

// Il pannello cambia a seconda della fase: mete, ritorni o riepilogo finale.
function disegnaPannello() {
  const { fase } = stato;
  pagina.chiudiGiro.hidden = fase !== "tappe" || stato.tappe.length < 2;
  pagina.ritorno.hidden = fase !== "ritorno";
  pagina.riepilogo.hidden = fase === "tappe";
  pagina.azioniRientro.hidden = fase === "tappe";
  if (fase === "tappe") {
    disegnaLista();
  } else {
    pagina.filtri.hidden = true;
    pagina.lista.replaceChildren();
    mostraVuoto("");
    if (fase === "ritorno") disegnaListaRitorni();
    disegnaRiepilogo();
  }
  disegnaAvviso();
}

function disegnaFiltroPaese() {
  const scelte = [{ codice: "", nome: "Tutti i paesi" }, ...paesiDelleMete(stato.mete)];
  pagina.filtroPaese.replaceChildren(...scelte.map(({ codice, nome }) => {
    const opzione = crea("option", null, nome);
    opzione.value = codice;
    return opzione;
  }));
  pagina.filtroPaese.value = stato.filtri.paese;
}

function linkEsterno(testo, url) {
  const link = crea("a", null, testo);
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  return link;
}

// Nel pannello solo la data e il rimando: fonti e licenze complete stanno in Informazioni.
function disegnaFonti() {
  const { dati } = stato;
  const collegamento = crea("a", null, "Fonti e licenze");
  collegamento.href = "#informazioni";
  pagina.fonti.replaceChildren(
    `Dati aggiornati al ${testoData(dati.aggiornato)}. Controlla sempre con la compagnia prima di prenotare. `,
    collegamento,
  );
}

function disegnaInformazioni() {
  const { dati } = stato;
  const partenzeContate = Object.keys(stato.partenze).length;
  const rotte = dati.rotte.filter((r) => r.stato !== "nascosta").length;
  pagina.infoStato.textContent = `Versione ${pagina.versione.textContent.replace("v", "") || "non nota"}. `
    + `Dati aggiornati al ${testoData(dati.aggiornato)}: ${partenzeContate} aeroporti e ${rotte} rotte.`;
  const voce = (fonte, spiega) => {
    const riga = crea("li");
    riga.append(linkEsterno(fonte.nome, fonte.url), ` (${fonte.licenza}): ${spiega}`);
    return riga;
  };
  const spiegazioni = {
    "omaxim/airline-route-data": "rotte, voli a settimana e giorni, ricavati dagli orari di flightsfrom.com",
    Wikipedia: "rotte stagionali e annunciate, dalle pagine degli aeroporti",
    OurAirports: "nomi, coordinate e paesi degli aeroporti",
  };
  pagina.infoFonti.replaceChildren(
    ...dati.fonti.map((fonte) => voce(fonte, spiegazioni[fonte.nome] || "dati del sito")),
    ...CREDITI_MAPPA.map((credito) => voce(credito, credito.ruolo)),
  );
}

let changelogCaricato = false;

function caricaChangelog() {
  if (changelogCaricato) return;
  changelogCaricato = true;
  fetch("CHANGELOG.md", { cache: "no-cache" })
    .then((r) => (r.ok ? r.text() : Promise.reject(new Error(String(r.status)))))
    .then((testo) => {
      pagina.infoChangelog.replaceChildren(...leggiChangelog(testo).flatMap(({ titolo, voci }) => {
        const elenco = crea("ul");
        elenco.append(...voci.map((v) => crea("li", null, v)));
        return [crea("h4", null, titolo), elenco];
      }));
    })
    .catch(() => {
      changelogCaricato = false;
      pagina.infoChangelog.replaceChildren(crea("p", "pagina-nota", "Non riesco a leggere le novità: riprova tra poco."));
    });
}

// ---------------------------------------------------------------- azioni

// Ridisegna tutto dopo un cambio del giro: le mete sono sempre quelle dell'ultima tappa.
function aggiornaGiro() {
  stato.mete = meteDa(stato.dati, ultimaTappa());
  stato.selezionata = null;
  stato.filtri.paese = "";
  pagina.campo.value = testoAeroporto(partenza());
  chiudiSuggerimenti();
  aggiornaTogli();
  disegnaCatena();
  disegnaFiltroPaese();
  disegnaPannello();
  aggiornaMisureMappa();
  disegnaRotte(true);
  pagina.lista.parentElement.scrollTop = 0;
}

// Una nuova partenza dal campo di ricerca inizia un giro nuovo.
function iniziaGiro(codice) {
  stato.tappe = [codice];
  stato.fase = "tappe";
  stato.ritornoAggiunto = false;
  mostraMessaggioGiro("");
  aggiornaGiro();
}

function aggiungiTappa(codice) {
  stato.tappe = [...stato.tappe, codice];
  mostraMessaggioGiro("");
  aggiornaGiro();
}

function rimuoviTappa(indice) {
  const esito = togliTappa(stato.dati, stato.tappe, indice);
  if (!esito.tappe.length) {
    ricomincia();
    return;
  }
  stato.tappe = esito.tappe;
  stato.ritornoAggiunto = false;
  if (stato.fase !== "tappe") stato.fase = faseDiChiusura();
  mostraMessaggioGiro(testoTappeTolte(esito));
  aggiornaGiro();
}

// Se l'ultima tappa e' gia' la partenza il giro e' chiuso; con meno di due tappe non c'e' nulla da chiudere.
function faseDiChiusura() {
  if (stato.tappe.length < 2) return "tappe";
  return ultimaTappa() === partenza() ? "chiuso" : "ritorno";
}

function chiudiGiro() {
  stato.fase = faseDiChiusura();
  stato.ritornoAggiunto = false;
  mostraMessaggioGiro("");
  aggiornaGiro();
}

function scegliRitorno(codice) {
  stato.tappe = [...stato.tappe, codice];
  stato.fase = "chiuso";
  stato.ritornoAggiunto = true;
  mostraMessaggioGiro("");
  aggiornaGiro();
}

function cambiaRitorno() {
  stato.tappe = stato.tappe.slice(0, -1);
  stato.ritornoAggiunto = false;
  stato.fase = "ritorno";
  mostraMessaggioGiro("");
  aggiornaGiro();
}

// Si torna ad aggiungere tappe. Se il ritorno era stato scelto, si toglie; le tappe aggiunte col "+" restano.
function annullaRientro() {
  if (stato.ritornoAggiunto) stato.tappe = stato.tappe.slice(0, -1);
  stato.ritornoAggiunto = false;
  stato.fase = "tappe";
  mostraMessaggioGiro("");
  aggiornaGiro();
}

function cambiaRaggio(adatta) {
  stato.raggio = Number(pagina.raggio.value);
  const { dentro } = trovaRitorni(stato.dati, stato.tappe, stato.raggio);
  if (!dentro.some((m) => m.codice === stato.selezionata)) stato.selezionata = null;
  disegnaPannello();
  disegnaRotte(adatta);
}

function aggiornaTogli() {
  pagina.togli.hidden = !partenza() && !pagina.campo.value;
}

function mostraInvito() {
  pagina.titolo.textContent = "Scegli un aeroporto di partenza";
  pagina.filtri.hidden = true;
  pagina.avviso.hidden = true;
  pagina.chiudiGiro.hidden = true;
  pagina.ritorno.hidden = true;
  pagina.riepilogo.hidden = true;
  pagina.azioniRientro.hidden = true;
  pagina.lista.replaceChildren();
  mostraVuoto("Scrivi una città o un codice qui sopra, oppure tocca un punto sulla mappa.");
}

// Torna all'inizio: nessun giro, tutti gli aeroporti sulla mappa, filtri azzerati.
function ricomincia() {
  stato.tappe = [];
  stato.fase = "tappe";
  stato.ritornoAggiunto = false;
  stato.raggio = impostazioni.raggio;
  stato.mete = [];
  stato.selezionata = null;
  stato.filtri = { attive: true, stagionali: impostazioni.stagionali, paese: "" };
  pagina.filtroAttive.setAttribute("aria-pressed", "true");
  pagina.filtroStagionali.setAttribute("aria-pressed", String(impostazioni.stagionali));
  pagina.campo.value = "";
  mostraMessaggioGiro("");
  chiudiSuggerimenti();
  aggiornaTogli();
  disegnaCatena();
  mostraInvito();
  disegnaTuttiGliAeroporti();
  aggiornaMisureMappa();
  mappa.setView(CENTRO_EUROPA, 4);
  pagina.lista.parentElement.scrollTop = 0;
}

function selezionaMeta(codice) {
  stato.selezionata = stato.selezionata === codice ? null : codice;
  disegnaPannello();
  disegnaRotte(false);
}

function aggiornaFiltri() {
  const visibili = filtraMete(stato.mete, stato.filtri);
  if (!visibili.some((m) => m.codice === stato.selezionata)) stato.selezionata = null;
  disegnaLista();
  disegnaRotte(true);
}

function alternaFiltro(bottone, chiave) {
  stato.filtri[chiave] = !stato.filtri[chiave];
  bottone.setAttribute("aria-pressed", String(stato.filtri[chiave]));
  aggiornaFiltri();
}

pagina.filtroAttive.addEventListener("click", () => alternaFiltro(pagina.filtroAttive, "attive"));
pagina.filtroStagionali.addEventListener("click", () => alternaFiltro(pagina.filtroStagionali, "stagionali"));
pagina.filtroPaese.addEventListener("change", () => {
  stato.filtri.paese = pagina.filtroPaese.value;
  aggiornaFiltri();
});
pagina.ricomincia.addEventListener("click", ricomincia);
pagina.chiudiGiro.addEventListener("click", chiudiGiro);
pagina.annullaRientro.addEventListener("click", annullaRientro);
pagina.cambiaRitorno.addEventListener("click", cambiaRitorno);
pagina.raggio.addEventListener("input", () => cambiaRaggio(false));
pagina.raggio.addEventListener("change", () => cambiaRaggio(true));

// ---------------------------------------------------------------- schede

function schedaDaIndirizzo() {
  const scheda = window.location.hash.slice(1);
  return SCHEDE.includes(scheda) ? scheda : "giro";
}

// Le schede usano l'indirizzo (#aiuto): cosi' il tasto Indietro del telefono torna al giro.
function mostraScheda() {
  const attiva = schedaDaIndirizzo();
  for (const scheda of SCHEDE) {
    const aperta = scheda === attiva;
    document.getElementById(`scheda-${scheda}`).setAttribute("aria-selected", String(aperta));
    document.getElementById(`vista-${scheda}`).hidden = !aperta;
  }
  const inGiro = attiva === "giro";
  pagina.ricerca.classList.toggle("nascosta-in-pagina", !inGiro);
  pagina.giro.classList.toggle("nascosta-in-pagina", !inGiro);
  if (inGiro) {
    mappa.invalidateSize({ pan: false });
    if (partenza()) disegnaRotte(true);
  } else {
    document.getElementById(`vista-${attiva}`).scrollTop = 0;
    if (attiva === "informazioni") {
      if (stato.dati) disegnaInformazioni();
      caricaChangelog();
    }
  }
}

function apriScheda(scheda) {
  const indirizzo = scheda === "giro" ? window.location.pathname + window.location.search : `#${scheda}`;
  if (scheda === schedaDaIndirizzo()) return;
  if (scheda === "giro") {
    window.history.pushState(null, "", indirizzo);
    mostraScheda();
  } else {
    window.location.hash = scheda;
  }
}

for (const scheda of SCHEDE) {
  document.getElementById(`scheda-${scheda}`).addEventListener("click", () => apriScheda(scheda));
}
window.addEventListener("hashchange", mostraScheda);
window.addEventListener("popstate", mostraScheda);

function disegnaImpostazioni() {
  pagina.opzioneRaggio.value = impostazioni.raggio;
  pagina.opzioneRaggioTesto.textContent = `Raggio di ritorno predefinito: ${impostazioni.raggio} km`;
  pagina.opzioneStagionali.checked = impostazioni.stagionali;
}

function salvaOpzioni() {
  const riuscito = salvaImpostazioni(memoria, impostazioni);
  pagina.opzioniStato.textContent = riuscito
    ? "Salvato."
    : "Questo browser non permette di salvare: le scelte valgono finché la pagina resta aperta.";
}

pagina.opzioneRaggio.addEventListener("input", () => {
  impostazioni.raggio = Number(pagina.opzioneRaggio.value);
  // Il raggio vale subito, a meno che non si stia gia' scegliendo un ritorno con il proprio cursore.
  if (stato.fase !== "ritorno") stato.raggio = impostazioni.raggio;
  disegnaImpostazioni();
  salvaOpzioni();
});

pagina.opzioneStagionali.addEventListener("change", () => {
  impostazioni.stagionali = pagina.opzioneStagionali.checked;
  stato.filtri.stagionali = impostazioni.stagionali;
  pagina.filtroStagionali.setAttribute("aria-pressed", String(impostazioni.stagionali));
  if (partenza() && stato.fase === "tappe") disegnaPannello();
  salvaOpzioni();
});

// ---------------------------------------------------------------- ricerca

function chiudiSuggerimenti() {
  stato.trovati = [];
  stato.evidenziato = -1;
  pagina.suggerimenti.hidden = true;
  pagina.suggerimenti.replaceChildren();
  pagina.campo.setAttribute("aria-expanded", "false");
  pagina.campo.removeAttribute("aria-activedescendant");
}

function disegnaSuggerimenti() {
  const voci = stato.trovati.map(({ codice, aeroporto }, i) => {
    const voce = crea("li", "suggerimento");
    voce.id = `suggerimento-${i}`;
    voce.setAttribute("role", "option");
    voce.setAttribute("aria-selected", String(i === stato.evidenziato));
    const testo = crea("span", null, nomeCitta(aeroporto, codice));
    testo.append(crea("small", null, `${aeroporto.nome} · ${nomePaese(aeroporto.paese)}`));
    voce.append(crea("span", "codice", codice), testo);
    // pointerdown arriva prima che il campo perda il fuoco e chiuda l'elenco
    voce.addEventListener("pointerdown", (evento) => {
      evento.preventDefault();
      iniziaGiro(codice);
    });
    return voce;
  });
  if (!voci.length) {
    voci.push(crea("li", "suggerimento-vuoto", "Nessun aeroporto trovato nell'area."));
  }
  pagina.suggerimenti.replaceChildren(...voci);
  pagina.suggerimenti.hidden = false;
  pagina.campo.setAttribute("aria-expanded", "true");
  if (stato.evidenziato >= 0) {
    pagina.campo.setAttribute("aria-activedescendant", `suggerimento-${stato.evidenziato}`);
    document.getElementById(`suggerimento-${stato.evidenziato}`).scrollIntoView({ block: "nearest" });
  } else {
    pagina.campo.removeAttribute("aria-activedescendant");
  }
}

pagina.togli.addEventListener("click", (evento) => {
  ricomincia();
  // Da tastiera il pulsante sparisce: il fuoco passa al campo. Col dito no, aprirebbe la tastiera.
  if (evento.detail === 0) pagina.campo.focus();
});

pagina.campo.addEventListener("input", () => {
  aggiornaTogli();
  if (!stato.dati) return;
  if (!pagina.campo.value.trim()) {
    chiudiSuggerimenti();
    return;
  }
  stato.trovati = cercaAeroporti(stato.dati, pagina.campo.value, stato.partenze);
  stato.evidenziato = -1;
  disegnaSuggerimenti();
});

pagina.campo.addEventListener("focus", () => pagina.campo.select());

pagina.campo.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape") {
    chiudiSuggerimenti();
    return;
  }
  if (!stato.trovati.length) return;
  if (evento.key === "ArrowDown" || evento.key === "ArrowUp") {
    evento.preventDefault();
    const passo = evento.key === "ArrowDown" ? 1 : -1;
    stato.evidenziato = (stato.evidenziato + passo + stato.trovati.length) % stato.trovati.length;
    disegnaSuggerimenti();
  } else if (evento.key === "Enter") {
    evento.preventDefault();
    iniziaGiro(stato.trovati[Math.max(stato.evidenziato, 0)].codice);
    pagina.campo.blur();
  }
});

pagina.campo.addEventListener("blur", () => {
  chiudiSuggerimenti();
  if (partenza()) pagina.campo.value = testoAeroporto(partenza());
  aggiornaTogli();
});

// ---------------------------------------------------------------- pannello trascinabile

const FERMATE = [0, 0.45, 0.85]; // 0 = solo il titolo
let fermata = 1;

function schermoLargo() {
  return window.matchMedia("(min-width: 900px)").matches;
}

function altezzaFermata(indice) {
  const contenitore = pagina.pannello.parentElement.clientHeight;
  return Math.max(pagina.maniglia.offsetHeight, contenitore * FERMATE[indice]);
}

function vaiAFermata(indice) {
  fermata = indice;
  pagina.pannello.classList.add("animato");
  pagina.pannello.style.height = `${altezzaFermata(indice)}px`;
}

let trascinamento = null;

pagina.maniglia.addEventListener("pointerdown", (evento) => {
  if (schermoLargo()) return;
  pagina.maniglia.setPointerCapture(evento.pointerId);
  pagina.pannello.classList.remove("animato");
  trascinamento = { y: evento.clientY, altezza: pagina.pannello.offsetHeight, mosso: false };
});

pagina.maniglia.addEventListener("pointermove", (evento) => {
  if (!trascinamento) return;
  const spostamento = trascinamento.y - evento.clientY;
  if (Math.abs(spostamento) > 4) trascinamento.mosso = true;
  if (!trascinamento.mosso) return;
  const massimo = pagina.pannello.parentElement.clientHeight;
  const altezza = Math.min(massimo, Math.max(pagina.maniglia.offsetHeight, trascinamento.altezza + spostamento));
  pagina.pannello.style.height = `${altezza}px`;
});

function fineTrascinamento() {
  if (!trascinamento) return;
  const { mosso } = trascinamento;
  trascinamento = null;
  if (!mosso) {
    vaiAFermata((fermata + 1) % FERMATE.length);
    return;
  }
  const altezza = pagina.pannello.offsetHeight;
  let vicina = 0;
  FERMATE.forEach((_, i) => {
    if (Math.abs(altezzaFermata(i) - altezza) < Math.abs(altezzaFermata(vicina) - altezza)) vicina = i;
  });
  vaiAFermata(vicina);
}

pagina.maniglia.addEventListener("pointerup", fineTrascinamento);
pagina.maniglia.addEventListener("pointercancel", fineTrascinamento);
pagina.maniglia.addEventListener("click", (evento) => {
  // Da tastiera non c'e' pointerdown: Invio e spazio passano alla fermata dopo.
  if (evento.detail === 0 && !schermoLargo()) vaiAFermata((fermata + 1) % FERMATE.length);
});

let eraLargo = schermoLargo();

window.addEventListener("resize", () => {
  if (!schermoLargo()) pagina.pannello.style.height = `${altezzaFermata(fermata)}px`;
  mappa.invalidateSize();
  // Passando da telefono a colonna cambia lo spazio per la mappa: si rifa' l'inquadratura.
  if (schermoLargo() !== eraLargo && partenza()) disegnaRotte(true);
  eraLargo = schermoLargo();
});

// ---------------------------------------------------------------- avvio

function mostraErrore(testo) {
  pagina.titolo.textContent = "Dati non disponibili";
  mostraVuoto(testo);
}

async function avvia() {
  fetch("VERSIONE", { cache: "no-cache" })
    .then((r) => (r.ok ? r.text() : ""))
    .then((testo) => {
      pagina.versione.textContent = testo.trim() ? `v${testo.trim()}` : "";
      if (stato.dati) disegnaInformazioni();
    })
    .catch(() => {});

  disegnaImpostazioni();
  pagina.filtroStagionali.setAttribute("aria-pressed", String(impostazioni.stagionali));
  mostraScheda();

  try {
    const risposta = await fetch(FILE_DATI, { cache: "no-cache" });
    if (!risposta.ok) throw new Error(`Risposta ${risposta.status}`);
    stato.dati = controllaDati(await risposta.json());
  } catch (errore) {
    const locale = window.location.protocol === "file:";
    mostraErrore(locale
      ? "Questa pagina va aperta con Apri_Sito.bat, non con un doppio clic sul file."
      : `Non riesco a leggere i dati: ${errore.message}. Riprova tra poco.`);
    return;
  }

  stato.partenze = contaPartenze(stato.dati);
  mostraInvito();
  disegnaFonti();
  disegnaInformazioni();
  disegnaTuttiGliAeroporti();
}

avvia();
