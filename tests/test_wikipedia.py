"""Test della lettura di Wikipedia e di come entra nel file dati: nessuno usa la rete."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from urllib.error import URLError

from scanner.area import leggi_aeroporti
from scanner.costruisci import costruisci
from scanner.dati_file import valida
from scanner.differenze import confronta
from scanner.wikipedia import (Wikipedia, carica_con_cache, leggi_data, leggi_pagina, riassumi_rotta, rotte_da_pagine)

OGGI = date(2026, 11, 2)


def riga(codice, paese, lat=45.0, lon=7.0):
    return {"iata_code": codice, "iso_country": paese, "latitude_deg": str(lat), "longitude_deg": str(lon),
            "type": "medium_airport", "scheduled_service": "yes", "name": f"Aeroporto {codice}", "municipality": codice}


AREA, CONOSCIUTI = leggi_aeroporti([
    riga("TRN", "IT", 45.2, 7.65), riga("OTP", "RO", 44.57, 26.08), riga("BGY", "IT", 45.67, 9.7),
    riga("MAD", "ES", 40.47, -3.56), riga("BSL", "FR", 47.59, 7.53),
])

PAGINA = """
==History==
Testo [[Altro]].

==Airlines and destinations==
===Passenger===
<!-- [[Commento]] -->
{{Airport destination list
| 3rdcoltitle = Refs
| [[Ryanair]] | [[Henri Coanda Airport|Bucharest]],<ref>{{cite web|url=x|title=y}}</ref> [[Barajas Airport|Madrid]]<br>'''Seasonal:''' [[Il Caravaggio|Bergamo]]
| [[Wizz Air]] | [[Barajas Airport|Madrid]] (begins 13 December 2026), [[Henri Coanda Airport|Bucharest]] (ends 24 October 2026)
| [[Air Dolomiti]] | '''Seasonal charter:''' [[Il Caravaggio|Bergamo]]
| [[Vecchia]] | [[Barajas Airport|Madrid]] {{small|resumes March 2027}}
}}

===Cargo===
{{Airport destination list
| [[DHL]] | [[Cologne Airport|Colonia]]
}}

