"""Pakiet konwerterów. Import modułów dopisuje pary do rejestru."""


def zaladuj_konwertery() -> None:
    from konwersja import csv_json, docx_pdf, txt_docx  # noqa: F401
