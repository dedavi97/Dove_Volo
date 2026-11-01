// Test della logica del sito. Si eseguono con: node --test "tests/*.test.mjs"
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  cercaAeroporti, contaPartenze, controllaDati, distanzaKm, filtraMete, IMPOSTAZIONI_INIZIALI, leggiChangelog,
  leggiImpostazioni, meteDa, nomeCitta, nomePaese, normalizza, paesiDelleMete, puntiArco, riepilogoGiro,
  rottaVisibile, salvaImpostazioni, testoData, testoDurata, testoGiorni, testoKm, testoMete, testoRitorni,
  testoStato, testoTappeTolte, testoTotale, testoTratte, testoVicino, togliTappa, trovaRitorni,
} from "../sito/logica.js";

function aeroporto(citta, paese, nome = `${citta} Airport`, lat = 45, lon = 9) {
  return { nome, citta, paese, lat, lon, settimana_dal: "2026-11-02", settimana_completa: true };
}

function rotta(da, a, stato, compagnie, extra = {}) {
  return { da, a, stato, stagionale_wiki: false, km: 1000, durata_min: 90, compagnie, periodo: null,
           vista_ultima: "2026-11-01", fonte: "omaxim", ...extra };
}

const DATI = {
  tipo: "dove_volo_dati",
  versione_formato: 1,
  aggiornato: "2026-11-01",
  fonti: [],
  compagnie: { FR: "Ryanair", W4: null, IB: "Iberia" },
  aeroporti: {
    TRN: aeroporto("Turin", "IT", "Turin Airport"),
    MXP: aeroporto("Milan", "IT", "Malpensa International Airport"),
    BGY: aeroporto("Milan", "IT", "Il Caravaggio Bergamo Airport"),
    OTP: aeroporto("Bucharest", "RO", "Henri Coanda Airport"),
    MAD: aeroporto("Madrid", "ES", "Barajas Airport"),
    KEF: aeroporto("Reykjavik", "IS", "Keflavík Airport"),
    ZZZ: aeroporto("", "IT", "Senza Citta Airport"),
  },
  rotte: [
    rotta("TRN", "OTP", "attiva", [{ iata: "W4", voli_sett: 4, giorni: "1010101" }]),
    rotta("TRN", "MAD", "attiva", [
      { iata: "IB", voli_sett: 7, giorni: "1111111" },
      { iata: "FR", voli_sett: 10, giorni: "1111100" },
    ]),
    rotta("TRN", "KEF", "stagionale", [{ iata: "FR", voli_sett: null, giorni: null }],
      { vista_ultima: "2026-10-04" }),
    rotta("TRN", "MXP", "nascosta", [{ iata: "FR", voli_sett: null, giorni: null }]),
    rotta("MXP", "OTP", "attiva", [{ iata: "FR", voli_sett: 2, giorni: "1000100" }]),
    rotta("BGY", "OTP", "attiva", [{ iata: "FR", voli_sett: 3, giorni: "1000101" }]),
    rotta("BGY", "MAD", "attiva", [{ iata: "FR", voli_sett: 3, giorni: "1000101" }]),
  ],
};
const PARTENZE = contaPartenze(DATI);

function codici(lista) {
  return lista.map((voce) => voce.codice);
}

test("le rotte nascoste non contano e non si vedono", () => {
  assert.equal(PARTENZE.TRN, 3);
  assert.deepEqual(codici(meteDa(DATI, "TRN")).sort(), ["KEF", "MAD", "OTP"]);
});

test("ricerca: nome italiano, nome inglese, codice, accenti", () => {
  assert.equal(cercaAeroporti(DATI, "Torino", PARTENZE)[0].codice, "TRN");
  assert.equal(cercaAeroporti(DATI, "turin", PARTENZE)[0].codice, "TRN");
  assert.equal(cercaAeroporti(DATI, "trn", PARTENZE)[0].codice, "TRN");
  assert.equal(cercaAeroporti(DATI, "keflavik", PARTENZE)[0].codice, "KEF");
  assert.equal(cercaAeroporti(DATI, "  BUCAREST ", PARTENZE)[0].codice, "OTP");
});

