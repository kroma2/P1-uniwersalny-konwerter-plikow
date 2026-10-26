"""Testy kamienia milowego 2: regresja CSV/JSON, dokumenty i kontrola procesu."""

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from konwersja import zaladuj_konwertery

zaladuj_konwertery()

from konwersja.csv_json import csv_na_json, json_na_csv
from konwersja.docx_pdf import (
    docx_na_pdf_z_programem,
    ustaw_program_libreoffice,
    wywolaj_proces,
    znajdz_libreoffice,
)
from konwersja.rejestr import ZlecenieKonwersji, dostepne_formaty, pary, wykonaj
from konwersja.txt_docx import akapity, txt_na_docx
from main import main

DANE = ROOT / "dane"


def _libreoffice():
    try:
        return znajdz_libreoffice()
    except RuntimeError:
        return None


class TestRejestr(unittest.TestCase):
    def tearDown(self):
        ustaw_program_libreoffice(None)

    def test_cztery_kierunki(self):
        self.assertEqual(
            pary(),
            [(".csv", ".json"), (".docx", ".pdf"), (".json", ".csv"), (".txt", ".docx")],
        )

    def test_dostepne_formaty_zaleza_od_rozszerzenia(self):
        self.assertEqual(dostepne_formaty(DANE / "osoby.csv"), [".json"])
        self.assertEqual(dostepne_formaty(DANE / "przyklad.txt"), [".docx"])
        self.assertEqual(dostepne_formaty(Path("brak.odt")), [])

    def test_nieobslugiwana_para(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            zrodlo = katalog / "notatka.txt"
            zrodlo.write_text("abc", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                wykonaj(ZlecenieKonwersji(zrodlo, "pdf", katalog))
            self.assertIn("Nieobsługiwana konwersja", str(ctx.exception))


class TestCsvJson(unittest.TestCase):
    def test_csv_na_json_zachowuje_naglowki_i_polskie_znaki(self):
        with tempfile.TemporaryDirectory() as tmp:
            wynik = csv_na_json(DANE / "osoby.csv", Path(tmp))
            dane = json.loads(wynik.read_text(encoding="utf-8"))
        self.assertEqual(dane["kolumny"], ["imię", "miasto", "uwagi"])
        self.assertEqual(dane["wiersze"][0]["imię"], "Zosia")
        self.assertEqual(dane["wiersze"][0]["miasto"], "Łódź")
        self.assertEqual(dane["wiersze"][1]["uwagi"], "")
        self.assertEqual(dane["wiersze"][2]["imię"], "Michał")

    def test_json_na_csv_zachowuje_kolejnosc_kolumn(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            zrodlo = katalog / "kolejnosc.json"
            zrodlo.write_text(
                json.dumps(
                    {
                        "kolumny": ["miasto", "imię"],
                        "wiersze": [{"imię": "Jaźń", "miasto": "Łódź", "inne": "pominąć"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            wynik = json_na_csv(zrodlo, katalog)
            tresc = wynik.read_text(encoding="utf-8")
        self.assertEqual(tresc.splitlines(), ["miasto,imię", "Łódź,Jaźń"])

    def test_obie_strony_daja_te_same_wiersze(self):
        import csv

        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            json_wynik = csv_na_json(DANE / "osoby.csv", katalog)
            csv_wynik = json_na_csv(DANE / "osoby.json", katalog)
            with (DANE / "osoby.csv").open(encoding="utf-8-sig", newline="") as plik:
                oryginal = list(csv.DictReader(plik))
            with csv_wynik.open(encoding="utf-8", newline="") as plik:
                z_json = list(csv.DictReader(plik))
            ponownie = json.loads(json_wynik.read_text(encoding="utf-8"))
        self.assertEqual(z_json, oryginal)
        self.assertEqual(ponownie["wiersze"], oryginal)

    def test_bledny_json_daje_kontrolowany_komunikat(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            zrodlo = katalog / "zly.json"
            zrodlo.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                json_na_csv(zrodlo, katalog)
        self.assertIn("Niepoprawny JSON", str(ctx.exception))


class TestTxtDocx(unittest.TestCase):
    def test_linie_akapity_i_polskie_znaki(self):
        with tempfile.TemporaryDirectory() as tmp:
            wynik = txt_na_docx(DANE / "przyklad.txt", Path(tmp))
            self.assertEqual(
                akapity(wynik),
                ["Zażółć gęślą jaźń", "", "Drugi akapit: Łódź, Gdańsk i Kraków."],
            )

    def test_pusty_plik_nie_dostaje_dodatkowego_akapitu(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            zrodlo = katalog / "pusty.txt"
            zrodlo.write_text("", encoding="utf-8")
            wynik = txt_na_docx(zrodlo, katalog)
            self.assertEqual(akapity(wynik), [])

    def test_odmowa_nadpisania(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            zrodlo = katalog / "notatka.txt"
            zrodlo.write_text("jeden\n", encoding="utf-8")
            txt_na_docx(zrodlo, katalog)
            with self.assertRaises(FileExistsError) as ctx:
                txt_na_docx(zrodlo, katalog)
        self.assertIn("nie nadpisuje", str(ctx.exception))

    def test_sciezka_ze_spacjami(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp) / "katalog ze spacjami"
            katalog.mkdir()
            zrodlo = katalog / "notatka test.txt"
            zrodlo.write_text("Zażółć gęślą jaźń\n", encoding="utf-8")
            wynik = txt_na_docx(zrodlo, katalog)
            self.assertEqual(wynik.name, "notatka test.docx")
            self.assertEqual(akapity(wynik), ["Zażółć gęślą jaźń"])


class TestDocxPdf(unittest.TestCase):
    def tearDown(self):
        ustaw_program_libreoffice(None)

    def _docx(self, katalog: Path) -> Path:
        zrodlo = katalog / "notatka test.txt"
        zrodlo.write_text("Zażółć gęślą jaźń\n\nDrugi akapit.\n", encoding="utf-8")
        return txt_na_docx(zrodlo, katalog)

    def test_brak_narzedzia(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            docx = self._docx(katalog)
            brak = katalog / "nie ma takiego" / "soffice.com"
            with self.assertRaises(RuntimeError) as ctx:
                docx_na_pdf_z_programem(docx, katalog, program=str(brak))
        komunikat = str(ctx.exception)
        self.assertIn("Nie znaleziono LibreOffice", komunikat)
        self.assertIn("LIBREOFFICE_PATH", komunikat)

    def test_uszkodzony_docx_nie_konczy_sie_sukcesem(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            zly = katalog / "uszkodzony.docx"
            zly.write_text("Zażółć gęślą jaźń", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                docx_na_pdf_z_programem(zly, katalog, program=str(katalog / "soffice.com"))
        self.assertIn("nie jest poprawnym dokumentem DOCX", str(ctx.exception))

    def test_limit_czasu_na_atrapie_procesu(self):
        with self.assertRaises(RuntimeError) as ctx:
            wywolaj_proces([sys.executable, "-c", "import time; time.sleep(30)"], 1)
        self.assertIn("Przekroczono czas konwersji (1 s)", str(ctx.exception))

    def test_lista_argumentow_bez_shell_i_ze_spacjami(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp) / "wynik ze spacjami"
            katalog.mkdir()
            docx = self._docx(katalog)
            atrapa = katalog / "soffice.com"
            atrapa.write_text("atrapa", encoding="utf-8")
            widziane = {}

            def fake_run(polecenie, shell=None, **kwargs):
                widziane["shell"] = shell
                widziane["polecenie"] = polecenie
                widziane["timeout"] = kwargs.get("timeout")
                self.assertIs(shell, False)
                self.assertIsInstance(polecenie, list)
                self.assertEqual(polecenie[0], str(atrapa))
                self.assertIn("--headless", polecenie)
                self.assertEqual(polecenie[polecenie.index("--convert-to") + 1], "pdf")
                self.assertEqual(polecenie[-1], str(docx.resolve()))
                self.assertIn(" ", polecenie[-1])
                self.assertFalse(polecenie[-1].startswith('"'))
                outdir = Path(polecenie[polecenie.index("--outdir") + 1])
                pdf = outdir / f"{docx.stem}.pdf"
                pdf.write_bytes(b"%PDF-1.4\n% konwersja testowa\n%%EOF\n")
                return subprocess.CompletedProcess(polecenie, 0, stdout="ok", stderr="")

            with patch("konwersja.docx_pdf.subprocess.run", side_effect=fake_run):
                wynik = docx_na_pdf_z_programem(docx, katalog, program=str(atrapa), limit_czasu=60)
            self.assertTrue(wynik.read_bytes().startswith(b"%PDF"))
            self.assertIs(widziane["shell"], False)
            self.assertEqual(widziane["timeout"], 60)

    def test_kod_zakonczenia_rozny_od_zera(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            docx = self._docx(katalog)
            atrapa = katalog / "soffice.com"
            atrapa.write_text("atrapa", encoding="utf-8")

            def fake_run(polecenie, shell=None, **kwargs):
                return subprocess.CompletedProcess(polecenie, 1, stdout="", stderr="uszkodzony dokument")

            with patch("konwersja.docx_pdf.subprocess.run", side_effect=fake_run):
                with self.assertRaises(RuntimeError) as ctx:
                    docx_na_pdf_z_programem(docx, katalog, program=str(atrapa))
        self.assertIn("zakończył się błędem", str(ctx.exception))
        self.assertIn("uszkodzony dokument", str(ctx.exception))

    def test_kod_zero_bez_pliku_pdf_nie_jest_sukcesem(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            docx = self._docx(katalog)
            atrapa = katalog / "soffice.com"
            atrapa.write_text("atrapa", encoding="utf-8")

            def fake_run(polecenie, shell=None, **kwargs):
                return subprocess.CompletedProcess(polecenie, 0, stdout="", stderr="")

            with patch("konwersja.docx_pdf.subprocess.run", side_effect=fake_run):
                with self.assertRaises(RuntimeError) as ctx:
                    docx_na_pdf_z_programem(docx, katalog, program=str(atrapa))
        self.assertIn("nie powstał niepusty plik PDF", str(ctx.exception))

    def test_odmowa_nadpisania_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            docx = self._docx(katalog)
            istniejacy = katalog / "notatka test.pdf"
            istniejacy.write_bytes(b"%PDF-stary")
            atrapa = katalog / "soffice.com"
            atrapa.write_text("atrapa", encoding="utf-8")
            with patch("konwersja.docx_pdf.subprocess.run") as uruchom:
                with self.assertRaises(FileExistsError):
                    docx_na_pdf_z_programem(docx, katalog, program=str(atrapa))
            uruchom.assert_not_called()

    @unittest.skipUnless(_libreoffice(), "Brak zainstalowanego LibreOffice")
    def test_rzeczywista_konwersja_libreoffice(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp) / "katalog ze spacjami"
            katalog.mkdir()
            docx = self._docx(katalog)
            wynik = docx_na_pdf_z_programem(docx, katalog, limit_czasu=120)
            dane = wynik.read_bytes()
            self.assertTrue(dane.startswith(b"%PDF"))
            self.assertGreater(len(dane), 500)
            self.assertIn(" ", str(wynik))


class TestProgramUruchamiajacy(unittest.TestCase):
    def tearDown(self):
        ustaw_program_libreoffice(None)

    def test_brak_programu_konczy_sie_kodem_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            zrodlo = katalog / "a.txt"
            zrodlo.write_text("Zażółć\n", encoding="utf-8")
            docx = txt_na_docx(zrodlo, katalog)
            bufor = io.StringIO()
            with redirect_stderr(bufor):
                kod = main(
                    [str(docx), "pdf", str(katalog), "--program", str(katalog / "brak" / "soffice.com")]
                )
        self.assertEqual(kod, 1)
        self.assertIn("Nie znaleziono LibreOffice", bufor.getvalue())
        self.assertNotIn("Traceback", bufor.getvalue())


if __name__ == "__main__":
    unittest.main()
