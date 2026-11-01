"""Test dello scanner: nessuno usa la rete."""
import json
import os
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock
from urllib.error import URLError

from scanner import __main__ as principale
from scanner import versione
from scanner.area import leggi_aeroporti
from scanner.costruisci import costruisci, entro_12_mesi, importa_storico
from scanner.dati_file import in_testo, leggi, scrivi, valida
from scanner.differenze import confronta, riepilogo
from scanner.fonti import Scaricatore
from scanner.pubblica import motivo_blocco, pubblica
from scanner.settimana import finestra, giorni_in_testo, ricostruisci, ultimo_cambio_orario

OGGI = date(2026, 11, 2)


def riga(codice, paese, lat=45.0, lon=7.0, tipo="medium_airport", servizio="yes"):
    return {"iata_code": codice, "iso_country": paese, "latitude_deg": str(lat), "longitude_deg": str(lon),
            "type": tipo, "scheduled_service": servizio, "name": f"Aeroporto {codice}", "municipality": codice}


RIGHE = [
    riga("TRN", "IT", 45.2, 7.65), riga("OTP", "RO", 44.57, 26.08), riga("BGY", "IT", 45.67, 9.7),
    riga("BSL", "FR", 47.59, 7.53), riga("MLN", "ES", 35.28, -2.96),
    riga("JCU", "ES", 35.89, -5.3, tipo="heliport"),
    riga("BON", "BQ", 12.13, -68.27), riga("CAI", "EG", 30.12, 31.41),
    riga("VKO", "RU", 55.59, 37.26), riga("SVX", "RU", 56.74, 60.8),
    riga("XXX", "IT", tipo="closed"),
]
AREA, CONOSCIUTI = leggi_aeroporti(RIGHE)


def volo(meta, compagnia="W6", numero="W61", partenza="06:00", arrivo="08:00", fuso_p="60", fuso_a="120"):
    return [meta, compagnia, numero, partenza, arrivo, fuso_p, fuso_a]


def giornata(data, voli):
    return {"date": data, "flights": voli, "failed": [], "partial": True}


def settimana_piena(codice="TRN", meta="OTP", inizio=2):
    """Sette giornate da lunedi' 2 novembre 2026, ognuna con un volo."""
    return [giornata(f"2026-11-{inizio + i:02d}", {codice: [volo(meta, numero=f"W6{i}")]}) for i in range(7)]


def crea(giornate=None, precedente=None, storico=None, oggi=OGGI):
    return costruisci(AREA, CONOSCIUTI, giornate, precedente, storico, oggi)


def rotta_di(dati, da, a):
    return next(r for r in dati["rotte"] if r["da"] == da and r["a"] == a)


class TestArea(unittest.TestCase):
    def test_paesi_inclusi_ed_esclusi(self):
        for dentro in ("TRN", "OTP", "BSL", "MLN"):
            self.assertIn(dentro, AREA)
        for fuori in ("BON", "CAI"):
            self.assertNotIn(fuori, AREA)

    def test_russia_solo_europea(self):
        self.assertIn("VKO", AREA)
        self.assertNotIn("SVX", AREA)

    def test_eliporti_fuori(self):
        self.assertNotIn("JCU", AREA)
        area, conosciuti = leggi_aeroporti([riga("AEI", "ES"), riga("VIF", "IT")])
        self.assertEqual(area, {})
        self.assertIn("AEI", conosciuti)

    def test_aeroporti_chiusi_fuori(self):
        self.assertNotIn("XXX", AREA)