test("ricerca: stessa citta', prima l'aeroporto con piu' partenze", () => {
  assert.deepEqual(codici(cercaAeroporti(DATI, "Milano", PARTENZE)), ["BGY", "MXP"]);
});

test("ricerca: Bergamo si trova dal nome dell'aeroporto", () => {
  assert.equal(cercaAeroporti(DATI, "bergamo", PARTENZE)[0].codice, "BGY");
});

test("ricerca: il codice esatto batte una citta' simile", () => {
  const dati = { ...DATI, aeroporti: { MAD: aeroporto("Madrid", "ES"), XXX: aeroporto("Mad", "ES") } };
  assert.equal(cercaAeroporti(dati, "mad", {})[0].codice, "MAD");
});

test("ricerca: il nome italiano trova anche il nome inglese dell'aeroporto", () => {
  const dati = { ...DATI, aeroporti: { TRN: aeroporto("Caselle Torinese (TO)", "IT", "Turin Airport"), ATH: aeroporto("Spata", "GR", "Athens International Airport") } };
  assert.equal(cercaAeroporti(dati, "Torino", {})[0].codice, "TRN");
  assert.equal(cercaAeroporti(dati, "Atene", {})[0].codice, "ATH");
  assert.deepEqual(cercaAeroporti(dati, "Parigi", {}), []);
});

test("ricerca: vuota o senza risultati", () => {
  assert.deepEqual(cercaAeroporti(DATI, "", PARTENZE), []);
  assert.deepEqual(cercaAeroporti(DATI, "   ", PARTENZE), []);
  assert.deepEqual(cercaAeroporti(DATI, "qqqq", PARTENZE), []);
  assert.equal(cercaAeroporti(DATI, "a", PARTENZE, 2).length, 2);
});

test("mete: somma i voli e unisce i giorni delle compagnie", () => {
  const meta = meteDa(DATI, "TRN").find((m) => m.codice === "MAD");
  assert.equal(meta.voliSett, 17);
  assert.deepEqual(meta.giorni, [true, true, true, true, true, true, true]);
  assert.deepEqual(meta.compagnie.map((c) => c.nome), ["Ryanair", "Iberia"]);
});

test("mete: compagnia senza nome mostra il codice", () => {
  const meta = meteDa(DATI, "TRN").find((m) => m.codice === "OTP");
  assert.equal(meta.compagnie[0].nome, "W4");
});

test("mete: senza frequenze restano vuote, mai zero", () => {
  const meta = meteDa(DATI, "TRN").find((m) => m.codice === "KEF");
  assert.equal(meta.voliSett, null);
  assert.equal(meta.giorni, null);
  assert.equal(meta.compagnie[0].nome, "Ryanair");
});

test("mete: prima le attive per voli, poi le stagionali", () => {
  assert.deepEqual(codici(meteDa(DATI, "TRN")), ["MAD", "OTP", "KEF"]);
});

test("mete: aeroporto senza partenze", () => {
  assert.deepEqual(meteDa(DATI, "ZZZ"), []);
});

test("mete: una compagnia sconosciuta o senza compagnie non rompe nulla", () => {
  const dati = { ...DATI, rotte: [rotta("TRN", "OTP", "attiva", [])] };
  const [meta] = meteDa(dati, "TRN");
  assert.deepEqual(meta.compagnie, []);
  assert.equal(meta.voliSett, null);
  assert.equal(meta.giorni, null);
});

