"""Konwersje CSV ↔ JSON.

Przyjęta struktura JSON to obiekt z dwoma kluczami:
- kolumny: lista nazw kolumn w kolejności z nagłówka CSV,
- wiersze: lista obiektów; klucze pochodzą z nagłówka, brak wartości to pusty napis.

Kodowanie plików to UTF-8. Przy odczycie dopuszczalny jest znacznik BOM.
"""

import csv
import json
from pathlib import Path

from konwersja.rejestr import konwerter
from konwersja.walidacja import przygotuj_wynik


def _odczytaj_csv(zrodlo: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with zrodlo.open(encoding="utf-8-sig", newline="") as plik:
            czytnik = csv.DictReader(plik)
            if not czytnik.fieldnames:
                raise ValueError(
                    "Plik CSV nie zawiera nagłówków. Dodaj wiersz z nazwami kolumn."
                )
            kolumny = list(czytnik.fieldnames)
            if any(nazwa == "" for nazwa in kolumny):
                raise ValueError(
                    "Nagłówek CSV zawiera pustą nazwę kolumny. Uzupełnij nagłówki."
                )
            if len(set(kolumny)) != len(kolumny):
                raise ValueError(
                    "Nagłówek CSV zawiera powtórzoną nazwę kolumny. Nadaj kolumnom różne nazwy."
                )
            wiersze = []
            for wiersz in czytnik:
                if None in wiersz:
                    raise ValueError(
                        f"Wiersz {czytnik.line_num} ma więcej pól niż nagłówek. "
                        "Popraw separatory albo dodaj brakujące kolumny."
                    )
                wiersze.append(
                    {klucz: "" if wartosc is None else wartosc for klucz, wartosc in wiersz.items()}
                )
    except UnicodeDecodeError as blad:
        raise ValueError(
            "Plik CSV nie jest zapisany w UTF-8. Zapisz go jako UTF-8 i spróbuj ponownie."
        ) from blad
    return kolumny, wiersze


@konwerter(".csv", ".json")
def csv_na_json(zrodlo: Path, katalog: Path) -> Path:
    cel = przygotuj_wynik(zrodlo, katalog, ".csv", ".json")
    kolumny, wiersze = _odczytaj_csv(zrodlo)
    dane = {"kolumny": kolumny, "wiersze": wiersze}
    tekst = json.dumps(dane, ensure_ascii=False, indent=2)
    cel.write_text(tekst + "\n", encoding="utf-8")
    return cel


def _odczytaj_json(zrodlo: Path) -> tuple[list[str], list[dict]]:
    try:
        tresc = zrodlo.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as blad:
        raise ValueError(
            "Plik JSON nie jest zapisany w UTF-8. Zapisz go jako UTF-8 i spróbuj ponownie."
        ) from blad
    try:
        dane = json.loads(tresc)
    except json.JSONDecodeError as blad:
        raise ValueError(
            f"Niepoprawny JSON ({blad.msg}, wiersz {blad.lineno}). Popraw składnię pliku."
        ) from blad
    if not isinstance(dane, dict) or "kolumny" not in dane or "wiersze" not in dane:
        raise ValueError(
            "JSON musi być obiektem z kluczami 'kolumny' i 'wiersze'. "
            "Użyj pliku powstałego z CSV albo dopasuj strukturę."
        )
    kolumny = dane["kolumny"]
    wiersze = dane["wiersze"]
    if (
        not isinstance(kolumny, list)
        or not kolumny
        or not all(isinstance(nazwa, str) and nazwa for nazwa in kolumny)
    ):
        raise ValueError("Pole 'kolumny' musi być niepustą listą niepustych napisów.")
    if not isinstance(wiersze, list) or not all(isinstance(wiersz, dict) for wiersz in wiersze):
        raise ValueError("Pole 'wiersze' musi być listą obiektów.")
    for numer, wiersz in enumerate(wiersze, start=1):
        for nazwa in kolumny:
            if isinstance(wiersz.get(nazwa), (dict, list)):
                raise ValueError(
                    f"Wiersz {numer}, kolumna '{nazwa}' zawiera obiekt albo listę. "
                    "CSV przyjmuje tylko proste wartości: tekst, liczby, true/false lub null."
                )
    return kolumny, wiersze


def _komorka(wartosc: object) -> str:
    if wartosc is None:
        return ""
    if isinstance(wartosc, bool):
        return "true" if wartosc else "false"
    return str(wartosc)


@konwerter(".json", ".csv")
def json_na_csv(zrodlo: Path, katalog: Path) -> Path:
    cel = przygotuj_wynik(zrodlo, katalog, ".json", ".csv")
    kolumny, wiersze = _odczytaj_json(zrodlo)
    with cel.open("w", encoding="utf-8", newline="") as plik:
        writer = csv.writer(plik)
        writer.writerow(kolumny)
        for wiersz in wiersze:
            writer.writerow([_komorka(wiersz.get(nazwa)) for nazwa in kolumny])
    return cel
