"""Konwersja TXT → DOCX biblioteką python-docx.

Reguła przenoszenia tekstu:
- plik wejściowy jest w UTF-8,
- każda linia staje się osobnym akapitem,
- pusta linia wewnątrz tekstu staje się pustym akapitem,
- końcowy znak nowej linii nie dodaje kolejnego pustego akapitu,
- program nie interpretuje nagłówków ani znaczników formatowania.

Nowy dokument python-docx zawiera domyślnie jeden pusty akapit. Jest on usuwany,
żeby liczba akapitów odpowiadała liczbie linii, a nie była o jeden większa.
"""

from pathlib import Path

from docx import Document

from konwersja.rejestr import konwerter, przygotuj_wynik


def _usun_domyslny_akapit(dokument: Document) -> None:
    if not dokument.paragraphs:
        return
    element = dokument.paragraphs[0]._element
    rodzic = element.getparent()
    if rodzic is not None:
        rodzic.remove(element)


def akapity(sciezka: Path) -> list[str]:
    """Zwraca treść akapitów DOCX. Służy do testów i sprawdzenia reguły."""
    dokument = Document(str(sciezka))
    return [akapit.text for akapit in dokument.paragraphs]


@konwerter(".txt", ".docx")
def txt_na_docx(zrodlo: Path, katalog: Path) -> Path:
    cel = przygotuj_wynik(zrodlo, katalog, ".txt", ".docx")
    try:
        tekst = zrodlo.read_text(encoding="utf-8")
    except UnicodeDecodeError as blad:
        raise ValueError(
            "Plik TXT nie jest zapisany w UTF-8. Zapisz go jako UTF-8 i spróbuj ponownie."
        ) from blad

    dokument = Document()
    _usun_domyslny_akapit(dokument)
    for linia in tekst.splitlines():
        dokument.add_paragraph(linia)
    dokument.save(str(cel))
    return cel