class TestSettimana(unittest.TestCase):
    def test_cambio_orario(self):
        self.assertEqual(ultimo_cambio_orario(date(2026, 11, 8)), date(2026, 10, 25))
        self.assertEqual(ultimo_cambio_orario(date(2026, 10, 24)), date(2026, 3, 29))
        self.assertEqual(ultimo_cambio_orario(date(2027, 1, 5)), date(2026, 10, 25))

    def test_finestra_esclude_orario_precedente(self):
        giornate = [giornata(f"2026-10-{g}", {}) for g in range(20, 32)] + [giornata("2026-11-08", {})]
        date_usate = [g["date"] for g in finestra(giornate)]
        self.assertEqual(date_usate[0], "2026-10-25")
        self.assertNotIn("2026-10-24", date_usate)

    def test_finestra_appena_dopo_il_cambio_prende_7_giornate(self):
        giornate = [giornata(f"2026-10-{g}", {}) for g in range(20, 28)]
        self.assertEqual(len(finestra(giornate)), 7)

    def test_conta_voli_e_giorni_da_lunedi(self):
        giornate = [
            giornata("2026-11-02", {"TRN": [volo("OTP", numero="A"), volo("OTP", numero="B")]}),  # lunedi'
            giornata("2026-11-08", {"TRN": [volo("OTP", numero="C")]}),  # domenica
        ]
        compagnia = ricostruisci(giornate, AREA, CONOSCIUTI)["rotte"][("TRN", "OTP")]["compagnie"]["W6"]
        self.assertEqual(compagnia["voli"], 3)
        self.assertEqual(giorni_in_testo(compagnia["giorni"]), "1000001")

    def test_stesso_giorno_vale_la_giornata_piu_recente(self):
        giornate = [
            giornata("2026-10-26", {"TRN": [volo("OTP", numero="A"), volo("BGY", numero="V")]}),  # lunedi'
            giornata("2026-11-02", {"TRN": [volo("OTP", numero="B")]}),  # lunedi' dopo
        ]
        rotte = ricostruisci(giornate, AREA, CONOSCIUTI)["rotte"]
        self.assertEqual(rotte[("TRN", "OTP")]["compagnie"]["W6"]["voli"], 1)
        self.assertNotIn(("TRN", "BGY"), rotte)

    def test_settimana_incompleta(self):
        copertura = ricostruisci(settimana_piena()[:5], AREA, CONOSCIUTI)["copertura"]
        self.assertFalse(copertura["TRN"]["completa"])
        self.assertEqual(copertura["TRN"]["dal"], "2026-11-02")

    def test_settimana_completa(self):
        self.assertTrue(ricostruisci(settimana_piena(), AREA, CONOSCIUTI)["copertura"]["TRN"]["completa"])

    def test_durata_con_i_fusi(self):
        rotta = ricostruisci(settimana_piena(), AREA, CONOSCIUTI)["rotte"][("TRN", "OTP")]
        self.assertEqual(set(rotta["durate"]), {60})  # 2 ore di orologio, meno un'ora di fuso

    def test_mlh_si_unisce_a_bsl_senza_doppioni(self):
        giornate = [giornata("2026-11-02", {
            "BSL": [volo("OTP", numero="A")],
            "MLH": [volo("OTP", numero="B"), volo("OTP", numero="A"), volo("BSL", numero="Z")],
            "TRN": [volo("MLH", numero="C")],
        })]
        r = ricostruisci(giornate, AREA, CONOSCIUTI)
        self.assertEqual(r["rotte"][("BSL", "OTP")]["compagnie"]["W6"]["voli"], 2)
        self.assertIn(("TRN", "BSL"), r["rotte"])
        self.assertNotIn(("BSL", "BSL"), r["rotte"])

    def test_rotte_fuori_area_ed_eliporti_scartate(self):
        giornate = [giornata("2026-11-02", {"TRN": [volo("CAI"), volo("JCU")], "JCU": [volo("TRN")]})]
        r = ricostruisci(giornate, AREA, CONOSCIUTI)
        self.assertEqual(r["rotte"], {})
        self.assertEqual(r["mete_ignote"], set())

    def test_mete_sconosciute_segnalate(self):
        r = ricostruisci([giornata("2026-11-02", {"TRN": [volo("QQQ")]})], AREA, CONOSCIUTI)
        self.assertEqual(r["mete_ignote"], {"QQQ"})


FILE_OTTOBRE = {
    "TRN": {"city_name": "Turin", "routes": [
        {"iata": "OTP", "min": 135, "flights_per_week": 4, "carriers": [{"iata": "W6", "name": "Wizz Air"}]},
        {"iata": "BGY", "min": 0, "flights_per_week": 0, "carriers": [{"iata": "FR", "name": "Ryanair"}]},
        {"iata": "CAI", "min": 200, "flights_per_week": 2, "carriers": []},
    ]},
    "MLH": {"city_name": "Mulhouse", "routes": [{"iata": "OTP", "min": 150, "flights_per_week": 2, "carriers": [{"iata": "W6", "name": "Wizz Air"}]}]},
    "JCU": {"routes": [{"iata": "TRN", "min": 60, "flights_per_week": 2, "carriers": []}]},
}


