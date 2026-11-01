"""Testy konwerterów, rejestru i kontroli procesu LibreOffice."""

import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from konwersja import zaladuj_konwertery

zaladuj_konwertery()

from konwersja.csv_json import csv_na_json, json_na_csv
from konwersja.libreoffice import (
    docx_na_pdf,
    odt_na_pdf,
    ustaw_program_libreoffice,
    wywolaj_proces,
    znajdz_libreoffice,
)
from konwersja.rejestr import ZlecenieKonwersji, dostepne_formaty, pary, wykonaj
from konwersja.txt_docx import akapity, docx_na_txt, txt_na_docx
from main import main

DANE = ROOT / "dane"
TEKST_PRZYKLADU = ["Zażółć gęślą jaźń", "", "Drugi akapit: Łódź, Gdańsk i Kraków."]


def _libreoffice():
    try:
        return znajdz_libreoffice()
    except RuntimeError:
        return None


def _atrapa_programu(katalog: Path) -> Path:
    atrapa = katalog / "soffice.com"
    atrapa.write_text("atrapa", encoding="utf-8")
    return atrapa


class TestRejestr(unittest.TestCase):
    def tearDown(self):
        ustaw_program_libreoffice(None)

    def test_szesc_kierunkow_z_trzech_grup(self):
        self.assertEqual(
            pary(),
            [
                (".csv", ".json"),
                (".docx", ".pdf"),
                (".docx", ".txt"),
                (".json", ".csv"),
                (".odt", ".pdf"),
                (".txt", ".docx"),
            ],
        )

    def test_dostepne_formaty_zaleza_od_rozszerzenia(self):
        self.assertEqual(dostepne_formaty(DANE / "osoby.csv"), [".json"])
        self.assertEqual(dostepne_formaty(DANE / "osoby.json"), [".csv"])
        self.assertEqual(dostepne_formaty(DANE / "przyklad.txt"), [".docx"])
        self.assertEqual(dostepne_formaty(DANE / "przyklad.docx"), [".pdf", ".txt"])
        self.assertEqual(dostepne_formaty(DANE / "przyklad.odt"), [".pdf"])
        self.assertEqual(dostepne_formaty(Path("obraz.png")), [])

    def test_nieobslugiwana_para(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            zrodlo = katalog / "notatka.txt"
            zrodlo.write_text("abc", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                wykonaj(ZlecenieKonwersji(zrodlo, "pdf", katalog))
            self.assertIn("Nieobsługiwana konwersja", str(ctx.exception))
            self.assertIn(".docx", str(ctx.exception))
            self.assertEqual(list(katalog.glob("*.pdf")), [])

    def test_brak_pliku_i_katalogu(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            with self.assertRaises(FileNotFoundError):
                wykonaj(ZlecenieKonwersji(katalog / "brak.csv", "json", katalog))
            with self.assertRaises(NotADirectoryError):
                wykonaj(ZlecenieKonwersji(DANE / "osoby.csv", "json", katalog / "brak"))

    def test_istniejacy_wynik_bez_zgody_zostaje(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            cel = katalog / "osoby.json"
            cel.write_text("STARY", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                wykonaj(ZlecenieKonwersji(DANE / "osoby.csv", "json", katalog))
            self.assertEqual(cel.read_text(encoding="utf-8"), "STARY")

    def test_nadpisanie_za_zgoda_podmienia_plik(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            cel = katalog / "osoby.json"
            cel.write_text("STARY", encoding="utf-8")
            wynik = wykonaj(ZlecenieKonwersji(DANE / "osoby.csv", "json", katalog), nadpisz=True)
            self.assertEqual(wynik, cel)
            self.assertEqual(json.loads(cel.read_text(encoding="utf-8"))["wiersze"][0]["miasto"], "Łódź")
            self.assertEqual(sorted(p.name for p in katalog.iterdir()), ["osoby.json"])

    def test_nieudane_nadpisanie_zostawia_stary_plik(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            cel = katalog / "zly.csv"
            cel.write_text("STARY", encoding="utf-8")
            with self.assertRaises(ValueError):
                wykonaj(
                    ZlecenieKonwersji(DANE / "bledne" / "zly.json", "csv", katalog),
                    nadpisz=True,
                )
            self.assertEqual(cel.read_text(encoding="utf-8"), "STARY")
            self.assertEqual(sorted(p.name for p in katalog.iterdir()), ["zly.csv"])

    def test_blad_i_sukces_trafiaja_do_logu(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            with self.assertLogs("konwersja.rejestr", level="INFO") as logi:
                wykonaj(ZlecenieKonwersji(DANE / "osoby.csv", "json", katalog))
                with self.assertRaises(ValueError):
                    wykonaj(ZlecenieKonwersji(DANE / "bledne" / "zly.json", "csv", katalog))
        tekst = "\n".join(logi.output)
        self.assertIn("INFO:konwersja.rejestr:Zapisano", tekst)
        self.assertIn("WARNING:konwersja.rejestr:Nieudana konwersja", tekst)
        self.assertIn("Niepoprawny JSON", tekst)


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
                        "kolumny": ["miasto", "imię", "wiek", "aktywny", "uwagi"],
                        "wiersze": [
                            {"imię": "Jaźń", "miasto": "Łódź", "wiek": 7, "aktywny": True, "uwagi": None, "inne": "x"}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            wynik = json_na_csv(zrodlo, katalog)
            tresc = wynik.read_text(encoding="utf-8")
        self.assertEqual(tresc.splitlines(), ["miasto,imię,wiek,aktywny,uwagi", "Łódź,Jaźń,7,true,"])

    def test_obie_strony_daja_te_same_wiersze(self):
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
            with self.assertRaises(ValueError) as ctx:
                json_na_csv(DANE / "bledne" / "zly.json", Path(tmp))
            self.assertEqual(list(Path(tmp).iterdir()), [])
        self.assertIn("Niepoprawny JSON", str(ctx.exception))

    def test_zagniezdzona_wartosc_json_jest_odrzucana(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            zrodlo = katalog / "zagniezdzony.json"
            zrodlo.write_text(
                json.dumps({"kolumny": ["a"], "wiersze": [{"a": {"b": 1}}]}), encoding="utf-8"
            )
            with self.assertRaises(ValueError) as ctx:
                json_na_csv(zrodlo, katalog)
        self.assertIn("obiekt albo listę", str(ctx.exception))

    def test_csv_z_nadmiarowym_polem_i_powtorzona_kolumna(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            nadmiar = katalog / "nadmiar.csv"
            nadmiar.write_text("a,b\n1,2,3\n", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                csv_na_json(nadmiar, katalog)
            self.assertIn("więcej pól niż nagłówek", str(ctx.exception))

            powtorzona = katalog / "powtorzona.csv"
            powtorzona.write_text("a,a\n1,2\n", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                csv_na_json(powtorzona, katalog)
            self.assertIn("powtórzoną nazwę kolumny", str(ctx.exception))

    def test_csv_bez_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            zrodlo = katalog / "cp1250.csv"
            zrodlo.write_bytes("miasto\nŁódź\n".encode("cp1250"))
            with self.assertRaises(ValueError) as ctx:
                csv_na_json(zrodlo, katalog)
        self.assertIn("UTF-8", str(ctx.exception))


class TestTxtDocx(unittest.TestCase):
    def test_linie_akapity_i_polskie_znaki(self):
        with tempfile.TemporaryDirectory() as tmp:
            wynik = txt_na_docx(DANE / "przyklad.txt", Path(tmp))
            self.assertEqual(akapity(wynik), TEKST_PRZYKLADU)

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

    def test_docx_na_txt_odtwarza_tekst(self):
        with tempfile.TemporaryDirectory() as tmp:
            wynik = docx_na_txt(DANE / "przyklad.docx", Path(tmp))
            self.assertEqual(
                wynik.read_text(encoding="utf-8"),
                (DANE / "przyklad.txt").read_text(encoding="utf-8"),
            )

    def test_docx_na_txt_odrzuca_uszkodzony_plik(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as ctx:
                docx_na_txt(DANE / "bledne" / "uszkodzony.docx", Path(tmp))
            self.assertEqual(list(Path(tmp).iterdir()), [])
        self.assertIn("nie jest poprawnym dokumentem DOCX", str(ctx.exception))

    def test_brak_biblioteki_python_docx(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(sys.modules, {"docx": None}):
                with self.assertRaises(RuntimeError) as ctx:
                    txt_na_docx(DANE / "przyklad.txt", Path(tmp))
        self.assertIn("Brak biblioteki python-docx", str(ctx.exception))
        self.assertIn("requirements.txt", str(ctx.exception))


class TestLibreOffice(unittest.TestCase):
    def tearDown(self):
        ustaw_program_libreoffice(None)

    def test_brak_narzedzia(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            brak = katalog / "nie ma takiego" / "soffice.com"
            with self.assertRaises(RuntimeError) as ctx:
                docx_na_pdf(DANE / "przyklad.docx", katalog, program=str(brak))
        komunikat = str(ctx.exception)
        self.assertIn("Nie znaleziono LibreOffice", komunikat)
        self.assertIn("LIBREOFFICE_PATH", komunikat)

    def test_uszkodzony_docx_nie_konczy_sie_sukcesem(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            with patch("konwersja.libreoffice.subprocess.run") as uruchom:
                with self.assertRaises(ValueError) as ctx:
                    docx_na_pdf(
                        DANE / "bledne" / "uszkodzony.docx", katalog, program=str(_atrapa_programu(katalog))
                    )
            uruchom.assert_not_called()
        self.assertIn("nie jest poprawnym dokumentem DOCX", str(ctx.exception))

    def test_uszkodzony_odt_nie_konczy_sie_sukcesem(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            zly = katalog / "uszkodzony.odt"
            zly.write_text("Zażółć gęślą jaźń", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                odt_na_pdf(zly, katalog, program=str(_atrapa_programu(katalog)))
        self.assertIn("nie jest poprawnym dokumentem ODT", str(ctx.exception))

    def test_docx_przemianowany_na_odt_jest_odrzucany(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            podrobka = katalog / "podrobka.odt"
            podrobka.write_bytes((DANE / "przyklad.docx").read_bytes())
            with self.assertRaises(ValueError):
                odt_na_pdf(podrobka, katalog, program=str(_atrapa_programu(katalog)))

    def test_limit_czasu_na_atrapie_procesu(self):
        with self.assertRaises(RuntimeError) as ctx:
            wywolaj_proces([sys.executable, "-c", "import time; time.sleep(30)"], 1)
        self.assertIn("Przekroczono czas konwersji (1 s)", str(ctx.exception))

    def test_lista_argumentow_bez_shell_i_ze_spacjami(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp) / "wynik ze spacjami"
            katalog.mkdir()
            docx = katalog / "notatka test.docx"
            docx.write_bytes((DANE / "przyklad.docx").read_bytes())
            atrapa = _atrapa_programu(katalog)
            widziane = {}

            def fake_run(polecenie, shell=None, **kwargs):
                widziane["shell"] = shell
                widziane["timeout"] = kwargs.get("timeout")
                self.assertIsInstance(polecenie, list)
                self.assertEqual(polecenie[0], str(atrapa))
                self.assertIn("--headless", polecenie)
                self.assertEqual(polecenie[polecenie.index("--convert-to") + 1], "pdf")
                self.assertEqual(polecenie[-1], str(docx.resolve()))
                self.assertIn(" ", polecenie[-1])
                self.assertFalse(polecenie[-1].startswith('"'))
                outdir = Path(polecenie[polecenie.index("--outdir") + 1])
                (outdir / f"{docx.stem}.pdf").write_bytes(b"%PDF-1.4\n% konwersja testowa\n%%EOF\n")
                return subprocess.CompletedProcess(polecenie, 0, stdout="ok", stderr="")

            with patch("konwersja.libreoffice.subprocess.run", side_effect=fake_run):
                wynik = docx_na_pdf(docx, katalog, program=str(atrapa), limit_czasu=60)
            self.assertTrue(wynik.read_bytes().startswith(b"%PDF"))
        self.assertIs(widziane["shell"], False)
        self.assertEqual(widziane["timeout"], 60)

    def test_kod_zakonczenia_rozny_od_zera(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)

            def fake_run(polecenie, shell=None, **kwargs):
                return subprocess.CompletedProcess(polecenie, 1, stdout="", stderr="uszkodzony dokument")

            with patch("konwersja.libreoffice.subprocess.run", side_effect=fake_run):
                with self.assertRaises(RuntimeError) as ctx:
                    docx_na_pdf(DANE / "przyklad.docx", katalog, program=str(_atrapa_programu(katalog)))
            self.assertEqual(list(katalog.glob("*.pdf")), [])
        self.assertIn("zakończył się błędem (kod 1)", str(ctx.exception))
        self.assertIn("uszkodzony dokument", str(ctx.exception))

    def test_kod_zero_bez_pliku_pdf_nie_jest_sukcesem(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)

            def fake_run(polecenie, shell=None, **kwargs):
                return subprocess.CompletedProcess(polecenie, 0, stdout="", stderr="")

            with patch("konwersja.libreoffice.subprocess.run", side_effect=fake_run):
                with self.assertRaises(RuntimeError) as ctx:
                    docx_na_pdf(DANE / "przyklad.docx", katalog, program=str(_atrapa_programu(katalog)))
        self.assertIn("nie powstał niepusty plik PDF", str(ctx.exception))

    def test_odmowa_nadpisania_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            (katalog / "przyklad.pdf").write_bytes(b"%PDF-stary")
            with patch("konwersja.libreoffice.subprocess.run") as uruchom:
                with self.assertRaises(FileExistsError):
                    docx_na_pdf(DANE / "przyklad.docx", katalog, program=str(_atrapa_programu(katalog)))
            uruchom.assert_not_called()

    @unittest.skipUnless(_libreoffice(), "Brak zainstalowanego LibreOffice")
    def test_rzeczywista_konwersja_docx_i_odt(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp) / "katalog ze spacjami"
            katalog.mkdir()
            docx = katalog / "notatka test.docx"
            docx.write_bytes((DANE / "przyklad.docx").read_bytes())
            for wynik in (
                docx_na_pdf(docx, katalog, limit_czasu=120),
                odt_na_pdf(DANE / "przyklad.odt", katalog, limit_czasu=120),
            ):
                dane = wynik.read_bytes()
                self.assertTrue(dane.startswith(b"%PDF"))
                self.assertGreater(len(dane), 500)


class TestProgramUruchamiajacy(unittest.TestCase):
    def tearDown(self):
        ustaw_program_libreoffice(None)

    def test_brak_programu_konczy_sie_kodem_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            bufor = io.StringIO()
            with redirect_stderr(bufor):
                kod = main(
                    [
                        str(DANE / "przyklad.docx"),
                        "pdf",
                        str(katalog),
                        "--program",
                        str(katalog / "brak" / "soffice.com"),
                    ]
                )
        self.assertEqual(kod, 1)
        self.assertIn("Nie znaleziono LibreOffice", bufor.getvalue())
        self.assertNotIn("Traceback", bufor.getvalue())

    def test_opcja_nadpisz(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            (katalog / "osoby.json").write_text("STARY", encoding="utf-8")
            argumenty = [str(DANE / "osoby.csv"), "json", str(katalog)]
            with redirect_stderr(io.StringIO()) as bledy:
                self.assertEqual(main(argumenty), 1)
            self.assertIn("już istnieje", bledy.getvalue())
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main([*argumenty, "--nadpisz"]), 0)
            self.assertIn("Łódź", (katalog / "osoby.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
