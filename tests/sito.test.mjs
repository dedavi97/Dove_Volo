// Test della logica del sito. Si eseguono con: node --test "tests/*.test.mjs"
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  cercaAeroporti, contaPartenze, controllaDati, filtraMete, meteDa, nomeCitta, nomePaese, normalizza,
  paesiDelleMete, puntiArco, testoData, testoDurata, testoGiorni, testoKm, testoMete,
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
