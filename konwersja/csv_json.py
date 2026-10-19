import csv
import json
from pathlib import Path


def csv_na_json(sciezka_csv: Path, sciezka_json: Path) -> None:
    with sciezka_csv.open(encoding="utf-8-sig", newline="") as plik:
        czytnik = csv.DictReader(plik)
        if not czytnik.fieldnames:
            raise ValueError("plik CSV nie zawiera naglowkow.")
        kolumny = list(czytnik.fieldnames)
        wiersze = [dict(wiersz) for wiersz in czytnik]

    dane = {"kolumny": kolumny, "wiersze": wiersze}
    tekst = json.dumps(dane, ensure_ascii=False, indent=2)
    sciezka_json.write_text(tekst, encoding="utf-8")


if __name__ == "__main__":
    katalog = Path(__file__).resolve().parent.parent
    csv_na_json(katalog / "dane" / "osoby.csv", katalog / "dane" / "osoby.json")
    print("zapisano dane/osoby.json")