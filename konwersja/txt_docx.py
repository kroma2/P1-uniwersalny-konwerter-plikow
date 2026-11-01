"""Konwersje TXT ↔ DOCX biblioteką python-docx.

TXT → DOCX:
- plik wejściowy jest w UTF-8 (dopuszczalny znacznik BOM),
- każda linia staje się osobnym akapitem,
- pusta linia wewnątrz tekstu staje się pustym akapitem,
- końcowy znak nowej linii nie dodaje kolejnego pustego akapitu,
- program nie interpretuje nagłówków ani znaczników formatowania.

DOCX → TXT:
- każdy akapit treści głównej staje się jedną linią zakończoną znakiem nowej linii,
- formatowanie, tabele, nagłówki i stopki strony oraz obrazy są pomijane.

Dzięki tym regułom TXT → DOCX → TXT odtwarza ten sam tekst.
"""

from pathlib import Path

from konwersja.rejestr import konwerter
from konwersja.walidacja import przygotuj_wynik, sprawdz_docx


def _biblioteka_docx():
    try:
        import docx
    except ImportError as blad:
        raise RuntimeError(
            "Brak biblioteki python-docx. Zainstaluj zależności poleceniem: "
            "python -m pip install -r requirements.txt"
        ) from blad
    return docx


def akapity(sciezka: Path) -> list[str]:
    docx = _biblioteka_docx()
    try:
        dokument = docx.Document(str(sciezka))
    except Exception as blad:  # python-docx zgłasza różne typy wyjątków dla uszkodzonej treści
        raise ValueError(
            "Nie można odczytać dokumentu DOCX. Plik może być uszkodzony: "
            "otwórz go w edytorze i zapisz ponownie."
        ) from blad
    return [akapit.text for akapit in dokument.paragraphs]


@konwerter(".txt", ".docx")
def txt_na_docx(zrodlo: Path, katalog: Path) -> Path:
    cel = przygotuj_wynik(zrodlo, katalog, ".txt", ".docx")
    docx = _biblioteka_docx()
    try:
        tekst = zrodlo.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as blad:
        raise ValueError(
            "Plik TXT nie jest zapisany w UTF-8. Zapisz go jako UTF-8 i spróbuj ponownie."
        ) from blad

    dokument = docx.Document()
    for linia in tekst.splitlines():
        dokument.add_paragraph(linia)
    dokument.save(str(cel))
    return cel


@konwerter(".docx", ".txt")
def docx_na_txt(zrodlo: Path, katalog: Path) -> Path:
    cel = przygotuj_wynik(zrodlo, katalog, ".docx", ".txt")
    sprawdz_docx(zrodlo)
    linie = akapity(zrodlo)
    cel.write_text("".join(linia + "\n" for linia in linie), encoding="utf-8")
    return cel
