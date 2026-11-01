// La pagina: legge i dati, disegna mappa, giro e lista, risponde ai tocchi.
import {
  cercaAeroporti, contaPartenze, controllaDati, filtraMete, meteDa, nomeCitta, nomePaese, paesiDelleMete,
  puntiArco, testoData, testoDurata, testoGiorni, testoKm, testoMete, testoTappeTolte, togliTappa,
} from "./logica.js";

const L = window.L;
const FILE_DATI = "dati/dove_volo.json";
const FILE_MAPPA = "sito/europa.json";
const CENTRO_EUROPA = [50, 14];
// Non ci si perde nel vuoto. Deve restare piu' grande di cio' che mostra un telefono allo zoom minimo:
// se e' piu' piccolo, Leaflet ricentra la mappa sul mezzo di questi limiti e sposta l'inquadratura.
const LIMITI_MAPPA = [[-10, -80], [85, 120]];

const stile = getComputedStyle(document.documentElement);
const colore = (nome) => stile.getPropertyValue(nome).trim();
const COLORI = {
  attiva: colore("--attiva"),
  stagionale: colore("--stagionale"),
  punto: colore("--secondario"),
  giro: colore("--testo"),
  sfondo: colore("--sfondo"),
  terra: colore("--terra"),
  confine: colore("--bordo"),
};

const pagina = {
  versione: document.getElementById("versione"),
  campo: document.getElementById("partenza"),
  togli: document.getElementById("togli-partenza"),
  suggerimenti: document.getElementById("suggerimenti"),
  giro: document.getElementById("giro"),
  catena: document.getElementById("catena"),
  ricomincia: document.getElementById("ricomincia"),
  messaggioGiro: document.getElementById("messaggio-giro"),
  legendaGiro: document.getElementById("legenda-giro"),
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
};

const stato = {
  dati: null,
  partenze: {},
  tappe: [], // il giro: la prima e' la partenza, le mete si cercano dall'ultima
  mete: [],
  selezionata: null,
  filtri: { attive: true, stagionali: true, paese: "" },
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
  minZoom: 3,
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
  const visibili = filtraMete(stato.mete, stato.filtri);

  disegnaMete(origine, visibili);
  disegnaGiro();

  const scelta = visibili.find((m) => m.codice === stato.selezionata);
  if (scelta) etichettaFissa(scelta.aeroporto, `${scelta.codice} · ${scelta.citta}`).addTo(livelloPunti);

  if (adatta) {
    const punti = [
      ...stato.tappe.map((codice) => stato.dati.aeroporti[codice]),
      ...visibili.map((m) => m.aeroporto),
    ].map((a) => [a.lat, a.lon]);
    if (new Set(punti.map(String)).size > 1) {
      mappa.fitBounds(L.latLngBounds(punti), marginiMappa());
    } else {
      mappa.setView(punti[0], 6);
    }
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

function disegnaCatena() {
  pagina.giro.hidden = !stato.tappe.length;
  pagina.legendaGiro.hidden = stato.tappe.length < 2;
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
  const prossima = crea("li");
  prossima.append(crea("span", "tappa-prossima", `scegli tappa ${stato.tappe.length + 1}`));
  pagina.catena.replaceChildren(...voci, prossima);
  pagina.catena.scrollLeft = pagina.catena.scrollWidth;
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

  const dettagli = [testoKm(meta.km), testoDurata(meta.durata)].filter(Boolean);
  if (meta.stato !== "attiva") dettagli.push(`vista il ${testoData(meta.vistaUltima)}`);
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

function mostraVuoto(testo) {
  pagina.vuoto.textContent = testo;
  pagina.vuoto.hidden = !testo;
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

  const origine = stato.dati.aeroporti[ultimaTappa()];
  const parziale = !origine.settimana_completa && stato.mete.some((m) => m.voliSett);
  pagina.avviso.hidden = !parziale;
  pagina.avviso.textContent = parziale
    ? "Per questo aeroporto manca qualche giorno nei dati: voli e giorni possono essere più di così."
    : "";
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

function disegnaFonti() {
  const { dati } = stato;
  pagina.fonti.replaceChildren(`Dati aggiornati al ${testoData(dati.aggiornato)}. Fonti: `);
  dati.fonti.forEach((fonte, i) => {
    const link = crea("a", null, fonte.nome);
    link.href = fonte.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    pagina.fonti.append(i ? "; " : "", link, ` (${fonte.licenza})`);
  });
  pagina.fonti.append(
    ". Mappa: Natural Earth (Pubblico dominio) con Leaflet.",
    " Le rotte possono non essere aggiornate: controlla sempre con la compagnia prima di prenotare.",
  );
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
  disegnaLista();
  aggiornaMisureMappa();
  disegnaRotte(true);
  pagina.lista.parentElement.scrollTop = 0;
}

// Una nuova partenza dal campo di ricerca inizia un giro nuovo.
function iniziaGiro(codice) {
  stato.tappe = [codice];
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
  mostraMessaggioGiro(testoTappeTolte(esito));
  aggiornaGiro();
}

function aggiornaTogli() {
  pagina.togli.hidden = !partenza() && !pagina.campo.value;
}

function mostraInvito() {
  pagina.titolo.textContent = "Scegli un aeroporto di partenza";
  pagina.filtri.hidden = true;
  pagina.avviso.hidden = true;
  pagina.lista.replaceChildren();
  mostraVuoto("Scrivi una città o un codice qui sopra, oppure tocca un punto sulla mappa.");
}

// Torna all'inizio: nessun giro, tutti gli aeroporti sulla mappa, filtri azzerati.
function ricomincia() {
  stato.tappe = [];
  stato.mete = [];
  stato.selezionata = null;
  stato.filtri = { attive: true, stagionali: true, paese: "" };
  pagina.filtroAttive.setAttribute("aria-pressed", "true");
  pagina.filtroStagionali.setAttribute("aria-pressed", "true");
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
  disegnaLista();
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
    .then((testo) => { pagina.versione.textContent = testo.trim() ? `v${testo.trim()}` : ""; })
    .catch(() => {});

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
  disegnaTuttiGliAeroporti();
}

avvia();