class TestStorico(unittest.TestCase):
    def setUp(self):
        self.storico = importa_storico(FILE_OTTOBRE, AREA)
        self.rotte, self.nomi, self.citta = self.storico

    def test_citta_di_omaxim_conservate_anche_dopo_la_prima_esecuzione(self):
        self.assertEqual(self.citta, {"TRN": "Turin"})  # MLH non sovrascrive BSL
        primo, _ = crea(settimana_piena(), storico=self.storico)
        self.assertEqual(primo["aeroporti"]["TRN"]["citta"], "Turin")
        self.assertEqual(primo["aeroporti"]["OTP"]["citta"], "OTP")  # non c'e': resta OurAirports
        secondo, _ = crea(settimana_piena(), precedente=primo)
        self.assertEqual(secondo["aeroporti"]["TRN"]["citta"], "Turin")

    def test_import_filtrato_e_con_alias(self):
        self.assertEqual(set(self.rotte), {("TRN", "OTP"), ("TRN", "BGY"), ("BSL", "OTP")})

    def test_import_senza_frequenze_per_compagnia(self):
        self.assertEqual(self.rotte[("TRN", "OTP")]["compagnie"],
                         [{"iata": "W6", "voli_sett": None, "giorni": None}])
        self.assertEqual(self.rotte[("TRN", "OTP")]["vista_ultima"], "2026-10-04")

    def test_durata_zero_diventa_vuota(self):
        self.assertIsNone(self.rotte[("TRN", "BGY")]["durata_min"])

    def test_prima_esecuzione_rotta_estiva_stagionale(self):
        giornate = settimana_piena()
        dati, _ = crea(giornate, storico=self.storico)
        self.assertEqual(rotta_di(dati, "TRN", "OTP")["stato"], "attiva")
        estiva = rotta_di(dati, "TRN", "BGY")
        self.assertEqual(estiva["stato"], "stagionale")
        self.assertEqual(estiva["vista_ultima"], "2026-10-04")
        self.assertEqual(dati["compagnie"]["FR"], "Ryanair")
        valida(dati)

    def test_storico_ignorato_se_ce_un_file_precedente(self):
        precedente, _ = crea(settimana_piena())
        dati, _ = crea(settimana_piena(), precedente=precedente, storico=self.storico)
        self.assertEqual({(r["da"], r["a"]) for r in dati["rotte"]}, {("TRN", "OTP")})


class TestRegolaStagionali(unittest.TestCase):
    def precedente(self, vista):
        dati, _ = crea(settimana_piena())
        dati["rotte"][0]["vista_ultima"] = vista
        return dati

    def test_entro_12_mesi_al_limite(self):
        self.assertTrue(entro_12_mesi("2025-11-02", OGGI))
        self.assertFalse(entro_12_mesi("2025-11-01", OGGI))
        self.assertTrue(entro_12_mesi("2023-02-28", date(2024, 2, 29)))

    def test_assente_da_poco_resta_stagionale(self):
        giornate = [giornata("2026-11-02", {"BGY": [volo("OTP")]})]
        dati, _ = crea(giornate, precedente=self.precedente("2026-06-01"))
        rotta = rotta_di(dati, "TRN", "OTP")
        self.assertEqual(rotta["stato"], "stagionale")
        self.assertEqual(rotta["vista_ultima"], "2026-06-01")
        self.assertIsNone(rotta["compagnie"][0]["voli_sett"])

    def test_sparita_da_piu_di_12_mesi_si_nasconde_ma_resta_nel_file(self):
        giornate = [giornata("2026-11-02", {"BGY": [volo("OTP")]})]
        dati, _ = crea(giornate, precedente=self.precedente("2025-10-31"))
        self.assertEqual(rotta_di(dati, "TRN", "OTP")["stato"], "nascosta")
        valida(dati)

    def test_sparita_da_piu_di_12_mesi_ma_stagionale_su_wikipedia(self):
        precedente = self.precedente("2025-10-31")
        precedente["rotte"][0]["stagionale_wiki"] = True
        dati, _ = crea([giornata("2026-11-02", {"BGY": [volo("OTP")]})], precedente=precedente)
        self.assertEqual(rotta_di(dati, "TRN", "OTP")["stato"], "stagionale")

    def test_rotta_nascosta_che_torna_riparte_attiva(self):
        precedente = self.precedente("2025-10-31")
        precedente["rotte"][0]["stato"] = "nascosta"
        dati, _ = crea(settimana_piena(), precedente=precedente)
        rotta = rotta_di(dati, "TRN", "OTP")
        self.assertEqual(rotta["stato"], "attiva")
        self.assertEqual(rotta["compagnie"][0]["voli_sett"], 7)