test("filtri: attive, stagionali, paese, combinati", () => {
  const mete = meteDa(DATI, "TRN");
  const tutti = { attive: true, stagionali: true, paese: "" };
  assert.equal(filtraMete(mete, tutti).length, 3);
  assert.deepEqual(codici(filtraMete(mete, { ...tutti, attive: false })), ["KEF"]);
  assert.deepEqual(codici(filtraMete(mete, { ...tutti, stagionali: false })), ["MAD", "OTP"]);
  assert.deepEqual(codici(filtraMete(mete, { ...tutti, paese: "RO" })), ["OTP"]);
  assert.deepEqual(filtraMete(mete, { attive: false, stagionali: false, paese: "" }), []);
  assert.deepEqual(filtraMete(mete, { ...tutti, attive: false, paese: "RO" }), []);
});

test("paesi: in italiano e senza doppioni", () => {
  const paesi = paesiDelleMete(meteDa(DATI, "TRN"));
  assert.deepEqual(paesi.map((p) => p.codice), ["IS", "RO", "ES"]);
  assert.equal(nomePaese("IT"), "Italia");
  assert.equal(typeof nomePaese("XK"), "string");
});

test("nomi: italiano se c'e', altrimenti come nei dati", () => {
  assert.equal(nomeCitta(aeroporto("Turin", "IT")), "Torino");
  assert.equal(nomeCitta(aeroporto("Kutaisi", "GE")), "Kutaisi");
  assert.equal(nomeCitta(aeroporto("", "IT", "Solo Nome")), "Solo Nome");
  assert.equal(normalizza("Çorlu Düsseldorf"), "corlu dusseldorf");
});

test("testi", () => {
  assert.equal(testoMete(1), "1 meta diretta");
  assert.equal(testoMete(0), "0 mete dirette");
  assert.equal(testoDurata(45), "45 min");
  assert.equal(testoDurata(120), "2 h");
  assert.equal(testoDurata(135), "2 h 15 min");
  assert.equal(testoDurata(null), null);
  assert.equal(testoKm(1452), "1452 km");
  assert.equal(testoGiorni(Array(7).fill(true)), "Vola tutti i giorni");
  assert.equal(testoGiorni([true, false, true, false, false, false, false]), "Vola: lunedì, mercoledì");
  assert.match(testoData("2026-11-01"), /1 nov 2026/);
});

test("arco: parte e arriva nei punti giusti e curva", () => {
  const da = { lat: 45, lon: 7 };
  const a = { lat: 44, lon: 26 };
  const punti = puntiArco(da, a, 10);
  assert.equal(punti.length, 11);
  assert.deepEqual(punti[0], [45, 7]);
  assert.deepEqual(punti[10], [44, 26]);
  assert.notEqual(punti[5][0], (45 + 44) / 2);
});

const VOLO = [{ iata: "FR", voli_sett: 1, giorni: "1000000" }];
const GIRO = {
  ...DATI,
  rotte: [
    rotta("TRN", "OTP", "attiva", VOLO), rotta("OTP", "TRN", "attiva", VOLO),
    rotta("OTP", "MAD", "attiva", VOLO), rotta("MAD", "KEF", "stagionale", VOLO),
    rotta("TRN", "MAD", "attiva", VOLO), rotta("TRN", "KEF", "nascosta", VOLO),
  ],
};

test("rotta visibile: attive e stagionali si', nascoste e inesistenti no", () => {
  assert.ok(rottaVisibile(GIRO, "TRN", "OTP"));
  assert.ok(rottaVisibile(GIRO, "MAD", "KEF"));
  assert.ok(!rottaVisibile(GIRO, "TRN", "KEF"));
  assert.ok(!rottaVisibile(GIRO, "KEF", "TRN"));
});

test("togliere l'ultima tappa", () => {
  const esito = togliTappa(GIRO, ["TRN", "OTP", "MAD"], 2);
  assert.deepEqual(esito.tappe, ["TRN", "OTP"]);
  assert.deepEqual(esito.tolte, []);
  assert.equal(testoTappeTolte(esito), "");
});

