"""Konwersja DOCX → PDF programem LibreOffice.

Narzędzie jest uruchamiane listą argumentów, z shell=False. Sukces procesu
(returncode == 0) nie wystarcza: wynik musi być nowym, niepustym plikiem PDF.
Konwersja idzie do pustego katalogu tymczasowego, a gotowy plik jest kopiowany
dopiero potem. Dzięki temu stary PDF nie zostanie uznany za nowy wynik.
"""

import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote

from konwersja.rejestr import konwerter, przygotuj_wynik

LIMIT_CZASU_DOMYSLNY = 60
_nadpisany_program: str | None = None


def ustaw_program_libreoffice(sciezka: str | None) -> None:
    """Ścieżka przekazana przez program uruchamiający, zanim wywoła konwerter."""
    global _nadpisany_program
    _nadpisany_program = sciezka


def znajdz_libreoffice(jawna_sciezka: str | None = None) -> str:
    """Zwraca ścieżkę do soffice.com / soffice albo opisuje, jak ją uzupełnić."""
    if jawna_sciezka is not None:
        kandydat = Path(jawna_sciezka)
        if not kandydat.is_file():
            raise RuntimeError(
                f"Nie znaleziono LibreOffice pod ścieżką: {jawna_sciezka}. "
                "Zainstaluj LibreOffice i wskaż plik program\\soffice.com "
                "(na Windows) albo ustaw zmienną środowiskową LIBREOFFICE_PATH."
            )
        return str(kandydat)

    # Ścieżka z --program ma pierwszeństwo przed zmienną środowiskową.
    if _nadpisany_program:
        return znajdz_libreoffice(_nadpisany_program)

    ze_srodowiska = os.environ.get("LIBREOFFICE_PATH")
    if ze_srodowiska:
        return znajdz_libreoffice(ze_srodowiska)

    znalezione = (
        shutil.which("soffice.com")
        or shutil.which("soffice")
        or shutil.which("libreoffice")
    )
    if znalezione:
        return znalezione

    for wzorzec in (
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "LibreOffice"
        / "program"
        / "soffice.com",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "LibreOffice"
        / "program"
        / "soffice.com",
        Path.home() / "AppData" / "Local" / "Programs" / "LibreOffice" / "program" / "soffice.com",
        Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
        Path("/usr/bin/libreoffice"),
        Path("/usr/bin/soffice"),
    ):
        if wzorzec.is_file():
            return str(wzorzec)

    raise RuntimeError(
        "Brak LibreOffice. Zainstaluj pakiet LibreOffice albo ustaw zmienną "
        "LIBREOFFICE_PATH na pełną ścieżkę do soffice.com (Windows) lub soffice. "
        "Sam pakiet pip nie instaluje tego programu."
    )


def _uri_katalogu(katalog: Path) -> str:
    posix = katalog.resolve().as_posix()
    return "file:///" + quote(posix, safe="/:")


def _czy_docx(sciezka: Path) -> bool:
    if not zipfile.is_zipfile(sciezka):
        return False
    try:
        with zipfile.ZipFile(sciezka) as archiwum:
            nazwy = set(archiwum.namelist())
    except zipfile.BadZipFile:
        return False
    return "[Content_Types].xml" in nazwy and "word/document.xml" in nazwy


def wywolaj_proces(polecenie: list[str], limit_czasu: int) -> subprocess.CompletedProcess[str]:
    """Uruchamia proces bez powłoki i tłumaczy typowe awarie na czytelny komunikat."""
    try:
        return subprocess.run(
            polecenie,
            shell=False,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=limit_czasu,
        )
    except FileNotFoundError as blad:
        raise RuntimeError(
            "Nie udało się uruchomić LibreOffice. Sprawdź ścieżkę do soffice.com "
            "albo zmienną LIBREOFFICE_PATH."
        ) from blad
    except subprocess.TimeoutExpired as blad:
        raise RuntimeError(
            f"Przekroczono czas konwersji ({limit_czasu} s). "
            "Zamknij inne okna LibreOffice i spróbuj ponownie."
        ) from blad
    except OSError as blad:
        raise RuntimeError(
            f"Nie można uruchomić LibreOffice ({blad}). Sprawdź instalację i uprawnienia do pliku programu."
        ) from blad


def _konwersja_w_katalogu(
    zrodlo: Path,
    katalog_roboczy: Path,
    program: str,
    limit_czasu: int,
) -> Path:
    profil = katalog_roboczy / "profil"
    wynik = katalog_roboczy / "wynik"
    profil.mkdir()
    wynik.mkdir()
    polecenie = [
        program,
        f"-env:UserInstallation={_uri_katalogu(profil)}",
        "--headless",
        "--norestore",
        "--nolockcheck",
        "--convert-to",
        "pdf",
        "--outdir",
        str(wynik),
        str(zrodlo.resolve()),
    ]
    rezultat = wywolaj_proces(polecenie, limit_czasu)
    cel = wynik / f"{zrodlo.stem}.pdf"
    if rezultat.returncode != 0:
        szczegoly = (rezultat.stderr or rezultat.stdout or "").strip()
        komunikat = "LibreOffice zakończył się błędem"
        if szczegoly:
            komunikat += f": {szczegoly[:500]}"
        komunikat += ". Sprawdź, czy plik DOCX otwiera się w edytorze."
        raise RuntimeError(komunikat)
    if not cel.is_file() or cel.stat().st_size == 0 or not cel.read_bytes().startswith(b"%PDF"):
        raise RuntimeError(
            "LibreOffice zakończył się kodem 0, ale nie powstał niepusty plik PDF. "
            "Zamknij otwarty LibreOffice i sprawdź, czy dokument DOCX nie jest uszkodzony."
        )
    return cel


def _kopiuj_bez_nadpisania(zrodlo: Path, cel: Path) -> None:
    try:
        with zrodlo.open("rb") as wejscie, cel.open("xb") as wyjscie:
            shutil.copyfileobj(wejscie, wyjscie)
    except FileExistsError as blad:
        raise FileExistsError(
            f"Plik wynikowy już istnieje: {cel}. "
            "Program nie nadpisuje wyników. Usuń ten plik albo wskaż inny katalog."
        ) from blad
    except Exception:
        cel.unlink(missing_ok=True)
        raise


@konwerter(".docx", ".pdf")
def docx_na_pdf(zrodlo: Path, katalog: Path) -> Path:
    return docx_na_pdf_z_programem(zrodlo, katalog)


def docx_na_pdf_z_programem(
    zrodlo: Path,
    katalog: Path,
    program: str | None = None,
    limit_czasu: int = LIMIT_CZASU_DOMYSLNY,
) -> Path:
    cel = przygotuj_wynik(zrodlo, katalog, ".docx", ".pdf")
    if not _czy_docx(zrodlo):
        raise ValueError(
            "Plik nie jest poprawnym dokumentem DOCX. "
            "Zmiana rozszerzenia nie tworzy dokumentu. Zapisz plik w edytorze jako DOCX."
        )
    narzedzie = znajdz_libreoffice(program)
    with TemporaryDirectory(prefix="konwerter-pdf-") as tymczasowy:
        pdf = _konwersja_w_katalogu(zrodlo, Path(tymczasowy), narzedzie, limit_czasu)
        _kopiuj_bez_nadpisania(pdf, cel)
    return cel