==References==
{{Airport destination list
| [[Falso]] | [[Nessuno]]
}}
"""


def voce(compagnia="FR", stagionale=False, charter=False, nota=None, data=None, pagina="X"):
    return {"pagina": pagina, "compagnia": compagnia, "stagionale": stagionale, "charter": charter,
            "nota": nota, "data": data}


class TestPagina(unittest.TestCase):
    def setUp(self):
        self.voci = leggi_pagina(PAGINA)

    def trova(self, compagnia, pagina):
        return next(v for v in self.voci if v["compagnia"] == compagnia and v["pagina"] == pagina)

    def test_legge_le_righe_senza_cargo_ne_altre_sezioni(self):
        self.assertEqual({v["compagnia"] for v in self.voci}, {"Ryanair", "Wizz Air", "Air Dolomiti", "Vecchia"})

    def test_seasonal_vale_solo_dopo_l_etichetta(self):
        self.assertFalse(self.trova("Ryanair", "Barajas Airport")["stagionale"])
        self.assertTrue(self.trova("Ryanair", "Il Caravaggio")["stagionale"])

    def test_charter(self):
        voce_charter = self.trova("Air Dolomiti", "Il Caravaggio")
        self.assertTrue(voce_charter["charter"])
        self.assertTrue(voce_charter["stagionale"])

    def test_note_e_date(self):
        inizia = self.trova("Wizz Air", "Barajas Airport")
        self.assertEqual((inizia["nota"], inizia["data"]), ("begins", "2026-12-13"))
        finisce = self.trova("Wizz Air", "Henri Coanda Airport")
        self.assertEqual((finisce["nota"], finisce["data"]), ("ends", "2026-10-24"))
        riprende = self.trova("Vecchia", "Barajas Airport")
        self.assertEqual((riprende["nota"], riprende["data"]), ("resumes", "2027-03-01"))

    def test_i_riferimenti_non_diventano_mete(self):
        self.assertFalse(any(v["pagina"] in ("x", "y", "Commento") for v in self.voci))

    def test_pagina_senza_tabella(self):
        self.assertIsNone(leggi_pagina("==Airlines and destinations==\nSolo testo."))
        self.assertIsNone(leggi_pagina("Nessuna sezione."))

    def test_voli_sospesi_non_contano(self):
        testo = ("==Airlines and destinations==\n===Passenger===\n"
                 "Since 24 February 2022, all passenger flights have been suspended indefinitely.\n"
                 "{{Airport destination list\n| [[Air France]] | [[Paris]]\n}}\n")
        self.assertEqual(leggi_pagina(testo), [])

    def test_etichetta_suspended_non_conta(self):
        testo = ("==Airlines and destinations==\n{{Airport destination list\n"
                 "| [[A]] | [[B]]<br>'''Suspended:''' [[C]]\n}}\n")
        self.assertEqual([v["pagina"] for v in leggi_pagina(testo)], ["B"])

    def test_la_parola_sospesi_dopo_la_tabella_non_conta(self):
        testo = ("==Airlines and destinations==\n{{Airport destination list\n| [[A]] | [[B]]\n}}\n"
                 "Flights to X were suspended in 2020.\n")
        self.assertEqual(len(leggi_pagina(testo)), 1)

    def test_entrambi_i_nomi_del_modello(self):
        testo = "==Airlines and destinations==\n{{Airport-dest-list\n| [[A]] | [[B]]\n}}\n"
        self.assertEqual(leggi_pagina(testo)[0]["pagina"], "B")

    def test_date(self):
        self.assertEqual(leggi_data("13 December 2026"), "2026-12-13")
        self.assertEqual(leggi_data("December 13, 2026"), "2026-12-13")
        self.assertEqual(leggi_data("March 2027"), "2027-03-01")
        self.assertIsNone(leggi_data("summer 2027"))
        self.assertIsNone(leggi_data(""))


class TestRiassunto(unittest.TestCase):
    def test_normale(self):
        r = riassumi_rotta([voce()], OGGI)
        self.assertTrue(r["normale"])
        self.assertFalse(r["stagionale"] or r["annunciata"])
        self.assertIsNone(r["periodo"])

    def test_stagionale(self):
        r = riassumi_rotta([voce(stagionale=True)], OGGI)
        self.assertTrue(r["stagionale"])

    def test_una_compagnia_tutto_l_anno_batte_la_stagione(self):
        r = riassumi_rotta([voce("FR", stagionale=True), voce("VY")], OGGI)
        self.assertFalse(r["stagionale"])
        self.assertTrue(r["normale"])

    def test_annunciata_con_data_futura(self):
        r = riassumi_rotta([voce(nota="begins", data="2027-03-28")], OGGI)
        self.assertTrue(r["annunciata"])
        self.assertEqual(r["periodo"], {"dal": "2027-03-28", "al": None})

    def test_begins_passato_e_una_rotta_normale(self):
        r = riassumi_rotta([voce(nota="begins", data="2026-10-26")], OGGI)
        self.assertTrue(r["normale"])
        self.assertFalse(r["annunciata"])

    def test_begins_senza_data_capita_e_annunciata(self):
        self.assertTrue(riassumi_rotta([voce(nota="begins")], OGGI)["annunciata"])

    def test_stagionale_con_data_futura_resta_stagionale_col_periodo(self):
        r = riassumi_rotta([voce(stagionale=True, nota="begins", data="2026-12-19")], OGGI)
        self.assertTrue(r["stagionale"])
        self.assertFalse(r["annunciata"])
        self.assertEqual(r["periodo"]["dal"], "2026-12-19")

    def test_finita_e_tolta(self):
        self.assertIsNone(riassumi_rotta([voce(nota="ends", data="2026-10-24")], OGGI))

    def test_finira_resta_con_la_data(self):
        r = riassumi_rotta([voce(stagionale=True, nota="ends", data="2027-01-10")], OGGI)
        self.assertEqual(r["periodo"], {"dal": None, "al": "2027-01-10"})

    def test_solo_charter_non_conta(self):
        self.assertIsNone(riassumi_rotta([voce(charter=True, stagionale=True)], OGGI))

    def test_compagnie_senza_doppioni(self):
        self.assertEqual(riassumi_rotta([voce("FR"), voce("FR"), voce("VY")], OGGI)["compagnie"], ["FR", "VY"])


class TestRottePagine(unittest.TestCase):
    TITOLI = {"Henri Coanda Airport": "OTP", "Barajas Airport": "MAD", "Il Caravaggio": "BGY",
              "Mulhouse": "MLH", "Cairo": "CAI", "Turin": "TRN"}

    def test_solo_area_e_alias(self):
        pagine = {"TRN": [voce(pagina="Henri Coanda Airport"), voce(pagina="Cairo"), voce(pagina="Mulhouse"),
                          voce(pagina="Sconosciuta"), voce(pagina="Turin")]}
        rotte = rotte_da_pagine(pagine, self.TITOLI, AREA, OGGI)
        self.assertEqual(set(rotte), {("TRN", "OTP"), ("TRN", "BSL")})

    def test_voci_della_stessa_rotta_insieme(self):
        pagine = {"TRN": [voce("FR", stagionale=True, pagina="Barajas Airport"), voce("VY", pagina="Barajas Airport")]}
        r = rotte_da_pagine(pagine, self.TITOLI, AREA, OGGI)[("TRN", "MAD")]
        self.assertTrue(r["normale"])
        self.assertEqual(r["compagnie"], ["FR", "VY"])


def giornate_piene(codice="TRN", meta="OTP"):
    return [{"date": f"2026-11-{2 + i:02d}", "partial": True,
             "flights": {codice: [[meta, "W6", f"W6{i}", "06:00", "08:00", "60", "120"]]}} for i in range(7)]


def wiki(**campi):
    base = {"normale": False, "stagionale": False, "annunciata": False, "periodo": None, "compagnie": ["Ryanair"]}
    return {**base, **campi}


def crea(giornate=None, precedente=None, rotte_wiki=None, oggi=OGGI):
    return costruisci(AREA, CONOSCIUTI, giornate, precedente, None, oggi, rotte_wiki)


def rotta_di(dati, da, a):
    return next((r for r in dati["rotte"] if r["da"] == da and r["a"] == a), None)


class TestStati(unittest.TestCase):
    def test_attiva_e_stagionale_insieme(self):
        dati, _ = crea(giornate_piene(), rotte_wiki={("TRN", "OTP"): wiki(stagionale=True)})
        r = rotta_di(dati, "TRN", "OTP")
        self.assertEqual(r["stato"], "attiva")
        self.assertTrue(r["stagionale_wiki"])
        self.assertEqual(r["compagnie"][0]["voli_sett"], 7)

    def test_stagionale_solo_su_wikipedia(self):
        dati, _ = crea(giornate_piene(), rotte_wiki={("TRN", "BGY"): wiki(stagionale=True)})
        r = rotta_di(dati, "TRN", "BGY")
        self.assertEqual(r["stato"], "stagionale")
        self.assertIsNone(r["vista_ultima"])
        self.assertEqual(r["fonte"], "wikipedia")
        self.assertEqual(r["compagnie"], [{"iata": None, "voli_sett": None, "giorni": None, "nome": "Ryanair"}])
        self.assertIsNone(r["durata_min"])
        self.assertTrue(r["km"] > 0)
        valida(dati)

    def test_annunciata_col_periodo(self):
        periodo = {"dal": "2027-03-28", "al": None}
        dati, _ = crea(giornate_piene(), rotte_wiki={("TRN", "BGY"): wiki(annunciata=True, periodo=periodo)})
        r = rotta_di(dati, "TRN", "BGY")
        self.assertEqual(r["stato"], "annunciata")
        self.assertEqual(r["periodo"], periodo)
        valida(dati)

    def test_annunciata_ma_vola_gia_e_attiva(self):
        dati, _ = crea(giornate_piene(), rotte_wiki={("TRN", "OTP"): wiki(annunciata=True)})
        self.assertEqual(rotta_di(dati, "TRN", "OTP")["stato"], "attiva")

    def test_normale_su_wikipedia_ma_aeroporto_completo_non_entra(self):
        dati, _ = crea(giornate_piene(), rotte_wiki={("TRN", "BGY"): wiki(normale=True)})
        self.assertIsNone(rotta_di(dati, "TRN", "BGY"))

    def test_normale_su_wikipedia_e_settimana_incompleta_e_attiva(self):
        dati, _ = crea(giornate_piene()[:3], rotte_wiki={("TRN", "BGY"): wiki(normale=True)})
        r = rotta_di(dati, "TRN", "BGY")
        self.assertEqual(r["stato"], "attiva")
        self.assertIsNone(r["compagnie"][0]["voli_sett"])

    def test_normale_su_wikipedia_e_aeroporto_mai_visto_da_omaxim_non_entra(self):
        dati, _ = crea(giornate_piene(), rotte_wiki={("BGY", "MAD"): wiki(normale=True)})
        self.assertIsNone(rotta_di(dati, "BGY", "MAD"))

    def test_stagionale_su_wikipedia_e_aeroporto_mai_visto_entra(self):
        dati, _ = crea(giornate_piene(), rotte_wiki={("BGY", "MAD"): wiki(stagionale=True)})
        self.assertEqual(rotta_di(dati, "BGY", "MAD")["stato"], "stagionale")

    def test_rotta_nota_assente_normale_su_wikipedia_aeroporto_mai_visto_resta_stagionale(self):
        primo, _ = crea(giornate_piene("BGY", "MAD"))
        secondo, _ = crea(giornate_piene(), primo, {("BGY", "MAD"): wiki(normale=True)})
        self.assertEqual(rotta_di(secondo, "BGY", "MAD")["stato"], "stagionale")

    def test_rotta_nota_assente_normale_su_wikipedia_settimana_incompleta(self):
        primo, _ = crea(giornate_piene("TRN", "BGY"))
        secondo, _ = crea(giornate_piene("TRN", "OTP")[:3], primo, {("TRN", "BGY"): wiki(normale=True)})
        self.assertEqual(rotta_di(secondo, "TRN", "BGY")["stato"], "attiva")

    def test_nascosta_da_vecchia_ma_stagionale_su_wikipedia_torna_visibile(self):
        primo, _ = crea(giornate_piene("TRN", "BGY"))
        rotta_di(primo, "TRN", "BGY")["vista_ultima"] = "2025-01-01"
        rotta_di(primo, "TRN", "BGY")["stato"] = "nascosta"
        secondo, _ = crea(giornate_piene(), primo, {("TRN", "BGY"): wiki(stagionale=True)})
        self.assertEqual(rotta_di(secondo, "TRN", "BGY")["stato"], "stagionale")

    def test_sparita_anche_da_wikipedia_si_nasconde(self):
        primo, _ = crea(giornate_piene(), rotte_wiki={("TRN", "BGY"): wiki(stagionale=True)})
        secondo, _ = crea(giornate_piene(), primo, {})
        self.assertEqual(rotta_di(secondo, "TRN", "BGY")["stato"], "nascosta")
        self.assertFalse(rotta_di(secondo, "TRN", "BGY")["stagionale_wiki"])
        valida(secondo)

    def test_nome_conosciuto_prende_il_codice(self):
        primo, _ = crea(giornate_piene())
        primo["compagnie"]["FR"] = "Ryanair"
        primo["rotte"].append({**primo["rotte"][0], "a": "MAD", "compagnie": [{"iata": "FR", "voli_sett": None, "giorni": None}]})
        primo["aeroporti"]["MAD"] = {**primo["aeroporti"]["OTP"]}
        secondo, _ = crea(giornate_piene(), primo, {("TRN", "BGY"): wiki(stagionale=True)})
        self.assertEqual(rotta_di(secondo, "TRN", "BGY")["compagnie"][0]["iata"], "FR")

    def test_fonti(self):
        con, _ = crea(giornate_piene(), rotte_wiki={})
        self.assertEqual([f["nome"] for f in con["fonti"]], ["omaxim/airline-route-data", "Wikipedia", "OurAirports"])
        senza, _ = crea(giornate_piene())
        self.assertEqual([f["nome"] for f in senza["fonti"]], ["omaxim/airline-route-data", "OurAirports"])


class TestSoloOurAirportsEWikipedia(unittest.TestCase):
    """Il caso per cui Wikipedia e' la rete di sicurezza: omaxim si ferma."""

    def setUp(self):
        self.rotte = {
            ("TRN", "OTP"): wiki(normale=True, compagnie=["Wizz Air"]),
            ("TRN", "MAD"): wiki(stagionale=True, compagnie=["Ryanair"]),
            ("TRN", "BGY"): wiki(annunciata=True, periodo={"dal": "2027-03-28", "al": None}),
        }

    def test_prima_esecuzione(self):
        dati, _ = crea(None, None, self.rotte)
        valida(dati)
        self.assertEqual(rotta_di(dati, "TRN", "OTP")["stato"], "attiva")
        self.assertEqual(rotta_di(dati, "TRN", "MAD")["stato"], "stagionale")
        self.assertEqual(rotta_di(dati, "TRN", "BGY")["stato"], "annunciata")
        self.assertEqual([f["nome"] for f in dati["fonti"]], ["Wikipedia", "OurAirports"])
        for rotta in dati["rotte"]:
            for compagnia in rotta["compagnie"]:
                self.assertIsNone(compagnia["voli_sett"])
                self.assertIsNone(compagnia["giorni"])
        self.assertFalse(dati["aeroporti"]["TRN"]["settimana_completa"])

    def test_con_un_file_precedente_le_frequenze_si_svuotano(self):
        primo, _ = crea(giornate_piene())
        vista = rotta_di(primo, "TRN", "OTP")["vista_ultima"]
        dati, _ = crea(None, primo, self.rotte, date(2026, 12, 1))
        rotta = rotta_di(dati, "TRN", "OTP")
        self.assertEqual(rotta["stato"], "attiva")
        self.assertEqual(rotta["vista_ultima"], vista)
        self.assertEqual(rotta["compagnie"], [{"iata": "W6", "voli_sett": None, "giorni": None}])
        valida(dati)

    def test_differenze_con_compagnie_senza_codice(self):
        dati, _ = crea(None, None, {("TRN", "OTP"): wiki(normale=True, compagnie=["A", "B"])})
        altro, _ = crea(None, dati, {("TRN", "OTP"): wiki(normale=True, compagnie=["A", "B"])})
        self.assertEqual(confronta(dati, altro)["cambiate"], [])