test("togliere una tappa in mezzo, se il volo diretto c'e'", () => {
  const esito = togliTappa(GIRO, ["TRN", "OTP", "MAD"], 1);
  assert.deepEqual(esito.tappe, ["TRN", "MAD"]);
  assert.deepEqual(esito.tolte, []);
});

test("togliere una tappa in mezzo, senza volo diretto: il giro si taglia e lo dice", () => {
  const esito = togliTappa(GIRO, ["TRN", "OTP", "MAD", "KEF"], 2);
  assert.deepEqual(esito.tappe, ["TRN", "OTP"]);
  assert.deepEqual(esito.tolte, ["KEF"]);
  assert.equal(testoTappeTolte(esito), "Ho tolto anche KEF: da OTP a KEF non c'è un volo diretto.");
});

test("una rotta nascosta non tiene insieme il giro", () => {
  const esito = togliTappa(GIRO, ["TRN", "MAD", "KEF"], 1);
  assert.deepEqual(esito.tappe, ["TRN"]);
  assert.deepEqual(esito.tolte, ["KEF"]);
});

test("togliere la partenza: la tappa dopo diventa la partenza", () => {
  const esito = togliTappa(GIRO, ["TRN", "OTP", "MAD"], 0);
  assert.deepEqual(esito.tappe, ["OTP", "MAD"]);
  assert.deepEqual(esito.tolte, []);
});

test("A > B > A senza B: resta una A sola, senza allarmi", () => {
  const esito = togliTappa(GIRO, ["TRN", "OTP", "TRN"], 1);
  assert.deepEqual(esito.tappe, ["TRN"]);
  assert.deepEqual(esito.tolte, []);
});

test("togliere l'unica tappa lascia il giro vuoto", () => {
  assert.deepEqual(togliTappa(GIRO, ["TRN"], 0).tappe, []);
});

test("il giro originale non viene toccato", () => {
  const tappe = ["TRN", "OTP", "MAD"];
  togliTappa(GIRO, tappe, 1);
  assert.deepEqual(tappe, ["TRN", "OTP", "MAD"]);
});

const CHIUSURA = {
  ...DATI,
  aeroporti: {
    TRN: aeroporto("Turin", "IT", "Turin Airport", 45.2, 7.65),
    MXP: aeroporto("Milan", "IT", "Malpensa", 45.63, 8.72),
    BGY: aeroporto("Milan", "IT", "Il Caravaggio", 45.67, 9.7),
    GOA: aeroporto("Genoa", "IT", "Genova", 44.41, 8.84),
    OTP: aeroporto("Bucharest", "RO", "Otopeni", 44.57, 26.08),
    MAD: aeroporto("Madrid", "ES", "Barajas", 40.47, -3.56),
  },
  rotte: [
    rotta("TRN", "OTP", "attiva", [{ iata: "W4", voli_sett: 4, giorni: "1010101" }], { km: 1452, durata_min: 145 }),
    rotta("OTP", "TRN", "attiva", [{ iata: "W4", voli_sett: 4, giorni: "1010101" }], { km: 1452, durata_min: 145 }),
    rotta("OTP", "BGY", "attiva", [{ iata: "FR", voli_sett: 28, giorni: "1111111" }], { km: 1290, durata_min: 130 }),
    rotta("OTP", "MXP", "stagionale", [{ iata: "FR", voli_sett: null, giorni: null }], { km: 1370, durata_min: 140 }),
    rotta("OTP", "MAD", "attiva", [{ iata: "FR", voli_sett: 7, giorni: "1111111" }], { km: 2470, durata_min: 230 }),
    rotta("OTP", "GOA", "nascosta", [{ iata: "FR", voli_sett: null, giorni: null }], { km: 1400, durata_min: 140 }),
  ],
};

test("distanza: Torino-Bucarest circa 1450 km, da se' a se' zero", () => {
  const { TRN, OTP } = CHIUSURA.aeroporti;
  const km = distanzaKm(TRN, OTP);
  assert.ok(km > 1430 && km < 1470, String(km));
  assert.equal(distanzaKm(TRN, TRN), 0);
  assert.equal(distanzaKm(TRN, OTP), distanzaKm(OTP, TRN));
});

