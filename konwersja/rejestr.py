"""Rejestr kierunków konwersji, oddzielony od sposobu uruchomienia."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

Konwerter = Callable[[Path, Path], Path]
REJESTR: dict[tuple[str, str], Konwerter] = {}


def konwerter(wejscie: str, wyjscie: str):
    """Rejestruje funkcję jako jedyny konwerter pary rozszerzeń."""

    def zarejestruj(funkcja: Konwerter) -> Konwerter:
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

    def sprawdz(self) -> None:
        if not self.zrodlo.is_file():
            raise FileNotFoundError(
                f"Brak pliku wejściowego: {self.zrodlo}. Wskaż istniejący plik."
            )
        if not self.katalog.is_dir():
            raise NotADirectoryError(
                f"Brak katalogu wynikowego: {self.katalog}. Utwórz go i uruchom polecenie ponownie."
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


def wykonaj(zlecenie: ZlecenieKonwersji) -> Path:
    zlecenie.sprawdz()
    return REJESTR[zlecenie.klucz()](zlecenie.zrodlo, zlecenie.katalog)


def przygotuj_wynik(
    zrodlo: Path,
    katalog: Path,
    oczekiwane_wejscie: str,
    rozszerzenie_wyniku: str,
) -> Path:
    """Sprawdza plik i katalog oraz odmawia nadpisania istniejącego wyniku."""
    if not zrodlo.is_file():
        raise FileNotFoundError(
            f"Brak pliku wejściowego: {zrodlo}. Wskaż istniejący plik."
        )
    if zrodlo.suffix.lower() != oczekiwane_wejscie:
        otrzymane = zrodlo.suffix or "bez rozszerzenia"
        raise ValueError(
            f"Oczekiwano pliku {oczekiwane_wejscie}, otrzymano {otrzymane}. "
            "Wybierz zgodną parę formatów."
        )
    if not katalog.is_dir():
        raise NotADirectoryError(
            f"Brak katalogu wynikowego: {katalog}. Utwórz go i uruchom polecenie ponownie."
        )
    cel = katalog / f"{zrodlo.stem}{rozszerzenie_wyniku}"
    if cel.exists():
        raise FileExistsError(
            f"Plik wynikowy już istnieje: {cel}. "
            "Program nie nadpisuje wyników. Usuń ten plik albo wskaż inny katalog."
        )
    return cel
