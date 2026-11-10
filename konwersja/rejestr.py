"""Rejestr kierunków konwersji, oddzielony od sposobu uruchomienia."""

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

log = logging.getLogger(__name__)

REJESTR: dict[tuple[str, str]] = {}


def konwerter(wejscie: str, wyjscie: str):
    """Rejestruje funkcję jako jedyny konwerter pary rozszerzeń."""

    def zarejestruj(funkcja):
        REJESTR[(wejscie.lower(), wyjscie.lower())] = funkcja
        return funkcja

    return zarejestruj


def pary() -> list[tuple[str, str]]:
    return sorted(REJESTR)


def dostepne_formaty(zrodlo: Path) -> list[str]:
    rozszerzenie = zrodlo.suffix.lower()
    return sorted(wyjscie for (wejscie, wyjscie) in REJESTR if wejscie == rozszerzenie)


def _format(nazwa: str) -> str:
    nazwa = nazwa.strip().lower()
    if not nazwa.startswith("."):
        nazwa = "." + nazwa
    return nazwa


@dataclass(frozen=True)
class ZlecenieKonwersji:
    zrodlo: Path
    format_docelowy: str
    katalog: Path

    def klucz(self) -> tuple[str, str]:
        return (self.zrodlo.suffix.lower(), _format(self.format_docelowy))

    def plik_wynikowy(self) -> Path:
        return self.katalog / f"{self.zrodlo.stem}{self.klucz()[1]}"

    def sprawdz(self) -> None:
        if not self.zrodlo.is_file():
            raise FileNotFoundError(
                f"Brak pliku wejściowego: {self.zrodlo}. Wskaż istniejący plik."
            )
        if not self.katalog.is_dir():
            raise NotADirectoryError(
                f"Brak katalogu wynikowego: {self.katalog}. Utwórz go i uruchom polecenie ponownie."
            )
        if not os.access(self.katalog, os.W_OK):
            raise PermissionError(
                f"Brak uprawnień do zapisu w katalogu: {self.katalog}. Wybierz inny katalog."
            )
        klucz = self.klucz()
        if klucz not in REJESTR:
            dostepne = dostepne_formaty(self.zrodlo)
            if dostepne:
                podpowiedz = "Dostępne formaty dla tego pliku: " + ", ".join(dostepne) + "."
            else:
                podpowiedz = "Dla tego rozszerzenia nie ma żadnego konwertera."
            raise ValueError(
                f"Nieobsługiwana konwersja {klucz[0]} -> {klucz[1]}. {podpowiedz}"
            )


def _zastap(funkcja, zlecenie: ZlecenieKonwersji, cel: Path) -> Path:
    """Tworzy wynik obok starego i podmienia go dopiero po udanej konwersji."""
    with TemporaryDirectory(dir=zlecenie.katalog, prefix=".konwersja-") as tymczasowy:
        nowy = funkcja(zlecenie.zrodlo, Path(tymczasowy))
        os.replace(nowy, cel)
    return cel


def wykonaj(zlecenie: ZlecenieKonwersji, nadpisz: bool = False) -> Path:
    """Uruchamia konwerter pary. Istniejący wynik jest zastępowany tylko przy nadpisz=True."""
    poczatek = time.perf_counter()
    opis = f"{zlecenie.zrodlo} -> {zlecenie.format_docelowy}"
    try:
        zlecenie.sprawdz()
        funkcja = REJESTR[zlecenie.klucz()]
        cel = zlecenie.plik_wynikowy()
        if nadpisz and cel.exists():
            wynik = _zastap(funkcja, zlecenie, cel)
        else:
            wynik = funkcja(zlecenie.zrodlo, zlecenie.katalog)
    except PermissionError as blad:
        if blad.filename is None:
            log.warning("Nieudana konwersja %s: %s", opis, blad)
            raise
        komunikat = (
            f"Brak dostępu do pliku: {blad.filename}. "
            "Zamknij go w innym programie albo wybierz inny katalog."
        )
        log.warning("Nieudana konwersja %s: %s", opis, komunikat)
        raise PermissionError(komunikat) from blad
    except (OSError, ValueError, RuntimeError) as blad:
        log.warning("Nieudana konwersja %s: %s", opis, blad)
        raise
    except Exception:
        log.exception("Nieoczekiwany błąd konwersji %s", opis)
        raise
    log.info("Zapisano %s w %.2f s", wynik, time.perf_counter() - poczatek)
    return wynik