test("ritorni: dentro e fuori dal raggio, dal piu' vicino alla partenza", () => {
  const { dentro, fuori } = trovaRitorni(CHIUSURA, ["TRN", "OTP"], 150);
  assert.deepEqual(dentro.map((m) => m.codice), ["TRN", "MXP"]);
  assert.deepEqual(fuori.map((m) => m.codice), ["BGY", "MAD"]);
  assert.equal(dentro[0].distanza, 0);
  assert.ok(dentro[1].distanza > 50 && dentro[1].distanza < 150);
});

test("ritorni: raggio zero vale solo la partenza, raggio grande prende di piu'", () => {
  assert.deepEqual(trovaRitorni(CHIUSURA, ["TRN", "OTP"], 0).dentro.map((m) => m.codice), ["TRN"]);
  assert.deepEqual(trovaRitorni(CHIUSURA, ["TRN", "OTP"], 200).dentro.map((m) => m.codice), ["TRN", "MXP", "BGY"]);
});

test("ritorni: la distanza al limite del raggio e' dentro", () => {
  const { MXP, TRN } = CHIUSURA.aeroporti;
  const esatta = distanzaKm(TRN, MXP);
  assert.ok(trovaRitorni(CHIUSURA, ["TRN", "OTP"], esatta).dentro.some((m) => m.codice === "MXP"));
  assert.ok(!trovaRitorni(CHIUSURA, ["TRN", "OTP"], esatta - 1).dentro.some((m) => m.codice === "MXP"));
});

test("ritorni: rotte nascoste escluse", () => {
  const { dentro, fuori } = trovaRitorni(CHIUSURA, ["TRN", "OTP"], 400);
  assert.ok(![...dentro, ...fuori].some((m) => m.codice === "GOA"));
});

test("ritorni: un aeroporto senza voli non rompe nulla", () => {
  assert.deepEqual(trovaRitorni(CHIUSURA, ["OTP", "MXP"], 150), { dentro: [], fuori: [] });
});

test("riepilogo: tratte, compagnie, km totali e arrivo vicino alla partenza", () => {
  const riepilogo = riepilogoGiro(CHIUSURA, ["TRN", "OTP", "BGY"]);
  assert.equal(riepilogo.tratte.length, 2);
  assert.deepEqual(riepilogo.tratte.map((t) => [t.da, t.a]), [["TRN", "OTP"], ["OTP", "BGY"]]);
  assert.equal(riepilogo.tratte[1].cittaDa, "Bucarest Otopeni");
  assert.equal(riepilogo.tratte[1].meta.citta, "Milano Bergamo");
  assert.equal(riepilogo.tratte[1].meta.voliSett, 28);
  assert.equal(riepilogo.kmTotali, 1452 + 1290);
  assert.equal(riepilogo.minutiTotali, 145 + 130);
  assert.equal(riepilogo.durataCompleta, true);
  assert.equal(testoTotale(riepilogo), "2742 km · 4 h 35 min in volo");
  assert.equal(riepilogo.distanzaFinale, distanzaKm(CHIUSURA.aeroporti.TRN, CHIUSURA.aeroporti.BGY));
});

test("riepilogo: tornando alla partenza la distanza e' zero", () => {
  assert.equal(riepilogoGiro(CHIUSURA, ["TRN", "OTP", "TRN"]).distanzaFinale, 0);
});

test("riepilogo: una tratta senza frequenze resta vuota, mai zero", () => {
  const { meta } = riepilogoGiro(CHIUSURA, ["TRN", "OTP", "MXP"]).tratte[1];
  assert.equal(meta.voliSett, null);
  assert.equal(meta.giorni, null);
  assert.equal(meta.stato, "stagionale");
});

