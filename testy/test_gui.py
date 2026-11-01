"""Testy okna: formaty zależne od pliku, blokada pary i pytanie o nadpisanie."""

import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gui import OknoKonwertera

DANE = ROOT / "dane"


class TestOkno(unittest.TestCase):
    def setUp(self):
        self.okno = OknoKonwertera()
        self.okno.withdraw()
        self.dialogi = []
        self.okno.pytanie_nadpisania = self._nie
        self.okno.informacja = lambda *args, **kwargs: self.dialogi.append(("info", args))
        self.okno.okno_bledu = lambda *args, **kwargs: self.dialogi.append(("blad", args))

    def tearDown(self):
        self._czekaj()
        self.okno.destroy()

    def _nie(self, *args, **kwargs):
        self.dialogi.append(("pytanie", args))
        return False

    def _tak(self, *args, **kwargs):
        self.dialogi.append(("pytanie", args))
        return True

    def _czekaj(self, limit: float = 5):
        koniec = time.time() + limit
        while time.time() < koniec and self.okno._pracuje:
            self.okno.update()
            time.sleep(0.02)
        self.okno.update()

    def test_formaty_zaleza_od_rozszerzenia(self):
        self.okno.ustaw_plik(DANE / "osoby.csv")
        self.assertEqual(self.okno.formaty_widoczne, (".json",))
        self.okno.ustaw_plik(DANE / "osoby.json")
        self.assertEqual(self.okno.formaty_widoczne, (".csv",))
        self.okno.ustaw_plik(DANE / "przyklad.txt")
        self.assertEqual(self.okno.formaty_widoczne, (".docx",))

    def test_nieobslugiwany_plik_nie_daje_formatu(self):
        with tempfile.TemporaryDirectory() as tmp:
            obcy = Path(tmp) / "obraz.png"
            obcy.write_bytes(b"nie dokument")
            self.okno.ustaw_plik(obcy)
            self.okno.ustaw_katalog(Path(tmp))
        self.assertEqual(self.okno.formaty_widoczne, ())
        self.assertTrue(self.okno.przycisk_konwertuj.instate(["disabled"]))
        self.okno.konwertuj()
        self.assertFalse(self.okno._pracuje)
        self.assertIn("nie zostanie uruchomiona", self.okno.status.get())

    def test_konwersja_csv_i_odmowa_nadpisania(self):
        with tempfile.TemporaryDirectory() as tmp:
            katalog = Path(tmp)
            self.okno.ustaw_plik(DANE / "osoby.csv")
            self.okno.ustaw_katalog(katalog)
            self.assertFalse(self.okno.przycisk_konwertuj.instate(["disabled"]))
            self.okno.konwertuj()
            self._czekaj()
            wynik = katalog / "osoby.json"
            self.assertTrue(wynik.is_file())
            self.assertEqual(json.loads(wynik.read_text(encoding="utf-8"))["wiersze"][0]["miasto"], "Łódź")
            self.assertTrue(any(rodzaj == "info" for rodzaj, _args in self.dialogi))

            self.okno.pytanie_nadpisania = self._nie
            self.okno.konwertuj()
            self.assertFalse(self.okno._pracuje)
            self.assertIn("bez zmian", self.okno.status.get())
            self.assertEqual(json.loads(wynik.read_text(encoding="utf-8"))["wiersze"][0]["miasto"], "Łódź")

            wynik.write_text("STARY", encoding="utf-8")
            self.okno.pytanie_nadpisania = self._tak
            self.okno.konwertuj()
            self._czekaj()
            self.assertEqual(json.loads(wynik.read_text(encoding="utf-8"))["wiersze"][0]["imię"], "Zosia")

    def test_watek_oddaje_sterowanie_oknu(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.okno.ustaw_plik(DANE / "osoby.csv")
            self.okno.ustaw_katalog(Path(tmp))
            wystartowal = threading.Event()

            def wolno(*_args, **_kwargs):
                wystartowal.set()
                time.sleep(0.3)
                return Path(tmp) / "osoby.json"

            with patch("gui.wykonaj", wolno):
                self.okno.konwertuj()
                self.assertTrue(wystartowal.wait(2))
                self.okno.update()
                self.assertIn("Trwa konwersja", self.okno.status.get())
                self._czekaj()
            self.assertIn("Zapisano", self.okno.status.get())


if __name__ == "__main__":
    unittest.main()