class TestSenzaFrequenze(unittest.TestCase):
    def test_voli_e_giorni_vuoti_mai_zero(self):
        precedente, _ = crea(settimana_piena())
        dati, _ = crea(None, precedente=precedente)
        rotta = rotta_di(dati, "TRN", "OTP")
        self.assertEqual(rotta["compagnie"], [{"iata": "W6", "voli_sett": None, "giorni": None}])
        valida(dati)

    def test_stato_e_data_restano_com_erano(self):
        precedente, _ = crea(settimana_piena())
        dopo = date(2026, 12, 1)
        dati, _ = crea(None, precedente=precedente, oggi=dopo)
        rotta = rotta_di(dati, "TRN", "OTP")
        self.assertEqual(rotta["stato"], "attiva")
        self.assertEqual(rotta["vista_ultima"], rotta_di(precedente, "TRN", "OTP")["vista_ultima"])

    def test_senza_omaxim_dopo_12_mesi_si_nasconde(self):
        precedente, _ = crea(settimana_piena())
        dati, _ = crea(None, precedente=precedente, oggi=date(2028, 1, 1))
        self.assertEqual(rotta_di(dati, "TRN", "OTP")["stato"], "nascosta")

    def test_solo_storico_alla_prima_esecuzione(self):
        dati, _ = crea(None, storico=importa_storico(FILE_OTTOBRE, AREA))
        self.assertEqual(rotta_di(dati, "TRN", "OTP")["stato"], "stagionale")
        self.assertFalse(dati["aeroporti"]["TRN"]["settimana_completa"])
        self.assertIsNone(dati["aeroporti"]["TRN"]["settimana_dal"])
        self.assertEqual([f["nome"] for f in dati["fonti"]], ["OurAirports"])
        valida(dati)

    def test_riepilogo_avvisa(self):
        precedente, _ = crea(settimana_piena())
        dati, _ = crea(None, precedente=precedente)
        self.assertIn("non ha frequenze", riepilogo(precedente, dati, []))

    def test_validazione_rifiuta_lo_zero(self):
        dati, _ = crea(settimana_piena())
        dati["rotte"][0]["compagnie"][0]["voli_sett"] = 0
        with self.assertRaisesRegex(ValueError, "mai zero"):
            valida(dati)


class TestFormato(unittest.TestCase):
    def test_contenuto_completo(self):
        dati, _ = crea(settimana_piena())
        rotta = rotta_di(dati, "TRN", "OTP")
        self.assertEqual(rotta["compagnie"], [{"iata": "W6", "voli_sett": 7, "giorni": "1111111"}])
        self.assertEqual(rotta["durata_min"], 60)
        self.assertTrue(1400 < rotta["km"] < 1600)
        self.assertEqual(dati["compagnie"], {"W6": None})  # senza nome: il sito mostra il codice
        self.assertTrue(dati["aeroporti"]["TRN"]["settimana_completa"])
        self.assertEqual(dati["aeroporti"]["TRN"]["settimana_dal"], "2026-11-02")
        self.assertFalse(dati["aeroporti"]["OTP"]["settimana_completa"])

    def test_vista_ultima_non_va_nel_futuro(self):
        dati, _ = crea(settimana_piena())  # giornate fino all'8 novembre, oggi e' il 2
        self.assertEqual(rotta_di(dati, "TRN", "OTP")["vista_ultima"], "2026-11-02")

    def test_scrivi_e_rileggi(self):
        dati, _ = crea(settimana_piena())
        with tempfile.TemporaryDirectory() as cartella:
            percorso = Path(cartella) / "dati" / "file.json"
            scrivi(dati, percorso)
            self.assertEqual(leggi(percorso), dati)
            self.assertEqual(list(percorso.parent.iterdir()), [percorso])

    def test_una_riga_per_rotta(self):
        dati, _ = crea(settimana_piena())
        self.assertEqual(json.loads(in_testo(dati)), dati)
        self.assertIn('\n{"da":"TRN"', in_testo(dati))

    def test_file_sconosciuto_rifiutato(self):
        with self.assertRaisesRegex(ValueError, "Non e' un file"):
            valida({"tipo": "altro"})

    def test_scrittura_non_valida_lascia_il_file_com_era(self):
        dati, _ = crea(settimana_piena())
        with tempfile.TemporaryDirectory() as cartella:
            percorso = Path(cartella) / "file.json"
            scrivi(dati, percorso)
            guasto = json.loads(json.dumps(dati))
            guasto["rotte"][0]["da"] = "ZZZ"
            with self.assertRaises(ValueError):
                scrivi(guasto, percorso)
            self.assertEqual(leggi(percorso), dati)

    def test_versione_in_un_solo_punto(self):
        self.assertRegex(versione(), r"^\d+\.\d+\.\d+$")