test("riepilogo: una tratta sparita dai dati non rompe nulla", () => {
  const riepilogo = riepilogoGiro(CHIUSURA, ["TRN", "MAD"]);
  assert.equal(riepilogo.tratte[0].meta, null);
  assert.equal(riepilogo.kmTotali, 0);
  assert.equal(riepilogo.durataCompleta, false);
  assert.equal(testoTotale(riepilogo), "0 km");
});

test("riepilogo: se manca una durata il totale e' un minimo", () => {
  const dati = {
    ...CHIUSURA,
    rotte: [
      rotta("TRN", "OTP", "attiva", VOLO, { km: 100, durata_min: 60 }),
      rotta("OTP", "MAD", "attiva", VOLO, { km: 200, durata_min: null }),
    ],
  };
  assert.equal(testoTotale(riepilogoGiro(dati, ["TRN", "OTP", "MAD"])), "300 km · almeno 1 h in volo");
});

test("changelog: versioni e voci, senza i segni del file", () => {
  const testo = "# Changelog\n\nIntro.\n\n## 0.2.0 · oggi\n\nFrase.\n\n- Una `cosa`\n- Altra\n\n## 0.1.0 · ieri\n- Prima\r\n";
  assert.deepEqual(leggiChangelog(testo), [
    { titolo: "0.2.0 · oggi", voci: ["Frase.", "Una cosa", "Altra"] },
    { titolo: "0.1.0 · ieri", voci: ["Prima"] },
  ]);
  assert.deepEqual(leggiChangelog(""), []);
});

test("il vero changelog si legge e la prima versione e' quella attuale", () => {
  const leggi = (nome) => readFileSync(new URL(`../${nome}`, import.meta.url), "utf8");
  const [prima] = leggiChangelog(leggi("CHANGELOG.md"));
  assert.ok(prima.titolo.startsWith(leggi("VERSIONE").trim()), prima.titolo);
  assert.ok(prima.voci.length > 0);
});

function memoriaFinta(iniziale = null) {
  let valore = iniziale;
  return { getItem: () => valore, setItem: (_, v) => { valore = v; } };
}

test("impostazioni: senza nulla di salvato valgono quelle iniziali", () => {
  assert.deepEqual(leggiImpostazioni(memoriaFinta()), IMPOSTAZIONI_INIZIALI);
  assert.deepEqual(leggiImpostazioni(null), IMPOSTAZIONI_INIZIALI);
});

test("impostazioni: si salvano e si rileggono", () => {
  const memoria = memoriaFinta();
  assert.equal(salvaImpostazioni(memoria, { raggio: 300, stagionali: false }), true);
  assert.deepEqual(leggiImpostazioni(memoria), { raggio: 300, stagionali: false });
});

test("impostazioni: valori rovinati non rompono nulla", () => {
  for (const guasto of ["non json", "null", '{"raggio":9999}', '{"raggio":"x","stagionali":"si"}', '{"raggio":-10}']) {
    assert.deepEqual(leggiImpostazioni(memoriaFinta(guasto)), IMPOSTAZIONI_INIZIALI, guasto);
  }
  assert.equal(leggiImpostazioni(memoriaFinta('{"raggio":127,"stagionali":false}')).raggio, 130);
});

test("impostazioni: memoria che da' errore", () => {
  const rotta = { getItem() { throw new Error("no"); }, setItem() { throw new Error("no"); } };
  assert.deepEqual(leggiImpostazioni(rotta), IMPOSTAZIONI_INIZIALI);
  assert.equal(salvaImpostazioni(rotta, IMPOSTAZIONI_INIZIALI), false);
  assert.equal(salvaImpostazioni(null, IMPOSTAZIONI_INIZIALI), false);
});

