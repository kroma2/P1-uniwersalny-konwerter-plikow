# Raport testów — Projekt 1, wersja do oddania

Data: 1 listopada 2026.  
Autor: Jakub.  
Środowisko: Windows 11, Python 3.12.10, python-docx 1.2.0, LibreOffice 26.8.1.1 (`C:\Program Files\LibreOffice\program\soffice.com`).  
Polecenia uruchamiano z katalogu projektu, w aktywnym środowisku `.venv`.

## Podsumowanie minimalnej macierzy testów

| Przypadek z instrukcji | Próby | Status |
| --- | --- | --- |
| Poprawny plik w każdej wspieranej grupie | P1–P6 | OK |
| Błędny lub uszkodzony plik | B1, B2 | OK |
| Nieobsługiwana para | B3 | OK |
| Brak LibreOffice lub biblioteki | B4, B5 | OK |
| Plik docelowy już istnieje | B6 | OK |
| Polskie znaki i puste wartości | P1–P6, B8 | OK |

Dodatkowo: kontrola procesu LibreOffice (B7), ścieżka ze spacjami (B8) i dziennik błędów (B9).

Macierz wypisana przez `python main.py --macierz` (kod 0):

```text
.csv -> .json
.docx -> .pdf
.docx -> .txt
.json -> .csv
.odt -> .pdf
.txt -> .docx
```

## Poprawne pliki

Wyniki zapisano w `przyklady/<kierunek>/`. Każde polecenie zakończyło się kodem 0 i komunikatem `Zapisano: ...`.

### P1. CSV → JSON

- Wejście: `dane/osoby.csv`.
- Wywołanie: `python main.py dane/osoby.csv json przyklady/csv-json`
- Oczekiwany rezultat: nagłówki, kolejność kolumn, polskie znaki i puste pole zachowane.
- Faktyczny rezultat: odczytany JSON jest równy `dane/osoby.json`. Kolumny `imię`, `miasto`, `uwagi`, miasta `Łódź`, `Kraków`, `Gdańsk`, puste pole `uwagi` w drugim wierszu.
- Status: OK. Dowód: `przyklady/csv-json/osoby.json`.

### P2. JSON → CSV

- Wejście: `dane/osoby.json`.
- Wywołanie: `python main.py dane/osoby.json csv przyklady/json-csv`
- Oczekiwany rezultat: te same wiersze i kolejność kolumn co w `dane/osoby.csv`.
- Faktyczny rezultat: wiersze odczytane z wyniku są równe wierszom z `dane/osoby.csv`.

```text
imię,miasto,uwagi
Zosia,Łódź,uczennica
Jan,Kraków,
Michał,Gdańsk,w trakcie
```

- Status: OK. Dowód: `przyklady/json-csv/osoby.csv`.

### P3. TXT → DOCX

- Wejście: `dane/przyklad.txt`.
- Wywołanie: `python main.py dane/przyklad.txt docx przyklady/txt-docx`
- Oczekiwany rezultat: jedna linia to jeden akapit, bez dodatkowego akapitu na końcu.
- Faktyczny rezultat: akapity dokumentu to `["Zażółć gęślą jaźń", "", "Drugi akapit: Łódź, Gdańsk i Kraków."]`.
- Status: OK. Dowód: `przyklady/txt-docx/przyklad.docx`.

### P4. DOCX → TXT

- Wejście: `dane/przyklad.docx`.
- Wywołanie: `python main.py dane/przyklad.docx txt przyklady/docx-txt`
- Oczekiwany rezultat: tekst identyczny z `dane/przyklad.txt`.
- Faktyczny rezultat: zawartość `"Zażółć gęślą jaźń\n\nDrugi akapit: Łódź, Gdańsk i Kraków.\n"`, porównanie z `dane/przyklad.txt`: zgodne.
- Status: OK. Dowód: `przyklady/docx-txt/przyklad.txt`.

### P5. DOCX → PDF

- Wejście: `dane/przyklad.docx`.
- Wywołanie: `python main.py dane/przyklad.docx pdf przyklady/docx-pdf`
- Oczekiwany rezultat: otwieralny PDF z tym samym tekstem i polskimi znakami.
- Faktyczny rezultat: 20978 bajtów, nagłówek `%PDF-1.7`, 1 strona. Tekst strony: „Zażółć gęślą jaźń” i „Drugi akapit: Łódź, Gdańsk i Kraków.”, z odstępem w miejscu pustego akapitu. Czas: 4,84 s.
- Status: OK. Dowód: `przyklady/docx-pdf/przyklad.pdf`.

### P6. ODT → PDF

- Wejście: `dane/przyklad.odt`.
- Wywołanie: `python main.py dane/przyklad.odt pdf przyklady/odt-pdf`
- Oczekiwany rezultat: jak w P5.
- Faktyczny rezultat: 20978 bajtów, nagłówek `%PDF-1.7`, 1 strona, ten sam tekst co w P5. Czas: 6,15 s.
- Status: OK. Dowód: `przyklady/odt-pdf/przyklad.pdf`.

## Przypadki błędne i brzegowe

### B1. Błędny JSON

- Wejście: `dane/bledne/zly.json` (JSON urwany w połowie).
- Wywołanie: `python main.py dane/bledne/zly.json csv <katalog tymczasowy>`
- Oczekiwany rezultat: kontrolowany błąd, brak pliku wynikowego.
- Faktyczny rezultat: kod 1, `Błąd: Niepoprawny JSON (Expecting value, wiersz 5). Popraw składnię pliku.` Katalog wynikowy pozostał pusty.
- W oknie pojawia się ten sam komunikat. Po zamknięciu okna błędu przyciski są znów aktywne.
- Status: OK.

### B2. Uszkodzony DOCX

