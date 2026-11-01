// Logica del sito senza mappa e senza pagina: si puo' provare con i test automatici.

export const TIPO_DATI = "dove_volo_dati";
export const VERSIONE_FORMATO = 1;

// I dati dicono "Turin" e "Milan": in italiano si mostra e si cerca "Torino" e "Milano".
const NOMI_ITALIANI = {
  "Amsterdam": "Amsterdam", "Athens": "Atene", "Barcelona": "Barcellona",
  "Basel, Switzerland/Mulhouse": "Basilea", "Belgrade": "Belgrado", "Brussels": "Bruxelles",
  "Bucharest": "Bucarest", "Chania": "La Canea", "Cologne": "Colonia", "Copenhagen": "Copenaghen",
  "Dublin": "Dublino", "Dusseldorf": "Düsseldorf", "Edinburgh": "Edimburgo", "Florence": "Firenze",
  "Frankfurt": "Francoforte", "Gdansk": "Danzica", "Geneva": "Ginevra", "Genoa": "Genova",
  "Gothenburg": "Göteborg", "Hamburg": "Amburgo", "Hanover": "Hannover", "Izmir": "Smirne",
  "Kerkyra": "Corfù", "Krakow": "Cracovia", "Lamezia-Terme": "Lamezia Terme", "Lisbon": "Lisbona",
  "Ljubljana": "Lubiana", "London": "Londra", "Luxembourg": "Lussemburgo", "Lyon": "Lione",
  "Marseille": "Marsiglia", "Menorca": "Minorca", "Milan": "Milano", "Moscow": "Mosca",
  "Munich": "Monaco di Baviera", "Naples": "Napoli", "Nice": "Nizza", "Nuremberg": "Norimberga",
  "Palma de Mallorca": "Palma di Maiorca", "Paris": "Parigi", "Prague": "Praga", "Rhodes": "Rodi",
  "Rome": "Roma", "Saint Petersburg": "San Pietroburgo", "Salzburg": "Salisburgo",
  "Santiago De Compostela": "Santiago de Compostela", "Sevilla": "Siviglia", "Split": "Spalato",
  "Stockholm": "Stoccolma", "Strasbourg": "Strasburgo", "Stuttgart": "Stoccarda",
  "Thessaloniki": "Salonicco", "Toulouse": "Tolosa", "Turin": "Torino", "Venice": "Venezia",
  "Warsaw": "Varsavia", "Wroclaw": "Breslavia", "Yerevan": "Erevan", "Zagreb": "Zagabria",
  "Zakinthos": "Zante", "Zurich": "Zurigo",
};

// Aeroporti che i dati mettono sotto una citta' grande, ma che tutti chiamano col loro nome.
// Cercando la citta' grande si trovano lo stesso.
const NOMI_PROPRI = { BGY: "Bergamo", TSF: "Treviso", CRL: "Charleroi", BVA: "Beauvais", NRN: "Weeze" };

const GIORNI_ESTESI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"];