test("testi della chiusura", () => {
  assert.equal(testoRitorni(1, 150), "1 ritorno entro 150 km");
  assert.equal(testoRitorni(3, 0), "3 ritorni entro 0 km");
  assert.equal(testoVicino(0, "Torino"), "Torna a Torino");
  assert.equal(testoVicino(123, "Torino"), "A 123 km da Torino");
  assert.equal(testoTratte(1), "1 tratta");
  assert.equal(testoTratte(4), "4 tratte");
});

test("dati veri: l'esempio del progetto si chiude", () => {
  const dati = JSON.parse(readFileSync(new URL("../dati/dove_volo.json", import.meta.url), "utf8"));
  const { dentro } = trovaRitorni(dati, ["TRN", "OTP", "TBS"], 150);
  assert.ok(dentro.some((m) => m.codice === "BGY" || m.codice === "MXP"), dentro.map((m) => m.codice).join());
  assert.ok(dentro.every((m) => m.distanza <= 150));
  const riepilogo = riepilogoGiro(dati, ["TRN", "OTP", "TBS", dentro[0].codice]);
  assert.ok(riepilogo.tratte.every((t) => t.meta));
  assert.ok(riepilogo.kmTotali > 3000);
});

test("stato della rotta a parole", () => {
  const dal = { dal: "2027-03-28", al: null };
  const al = { dal: null, al: "2027-01-10" };
  assert.equal(testoStato({ stato: "attiva", stagionaleWiki: false, periodo: null }), "");
  assert.equal(testoStato({ stato: "attiva", stagionaleWiki: true, periodo: null }), "stagionale, vola adesso");
  assert.equal(testoStato({ stato: "attiva", stagionaleWiki: true, periodo: al }), "stagionale, vola adesso, fino al 10 gen 2027");
  assert.equal(testoStato({ stato: "annunciata", periodo: dal }), "annunciata, dal 28 mar 2027");
  assert.equal(testoStato({ stato: "annunciata", periodo: null }), "annunciata");
  assert.equal(testoStato({ stato: "stagionale", periodo: dal, vistaUltima: "2026-10-04" }), "stagionale, dal 28 mar 2027");
  assert.equal(testoStato({ stato: "stagionale", periodo: null, vistaUltima: "2026-10-04" }), "stagionale, vista il 4 ott 2026");
  assert.equal(testoStato({ stato: "stagionale", periodo: null, vistaUltima: null }), "stagionale");
  assert.equal(testoStato({ stato: "stagionale", periodo: { dal: "2026-12-19", al: "2027-01-10" }, vistaUltima: null }),
    "stagionale, dal 19 dic 2026 al 10 gen 2027");
});

test("compagnie da Wikipedia: nome senza codice", () => {
  const dati = { ...DATI, rotte: [rotta("TRN", "OTP", "stagionale", [{ iata: null, nome: "TUI Airways", voli_sett: null, giorni: null }],
    { vista_ultima: null, stagionale_wiki: true })] };
  const [meta] = meteDa(dati, "TRN");
  assert.equal(meta.compagnie[0].nome, "TUI Airways");
  assert.equal(meta.voliSett, null);
  assert.equal(meta.vistaUltima, null);
  assert.equal(meta.stagionaleWiki, true);
});

test("dati veri: tre fonti, stati validi, nessuna rotta ucraina attiva", () => {
  const dati = JSON.parse(readFileSync(new URL("../dati/dove_volo.json", import.meta.url), "utf8"));
  assert.deepEqual(dati.fonti.map((f) => f.nome), ["omaxim/airline-route-data", "Wikipedia", "OurAirports"]);
  assert.ok(dati.rotte.some((r) => r.stato === "annunciata"));
  assert.ok(dati.rotte.some((r) => r.stato === "attiva" && r.stagionale_wiki));
  const attiveUa = dati.rotte.filter((r) => r.stato === "attiva" && dati.aeroporti[r.da].paese === "UA");
  assert.deepEqual(attiveUa, []);
  const annunciata = meteDa(dati, "OTP").find((m) => m.codice === "TBS");
  assert.match(testoStato(annunciata), /^annunciata, dal /);
});