class TestSenzaWikipedia(unittest.TestCase):
    def test_conserva_cio_che_sapeva(self):
        periodo = {"dal": "2027-03-28", "al": None}
        primo, _ = crea(giornate_piene(), rotte_wiki={
            ("TRN", "BGY"): wiki(annunciata=True, periodo=periodo),
            ("TRN", "MAD"): wiki(stagionale=True),
        })
        secondo, _ = crea(giornate_piene(), primo, None)
        self.assertEqual(rotta_di(secondo, "TRN", "BGY")["stato"], "annunciata")
        self.assertEqual(rotta_di(secondo, "TRN", "BGY")["periodo"], periodo)
        self.assertEqual(rotta_di(secondo, "TRN", "MAD")["stato"], "stagionale")
        self.assertTrue(rotta_di(secondo, "TRN", "MAD")["stagionale_wiki"])

    def test_annuncio_scaduto_non_resta_annunciato(self):
        primo, _ = crea(giornate_piene(), rotte_wiki={("TRN", "BGY"): wiki(annunciata=True, periodo={"dal": "2027-03-28", "al": None})})
        secondo, _ = crea(giornate_piene(), primo, None, date(2027, 4, 15))
        self.assertEqual(rotta_di(secondo, "TRN", "BGY")["stato"], "nascosta")