export function normalizza(testo) {
  return (testo || "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

export function nomeCitta(aeroporto, codice) {
  return NOMI_PROPRI[codice] || NOMI_ITALIANI[aeroporto.citta] || aeroporto.citta || aeroporto.nome;
}

export function controllaDati(dati) {
  if (!dati || dati.tipo !== TIPO_DATI) throw new Error("Il file dei dati non è di Dove_Volo.");
  if (dati.versione_formato !== VERSIONE_FORMATO) {
    throw new Error(`Formato dei dati non gestito: ${dati.versione_formato}.`);
  }
  return dati;
}

function visibile(rotta) {
  return rotta.stato !== "nascosta";
}

export function contaPartenze(dati) {
  const conteggi = {};
  for (const rotta of dati.rotte) {
    if (visibile(rotta)) conteggi[rotta.da] = (conteggi[rotta.da] || 0) + 1;
  }
  return conteggi;
}

function punteggioRicerca(richiesta, codice, aeroporto) {
  if (normalizza(codice) === richiesta) return 0;
  const citta = [nomeCitta(aeroporto, codice), NOMI_ITALIANI[aeroporto.citta], aeroporto.citta].map(normalizza);
  if (citta.some((c) => c.startsWith(richiesta))) return 1;
  if (normalizza(codice).startsWith(richiesta)) return 2;
  if (citta.some((c) => c.includes(` ${richiesta}`))) return 3;
  const nome = normalizza(aeroporto.nome);
  if (nome.startsWith(richiesta) || nome.includes(` ${richiesta}`)) return 4;
  if (citta.some((c) => c.includes(richiesta)) || nome.includes(richiesta)) return 5;
  return null;
}

// Trova gli aeroporti per citta', in italiano o in inglese, per codice o per nome.
export function cercaAeroporti(dati, testo, partenze, limite = 8) {
  const richiesta = normalizza(testo);
  if (!richiesta) return [];
  const trovati = [];
  for (const [codice, aeroporto] of Object.entries(dati.aeroporti)) {
    const punteggio = punteggioRicerca(richiesta, codice, aeroporto);
    if (punteggio !== null) {
      trovati.push({ codice, aeroporto, punteggio, partenze: partenze[codice] || 0 });
    }
  }
  trovati.sort((a, b) => a.punteggio - b.punteggio || b.partenze - a.partenze || a.codice.localeCompare(b.codice));
  return trovati.slice(0, limite);
}

// Sette valori da lunedi' a domenica, oppure null se i giorni non si conoscono.
function unisciGiorni(compagnie) {
  const conGiorni = compagnie.filter((c) => c.giorni);
  if (!conGiorni.length) return null;
  return Array.from({ length: 7 }, (_, i) => conGiorni.some((c) => c.giorni[i] === "1"));
}

// Le frequenze possono mancare: vuote, mai zero.
function sommaVoli(compagnie) {
  const conVoli = compagnie.filter((c) => c.voli_sett);
  return conVoli.length ? conVoli.reduce((totale, c) => totale + c.voli_sett, 0) : null;
}

function perVoliDecrescenti(a, b) {
  return (b.voli_sett || 0) - (a.voli_sett || 0) || a.nome.localeCompare(b.nome, "it");
}

export function meteDa(dati, partenza) {
  const mete = [];
  for (const rotta of dati.rotte) {
    if (rotta.da !== partenza || !visibile(rotta)) continue;
    const aeroporto = dati.aeroporti[rotta.a];
    const compagnie = rotta.compagnie
      .map((c) => ({ ...c, nome: dati.compagnie[c.iata] || c.iata }))
      .sort(perVoliDecrescenti);
    mete.push({
      codice: rotta.a,
      aeroporto,
      citta: nomeCitta(aeroporto, rotta.a),
      stato: rotta.stato,
      km: rotta.km,
      durata: rotta.durata_min,
      compagnie,
      voliSett: sommaVoli(compagnie),
      giorni: unisciGiorni(compagnie),
      vistaUltima: rotta.vista_ultima,
    });
  }
  return mete.sort((a, b) =>
    (a.stato === "attiva" ? 0 : 1) - (b.stato === "attiva" ? 0 : 1)
    || (b.voliSett || 0) - (a.voliSett || 0)
    || a.citta.localeCompare(b.citta, "it"));
}

export function rottaVisibile(dati, da, a) {
  return dati.rotte.some((r) => r.da === da && r.a === a && visibile(r));
}

// Toglie una tappa dal giro. Il giro deve restare fatto solo di voli diretti: se dopo il taglio
// due tappe vicine non hanno un volo diretto, da li' in poi le tappe vengono tolte e segnalate.
export function togliTappa(dati, tappe, indice) {
  const rimaste = tappe.filter((_, i) => i !== indice);
  const giro = [];
  for (let i = 0; i < rimaste.length; i++) {
    const precedente = giro[giro.length - 1];
    if (rimaste[i] === precedente) continue; // A > B > A senza B: resta una A sola
    if (precedente && !rottaVisibile(dati, precedente, rimaste[i])) {
      return { tappe: giro, tolte: rimaste.slice(i), da: precedente, a: rimaste[i] };
    }
    giro.push(rimaste[i]);
  }
  return { tappe: giro, tolte: [], da: null, a: null };
}

export function testoTappeTolte({ tolte, da, a }) {
  if (!tolte.length) return "";
  return `Ho tolto anche ${tolte.join(", ")}: da ${da} a ${a} non c'è un volo diretto.`;
}

export function filtraMete(mete, filtri) {
  return mete.filter((meta) => {
    if (filtri.paese && meta.aeroporto.paese !== filtri.paese) return false;
    return meta.stato === "attiva" ? filtri.attive : filtri.stagionali;
  });
}

export function nomePaese(codice) {
  try {
    return new Intl.DisplayNames(["it"], { type: "region" }).of(codice) || codice;
  } catch {
    return codice;
  }
}

export function paesiDelleMete(mete) {
  const codici = new Set(mete.map((m) => m.aeroporto.paese));
  return [...codici]
    .map((codice) => ({ codice, nome: nomePaese(codice) }))
    .sort((a, b) => a.nome.localeCompare(b.nome, "it"));
}

export function testoMete(numero) {
  return numero === 1 ? "1 meta diretta" : `${numero} mete dirette`;
}

export function testoDurata(minuti) {
  if (!minuti) return null;
  const ore = Math.floor(minuti / 60);
  const resto = minuti % 60;
  if (!ore) return `${resto} min`;
  return resto ? `${ore} h ${resto} min` : `${ore} h`;
}

export function testoKm(km) {
  return `${km.toLocaleString("it-IT")} km`;
}

export function testoGiorni(giorni) {
  const attivi = GIORNI_ESTESI.filter((_, i) => giorni[i]);
  return attivi.length === 7 ? "Vola tutti i giorni" : `Vola: ${attivi.join(", ")}`;
}

export function testoData(iso) {
  const [anno, mese, giorno] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat("it-IT", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
    .format(new Date(Date.UTC(anno, mese - 1, giorno)));
}

// La linea curva tra due punti: una curva semplice, solo per leggere meglio la mappa.
export function puntiArco(da, a, segmenti = 24) {
  const dLat = a.lat - da.lat;
  const dLon = a.lon - da.lon;
  const controllo = {
    lat: (da.lat + a.lat) / 2 + dLon * 0.15,
    lon: (da.lon + a.lon) / 2 - dLat * 0.15,
  };
  const punti = [];
  for (let i = 0; i <= segmenti; i++) {
    const t = i / segmenti;
    const u = 1 - t;
    punti.push([
      u * u * da.lat + 2 * u * t * controllo.lat + t * t * a.lat,
      u * u * da.lon + 2 * u * t * controllo.lon + t * t * a.lon,
    ]);
  }
  return punti;
}