class TestDifferenze(unittest.TestCase):
    def test_nuove_sparite_tornate_cambiate(self):
        precedente, _ = crea(settimana_piena() + settimana_piena("BGY", "OTP"))
        giornate = [giornata("2026-11-02", {"TRN": [volo("OTP")], "OTP": [volo("BGY")]})]
        dati, _ = crea(giornate, precedente=precedente)
        d = confronta(precedente, dati)
        self.assertEqual(d["nuove"], [("OTP", "BGY")])
        self.assertEqual(d["sparite"], [("BGY", "OTP")])
        self.assertEqual(d["cambiate"], [("TRN", "OTP")])
        terzo, _ = crea(settimana_piena("BGY", "OTP"), precedente=dati)
        self.assertIn(("BGY", "OTP"), confronta(dati, terzo)["tornate"])

    def test_calo_forte_segnalato(self):
        precedente, _ = crea(settimana_piena() + settimana_piena("BGY", "OTP"))
        dati, _ = crea([giornata("2026-11-02", {"TRN": [volo("OTP")]})], precedente=precedente)
        self.assertIn("scendono", riepilogo(precedente, dati, []))

    def test_prima_esecuzione(self):
        dati, _ = crea(settimana_piena())
        self.assertIn("Prima esecuzione", riepilogo(None, dati, ["prova"]))


class ScaricatoreGuasto(Scaricatore):
    def _leggi(self, url, secondi=180):
        raise URLError("rete assente")


class TestScaricatore(unittest.TestCase):
    def test_omaxim_irraggiungibile_non_ferma_tutto(self):
        with tempfile.TemporaryDirectory() as cartella:
            s = ScaricatoreGuasto(Path(cartella), "0")
            avvisi = []
            self.assertIsNone(s.giornate(avvisi))
            self.assertIsNone(s.storico(avvisi))
            self.assertEqual(len(avvisi), 2)

    def test_aeroporti_senza_rete_ne_copia_danno_errore(self):
        with tempfile.TemporaryDirectory() as cartella:
            with self.assertRaises(URLError):
                ScaricatoreGuasto(Path(cartella), "0").aeroporti([])

    def test_aeroporti_senza_rete_usano_la_copia(self):
        with tempfile.TemporaryDirectory() as cartella:
            (Path(cartella) / "airports.csv").write_text("iata_code,type\nTRN,medium_airport\n", encoding="utf-8")
            avvisi = []
            righe = ScaricatoreGuasto(Path(cartella), "0").aeroporti(avvisi)
            self.assertEqual(righe[0]["iata_code"], "TRN")
            self.assertEqual(len(avvisi), 1)

    def test_prepara_senza_omaxim_produce_un_file_valido(self):
        class Finto:
            def aeroporti(self, avvisi):
                return RIGHE

            def giornate(self, avvisi):
                avvisi.append("omaxim non disponibile")

            def storico(self, avvisi):
                return FILE_OTTOBRE

        dati, avvisi = principale.prepara(Finto(), None, OGGI, senza_wikipedia=True)
        valida(dati)
        self.assertIn("omaxim non disponibile", avvisi)
        self.assertTrue(dati["rotte"])
        self.assertTrue(all(c["voli_sett"] is None for r in dati["rotte"] for c in r["compagnie"]))

    def test_prepara_avvisa_se_omaxim_e_fermo(self):
        class Finto:
            def aeroporti(self, avvisi):
                return RIGHE

            def giornate(self, avvisi):
                return settimana_piena()

            def storico(self, avvisi):
                return None

        _, avvisi = principale.prepara(Finto(), None, date(2026, 12, 15), senza_wikipedia=True)
        self.assertTrue(any("ferma" in a for a in avvisi))


