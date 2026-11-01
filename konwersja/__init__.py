"""Pakiet konwerterów. Import modułów dopisuje pary do rejestru."""

import logging
from pathlib import Path

PLIK_LOGU = Path(__file__).resolve().parent.parent / "konwerter.log"

logging.getLogger(__name__).addHandler(logging.NullHandler())


def zaladuj_konwertery() -> None:
    from konwersja import csv_json, libreoffice, txt_docx  # noqa: F401


def konfiguruj_logi(plik: Path = PLIK_LOGU) -> None:
    logging.basicConfig(
        filename=plik,
        encoding="utf-8",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
