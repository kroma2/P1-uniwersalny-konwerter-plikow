"""Wspólne sprawdzenia wejścia i miejsca zapisu, używane przez wszystkie konwertery."""

import zipfile
from pathlib import Path

TYP_ODT = b"application/vnd.oasis.opendocument.text"


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
            "Program nie nadpisuje wyników bez zgody. Usuń ten plik albo wskaż inny katalog."
        )
    return cel


def _pliki_archiwum(sciezka: Path) -> set[str]:
    try:
        with zipfile.ZipFile(sciezka) as archiwum:
            return set(archiwum.namelist())
    except zipfile.BadZipFile:
        return set()


def sprawdz_docx(sciezka: Path) -> None:
    pliki = _pliki_archiwum(sciezka)
    if "[Content_Types].xml" not in pliki or "word/document.xml" not in pliki:
        raise ValueError(
            "Plik nie jest poprawnym dokumentem DOCX. "
            "Zmiana rozszerzenia nie tworzy dokumentu. Zapisz plik w edytorze jako DOCX."
        )


def sprawdz_odt(sciezka: Path) -> None:
    typ = b""
    pliki = _pliki_archiwum(sciezka)
    if "mimetype" in pliki:
        with zipfile.ZipFile(sciezka) as archiwum:
            typ = archiwum.read("mimetype").strip()
    if typ != TYP_ODT or "content.xml" not in pliki:
        raise ValueError(
            "Plik nie jest poprawnym dokumentem ODT. "
            "Zmiana rozszerzenia nie tworzy dokumentu. Zapisz plik w LibreOffice Writer jako ODT."
        )