AMBIENTE_GIT = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@example.com",
                "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@example.com"}


class TestPubblica(unittest.TestCase):
    """Usa un vero git, con un finto GitHub in una cartella temporanea."""

    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self._temp.cleanup)
        base = Path(self._temp.name).resolve()
        self.remoto, self.locale = base / "remoto.git", base / "locale"
        self.git(base, "init", "--quiet", "--bare", "-b", "main", str(self.remoto))
        self.git(base, "clone", "--quiet", str(self.remoto), str(self.locale))
        self.git(self.locale, "checkout", "--quiet", "-B", "main")
        self.dati = self.locale / "dati" / "file.json"
        (self.locale / "codice.py").write_text("x = 1\n", encoding="utf-8")
        self.git(self.locale, "add", "codice.py")
        self.git(self.locale, "commit", "--quiet", "-m", "inizio")
        self.git(self.locale, "push", "--quiet", "-u", "origin", "main")
        patcher = mock.patch.dict(os.environ, AMBIENTE_GIT)
        patcher.start()
        self.addCleanup(patcher.stop)

    def git(self, cartella, *argomenti):
        return subprocess.run(["git", *argomenti], cwd=cartella, env=AMBIENTE_GIT, check=True,
                              capture_output=True, text=True).stdout

    def file_nel_remoto(self):
        return self.git(self.remoto, "ls-tree", "-r", "--name-only", "main").split()

    def scrivi_dati(self):
        dati, _ = crea(settimana_piena())
        scrivi(dati, self.dati)

    def test_pubblica_solo_il_file_dati(self):
        (self.locale / "codice.py").write_text("x = 2\n", encoding="utf-8")
        (self.locale / "appunti.txt").write_text("segreto\n", encoding="utf-8")
        self.git(self.locale, "add", "appunti.txt")
        self.assertIsNone(motivo_blocco(self.locale, self.dati))
        self.scrivi_dati()
        self.assertEqual(pubblica(self.locale, self.dati, "2026-11-02"), (True, "Pubblicato."))
        self.assertEqual(sorted(self.file_nel_remoto()), ["codice.py", "dati/file.json"])
        self.assertEqual(self.git(self.remoto, "show", "main:codice.py"), "x = 1\n")
        self.assertIn("Dati aggiornati al 2026-11-02", self.git(self.remoto, "log", "-1", "--format=%s", "main"))

    def test_senza_differenze_non_crea_commit(self):
        self.scrivi_dati()
        pubblica(self.locale, self.dati, "2026-11-02")
        prima = self.git(self.locale, "rev-parse", "HEAD")
        self.assertEqual(pubblica(self.locale, self.dati, "2026-11-02"), (True, "Nessuna differenza da pubblicare."))
        self.assertEqual(self.git(self.locale, "rev-parse", "HEAD"), prima)

    def test_blocco_se_ci_sono_commit_non_pubblicati(self):
        (self.locale / "codice.py").write_text("x = 3\n", encoding="utf-8")
        self.git(self.locale, "commit", "--quiet", "-am", "non pubblicato")
        self.assertIn("non ancora pubblicati", motivo_blocco(self.locale, self.dati))

    def test_blocco_se_github_e_avanti(self):
        altro = self.locale.parent / "altro"
        self.git(self.locale.parent, "clone", "--quiet", str(self.remoto), str(altro))
        (altro / "nuovo.txt").write_text("y\n", encoding="utf-8")
        self.git(altro, "add", "nuovo.txt")
        self.git(altro, "commit", "--quiet", "-m", "dall'altro PC")
        self.git(altro, "push", "--quiet")
        self.assertIn("git pull", motivo_blocco(self.locale, self.dati))

    def test_blocco_se_il_file_dati_e_stato_toccato(self):
        self.scrivi_dati()
        self.assertIn("modifiche non pubblicate", motivo_blocco(self.locale, self.dati))


class TestDomanda(unittest.TestCase):
    def test_solo_s_conferma(self):
        for risposta, atteso in (("S", True), ("s", True), ("n", False), ("", False), ("si", False)):
            with mock.patch("builtins.input", return_value=risposta):
                self.assertEqual(principale.chiedi_conferma(), atteso, risposta)

    def test_senza_tastiera_non_pubblica(self):
        with mock.patch("builtins.input", side_effect=EOFError):
            self.assertFalse(principale.chiedi_conferma())


if __name__ == "__main__":
    unittest.main()