- Wejście: `dane/bledne/uszkodzony.docx` (zwykły tekst z rozszerzeniem `.docx`).
- Wywołanie: `python main.py dane/bledne/uszkodzony.docx pdf <katalog>` oraz to samo z formatem `txt`.
- Oczekiwany rezultat: brak fałszywego sukcesu.
- Faktyczny rezultat: oba wywołania kończą się kodem 1 i komunikatem `Błąd: Plik nie jest poprawnym dokumentem DOCX. Zmiana rozszerzenia nie tworzy dokumentu. Zapisz plik w edytorze jako DOCX.` Nie powstał żaden plik, a LibreOffice nie został uruchomiony.
- Status: OK.

### B3. Nieobsługiwana para

- Wejście: `dane/przyklad.txt` z formatem `pdf`.
- Wywołanie: `python main.py dane/przyklad.txt pdf <katalog>`
- Oczekiwany rezultat: brak próby konwersji.
- Faktyczny rezultat: kod 1, `Błąd: Nieobsługiwana konwersja .txt -> .pdf. Dostępne formaty dla tego pliku: .docx.`
- W oknie dla pliku `.png` lista formatów jest pusta, a przycisk „Konwertuj” zostaje zablokowany. Dla plików z `dane/` lista zawiera wyłącznie formaty z macierzy.
- Status: OK.

### B4. Brak LibreOffice

- Wejście: `dane/przyklad.docx` z celowo błędną ścieżką programu. Instalacja LibreOffice pozostała na miejscu.
- Wywołanie: `python main.py dane/przyklad.docx pdf <katalog> --program C:\nie-ma-libreoffice\soffice.com`
- Oczekiwany rezultat: kontrolowany błąd z instrukcją.
- Faktyczny rezultat: kod 1, bez tracebacku:

```text
Błąd: Nie znaleziono LibreOffice pod ścieżką: C:\nie-ma-libreoffice\soffice.com. Zainstaluj LibreOffice i wskaż plik program\soffice.com (na Windows) albo ustaw zmienną środowiskową LIBREOFFICE_PATH.
```

- Status: OK.

### B5. Brak biblioteki python-docx

- Wejście: `dane/przyklad.txt` z formatem `docx`, przy zablokowanym imporcie modułu `docx` (`sys.modules["docx"] = None`, bez odinstalowania pakietu).
- Oczekiwany rezultat: kontrolowany błąd z instrukcją, a CSV/JSON nadal działa.
- Faktyczny rezultat: kod 1, `Błąd: Brak biblioteki python-docx. Zainstaluj zależności poleceniem: python -m pip install -r requirements.txt`. Program uruchamia się mimo braku biblioteki, bo jest ona importowana dopiero przy konwersji dokumentu.
- Status: OK.

### B6. Plik docelowy już istnieje

- Wiersz poleceń bez zgody: `python main.py dane/osoby.csv json przyklady/csv-json` przy istniejącym `osoby.json` kończy się kodem 1 i komunikatem `Plik wynikowy już istnieje: przyklady\csv-json\osoby.json. Program nie nadpisuje wyników bez zgody. Usuń ten plik albo wskaż inny katalog.` Zawartość pliku bajt w bajt bez zmian.
- Wiersz poleceń za zgodą: z opcją `--nadpisz` plik z treścią „STARY” został zastąpiony poprawnym JSON (kod 0).
- Okno: przy istniejącym wyniku pojawia się pytanie „Nadpisać plik?”. Odmowa zostawia plik bez zmian, zgoda podmienia go nowym wynikiem.
- Status: OK.

### B7. Kontrola procesu LibreOffice

LibreOffice dostaje listę argumentów `--headless`, `--convert-to pdf` i `--outdir`, z `shell=False` i limitem 60 s. Kod zakończenia różny od 0 jest błędem. Kod 0 bez niepustego pliku zaczynającego się od `%PDF` też jest błędem. Przy błędzie niepełny plik jest usuwany.

Status: OK.

### B8. Ścieżka ze spacjami

- Wejście: `notatka test.txt` z treścią „Zażółć gęślą jaźń” w katalogu `...\p1 spacje ...\katalog ze spacjami`.
- Wywołanie: `python main.py "<katalog>\notatka test.txt" docx "<katalog>"`, a następnie `python main.py "<katalog>\notatka test.docx" pdf "<katalog>"`.
- Faktyczny rezultat: oba wywołania zakończyły się kodem 0. PDF ma 17790 bajtów, 1 stronę i tekst „Zażółć gęślą jaźń”.
- Status: OK.

### B9. Dziennik błędów

Fragment `konwerter.log` z tej sesji:

```text
2026-11-01 16:46:19,762 INFO konwersja.rejestr: Zapisano przyklady\docx-pdf\przyklad.pdf w 4.84 s
2026-11-01 16:46:26,505 WARNING konwersja.rejestr: Nieudana konwersja dane\bledne\zly.json -> csv: Niepoprawny JSON (Expecting value, wiersz 5). Popraw składnię pliku.
2026-11-01 16:46:27,251 WARNING konwersja.rejestr: Nieudana konwersja dane\przyklad.docx -> pdf: Nie znaleziono LibreOffice pod ścieżką: C:\nie-ma-libreoffice\soffice.com. Zainstaluj LibreOffice i wskaż plik program\soffice.com (na Windows) albo ustaw zmienną środowiskową LIBREOFFICE_PATH.
2026-11-01 16:46:27,605 WARNING konwersja.rejestr: Nieudana konwersja dane\osoby.csv -> json: Plik wynikowy już istnieje: przyklady\csv-json\osoby.json. Program nie nadpisuje wyników bez zgody. Usuń ten plik albo wskaż inny katalog.
```

Status: OK.