class RispostaFinta:
    """Fa finta di essere Wikidata e Wikipedia, e conta le richieste."""

    def __init__(self, testi):
        self.testi = testi
        self.richieste = 0

    def __call__(self, url):
        self.richieste += 1
        if "sparql" in url:
            righe = [("TRN", "Turin Airport"), ("OTP", "Henri Coanda Airport"), ("TRN", "Caselle"), ("MAD", "Barajas Airport")]
            corpo = {"results": {"bindings": [{"iata": {"value": c}, "titolo": {"value": t}} for c, t in righe]}}
        elif "prop=revisions" in url:
            pagine = [{"title": t, "revisions": [{"slots": {"main": {"content": c}}}]} for t, c in self.testi.items() if t.replace(" ", "+") in url]
            corpo = {"query": {"pages": pagine}}
        else:
            corpo = {"query": {"redirects": [{"from": "Otopeni", "to": "Henri Coanda Airport"}]}}
        return json.dumps(corpo).encode()


class TestRichieste(unittest.TestCase):
    TESTO = "==Airlines and destinations==\n{{Airport destination list\n| [[Wizz Air]] | [[Otopeni|Bucarest]]<br>'''Seasonal:''' [[Barajas Airport|Madrid]]\n}}\n"

    def test_percorso_completo_con_rinvio(self):
        finta = RispostaFinta({"Turin Airport": self.TESTO})
        rotte, statistiche = Wikipedia(finta, pausa=0).rotte(AREA, OGGI)
        self.assertTrue(rotte[("TRN", "OTP")]["normale"])
        self.assertTrue(rotte[("TRN", "MAD")]["stagionale"])
        self.assertEqual(statistiche["pagine"], 1)
        self.assertEqual(statistiche["senza_codice"], 0)
        self.assertLess(finta.richieste, 6)

    def test_pagina_mancante_conta_come_senza_tabella(self):
        _, statistiche = Wikipedia(RispostaFinta({}), pausa=0).rotte(AREA, OGGI)
        self.assertEqual(statistiche["senza_tabella"], 3)

    def test_rete_assente_non_ferma_lo_scanner(self):
        def guasto(url):
            raise URLError("rete assente")
        with tempfile.TemporaryDirectory() as cartella:
            avvisi = []
            self.assertIsNone(carica_con_cache(Wikipedia(guasto, pausa=0), AREA, OGGI, Path(cartella), avvisi))
            self.assertIn("Wikipedia non disponibile", avvisi[0])

    def test_risposta_di_errore_non_ferma_lo_scanner(self):
        with tempfile.TemporaryDirectory() as cartella:
            avvisi = []
            risposta = Wikipedia(lambda url: b'{"error":{"code":"altro"}}', pausa=0)
            self.assertIsNone(carica_con_cache(risposta, AREA, OGGI, Path(cartella), avvisi))

    def test_la_cache_vale_per_la_giornata(self):
        finta = RispostaFinta({"Turin Airport": self.TESTO})
        with tempfile.TemporaryDirectory() as cartella:
            prima = carica_con_cache(Wikipedia(finta, pausa=0), AREA, OGGI, Path(cartella), [])
            conta = finta.richieste
            dopo = carica_con_cache(Wikipedia(finta, pausa=0), AREA, OGGI, Path(cartella), [])
            self.assertEqual(finta.richieste, conta)
            self.assertEqual(prima, dopo)
            carica_con_cache(Wikipedia(finta, pausa=0), AREA, date(2026, 11, 3), Path(cartella), [])
            self.assertGreater(finta.richieste, conta)
            self.assertEqual(len(list(Path(cartella).glob("wikipedia_*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
