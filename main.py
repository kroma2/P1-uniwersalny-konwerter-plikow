"""Uruchamia konwersje z wiersza poleceń albo, bez argumentów, okno programu."""

import argparse
import importlib.metadata
import sys
from pathlib import Path

from konwersja import konfiguruj_logi, zaladuj_konwertery
from konwersja.libreoffice import ustaw_program_libreoffice, znajdz_libreoffice
from konwersja.rejestr import ZlecenieKonwersji, pary, wykonaj


def _opisz_srodowisko() -> str:
    linie = [f"Python {sys.version.split()[0]}"]
    try:
        linie.append("python-docx " + importlib.metadata.version("python-docx"))
    except importlib.metadata.PackageNotFoundError:
        linie.append("python-docx: brak. Zainstaluj zależności: python -m pip install -r requirements.txt")
    try:
        linie.append("LibreOffice: " + znajdz_libreoffice())
    except RuntimeError as blad:
        linie.append(f"LibreOffice: {blad}")
    return "\n".join(linie)


def zbuduj_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Uniwersalny konwerter plików. Bez argumentów otwiera okno."
    )
    parser.add_argument("zrodlo", nargs="?", type=Path, help="Plik wejściowy")
    parser.add_argument("format", nargs="?", help="Format wynikowy, np. json, csv, docx, txt, pdf")
    parser.add_argument("katalog", nargs="?", type=Path, help="Istniejący katalog na wynik")
    parser.add_argument(
        "--nadpisz",
        action="store_true",
        help="Zastąp istniejący plik wynikowy. Bez tej opcji program odmawia nadpisania.",
    )
    parser.add_argument(
        "--program",
        help="Pełna ścieżka do soffice.com albo soffice. Nadpisuje LIBREOFFICE_PATH.",
    )
    parser.add_argument("--macierz", action="store_true", help="Wypisz obsługiwane pary i zakończ")
    parser.add_argument(
        "--srodowisko",
        action="store_true",
        help="Wypisz wersję Pythona, python-docx i ścieżkę LibreOffice",
    )
    return parser


def main(argumenty: list[str] | None = None) -> int:
    zaladuj_konwertery()
    parser = zbuduj_parser()
    args = parser.parse_args(argumenty)
    if args.program is not None:
        ustaw_program_libreoffice(args.program)

    if args.macierz:
        for wejscie, wyjscie in pary():
            print(f"{wejscie} -> {wyjscie}")
        return 0
    if args.srodowisko:
        print(_opisz_srodowisko())
        return 0
    if args.zrodlo is None or args.format is None or args.katalog is None:
        parser.error("Podaj plik, format i katalog albo użyj --macierz / --srodowisko.")

    try:
        wynik = wykonaj(
            ZlecenieKonwersji(args.zrodlo, args.format, args.katalog),
            nadpisz=args.nadpisz,
        )
    except (OSError, ValueError, RuntimeError) as blad:
        print(f"Błąd: {blad}", file=sys.stderr)
        return 1
    print(f"Zapisano: {wynik}")
    return 0


if __name__ == "__main__":
    konfiguruj_logi()
    if len(sys.argv) == 1:
        from gui import uruchom

        uruchom()
    else:
        raise SystemExit(main())
