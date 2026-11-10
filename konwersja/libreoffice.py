"""Konwersje DOCX → PDF i ODT → PDF programem LibreOffice.

Narzędzie jest uruchamiane listą argumentów, z shell=False. Kod zakończenia 0
nie wystarcza: w katalogu musi powstać niepusty plik zaczynający się od %PDF.
"""

import os
import shutil
import subprocess
from pathlib import Path

from konwersja.rejestr import konwerter
from konwersja.walidacja import przygotuj_wynik, sprawdz_docx, sprawdz_odt

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

    for kandydat in (
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
        if kandydat.is_file():
            return str(kandydat)

    raise RuntimeError(
        "Brak LibreOffice. Zainstaluj pakiet LibreOffice albo ustaw zmienną "
        "LIBREOFFICE_PATH na pełną ścieżkę do soffice.com (Windows) lub soffice. "
        "Sam pakiet pip nie instaluje tego programu."
    )


def wywolaj_proces(polecenie: list[str], limit_czasu: int):
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


def _do_pdf(
    zrodlo: Path,
    katalog: Path,
    wejscie: str,
    sprawdz,
    program: str | None,
    limit_czasu: int,
) -> Path:
    cel = przygotuj_wynik(zrodlo, katalog, wejscie, ".pdf")
    sprawdz(zrodlo)
    polecenie = [
        znajdz_libreoffice(program),
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(katalog),
        str(zrodlo.resolve()),
    ]
    try:
        rezultat = wywolaj_proces(polecenie, limit_czasu)
        if rezultat.returncode != 0:
            szczegoly = (rezultat.stderr or rezultat.stdout or "").strip()
            komunikat = f"LibreOffice zakończył się błędem (kod {rezultat.returncode})"
            if szczegoly:
                komunikat += f": {szczegoly[:500]}"
            komunikat += ". Sprawdź, czy dokument otwiera się w edytorze."
            raise RuntimeError(komunikat)
        if not cel.is_file() or cel.stat().st_size == 0 or not cel.read_bytes().startswith(b"%PDF"):
            raise RuntimeError(
                "LibreOffice zakończył się kodem 0, ale nie powstał niepusty plik PDF. "
                "Zamknij otwarty LibreOffice i sprawdź, czy dokument nie jest uszkodzony."
            )
        return cel
    except Exception:
        cel.unlink(missing_ok=True)
        raise


@konwerter(".docx", ".pdf")
def docx_na_pdf(
    zrodlo: Path,
    katalog: Path,
    program: str | None = None,
    limit_czasu: int = LIMIT_CZASU_DOMYSLNY,
) -> Path:
    return _do_pdf(zrodlo, katalog, ".docx", sprawdz_docx, program, limit_czasu)


@konwerter(".odt", ".pdf")
def odt_na_pdf(
    zrodlo: Path,
    katalog: Path,
    program: str | None = None,
    limit_czasu: int = LIMIT_CZASU_DOMYSLNY,
) -> Path:
    return _do_pdf(zrodlo, katalog, ".odt", sprawdz_odt, program, limit_czasu)