test("controllo dei dati: file sbagliati rifiutati", () => {
  assert.equal(controllaDati(DATI), DATI);
  assert.throws(() => controllaDati(null), /Dove_Volo/);
  assert.throws(() => controllaDati({ tipo: "altro" }), /Dove_Volo/);
  assert.throws(() => controllaDati({ tipo: "dove_volo_dati", versione_formato: 2 }), /non gestito/);
});

test("il vero file dati si legge e Torino ha mete", () => {
  const dati = controllaDati(JSON.parse(readFileSync(new URL("../dati/dove_volo.json", import.meta.url), "utf8")));
  const partenze = contaPartenze(dati);
  assert.equal(cercaAeroporti(dati, "Torino", partenze)[0].codice, "TRN");
  assert.ok(meteDa(dati, "TRN").length > 20);
  assert.ok(!dati.aeroporti.JCU, "gli elicotteri sono fuori");
});

test("dati veri: si trovano con le parole che usa una persona", () => {
  const dati = JSON.parse(readFileSync(new URL("../dati/dove_volo.json", import.meta.url), "utf8"));
  const partenze = contaPartenze(dati);
  const primo = (testo) => cercaAeroporti(dati, testo, partenze)[0]?.codice;
  const tutti = (testo) => codici(cercaAeroporti(dati, testo, partenze));

  for (const [testo, atteso] of [
    ["Bergamo", "BGY"], ["Treviso", "TSF"], ["Charleroi", "CRL"], ["Beauvais", "BVA"], ["Weeze", "NRN"],
    ["Malpensa", "MXP"], ["Linate", "LIN"], ["Fiumicino", "FCO"], ["Ciampino", "CIA"],
    ["Stansted", "STN"], ["Gatwick", "LGW"], ["Bucarest", "OTP"], ["Tbilisi", "TBS"], ["Kutaisi", "KUT"],
    ["Barcellona", "BCN"], ["Atene", "ATH"], ["Keflavik", "KEF"], ["Torino", "TRN"],
  ]) {
    assert.equal(primo(testo), atteso, testo);
  }
  for (const codice of ["MXP", "BGY", "LIN"]) assert.ok(tutti("Milano").includes(codice), `Milano: ${codice}`);
  for (const codice of ["VCE", "TSF"]) assert.ok(tutti("Venezia").includes(codice), `Venezia: ${codice}`);
  for (const codice of ["LHR", "STN", "LGW"]) assert.ok(tutti("Londra").includes(codice), `Londra: ${codice}`);
});

test("citta' con piu' aeroporti: si vede quale", () => {
  const dati = JSON.parse(readFileSync(new URL("../dati/dove_volo.json", import.meta.url), "utf8"));
  const nome = (codice) => nomeCitta(dati.aeroporti[codice], codice);
  assert.equal(nome("MXP"), "Milano Malpensa");
  assert.equal(nome("LIN"), "Milano Linate");
  assert.equal(nome("CDG"), "Parigi Charles de Gaulle");
  assert.equal(nome("LHR"), "Londra Heathrow");
  assert.equal(nome("TRN"), "Torino");
  assert.equal(meteDa(dati, "OTP").find((m) => m.codice === "BGY").citta, "Milano Bergamo");
});

test("dati veri: nessun nome doppio tra aeroporti con voli in partenza", () => {
  const dati = JSON.parse(readFileSync(new URL("../dati/dove_volo.json", import.meta.url), "utf8"));
  const partenze = contaPartenze(dati);
  const visti = new Map();
  const doppi = [];
  for (const [codice, aeroporto] of Object.entries(dati.aeroporti)) {
    if (!partenze[codice]) continue;
    const nome = nomeCitta(aeroporto, codice);
    if (visti.has(nome)) doppi.push(`${nome}: ${visti.get(nome)} e ${codice}`);
    visti.set(nome, codice);
  }
  assert.deepEqual(doppi, []);
});
