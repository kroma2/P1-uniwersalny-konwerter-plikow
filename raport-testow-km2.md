# Raport testów — kamień milowy 2

Data: 26 października 2026.  
Autor: Jakub. Praca indywidualna.  
Katalog roboczy: katalog projektu. Polecenia uruchamiano przez `.\.venv\Scripts\python.exe` (Python 3.12.10).

## Środowisko

```text
Python 3.12.10
python-docx 1.2.0
LibreOffice: C:\Program Files\LibreOffice\program\soffice.com
```

Wersja programu zewnętrznego, polecenie `soffice.com --version`:

```text
LibreOffice 26.8.1.1 bf6ef2662401c7d6dce671ab4deb26ee0af3a7c1
```

Macierz wypisana przez `python main.py --macierz` (kod 0):

```text
.csv -> .json
.docx -> .pdf
.json -> .csv
.txt -> .docx
```

## T1. CSV → JSON

- Wejście: `dane/osoby.csv`.
- Wywołanie: `python main.py dane/osoby.csv json przyklady/t1`
- Oczekiwany rezultat: nagłówki, kolejność kolumn i polskie znaki zgodne ze źródłem.
- Faktyczny rezultat: kod 0, komunikat `Zapisano: przyklady\t1\osoby.json`. Treść pliku jest identyczna z `dane/osoby.json` (porównanie odczytanych obiektów JSON: zgodne). Są kolumny `imię`, `miasto`, `uwagi`, miasta `Łódź`, `Kraków`, `Gdańsk` oraz puste pole `uwagi` w drugim wierszu.
- Status: OK.
- Dowód: `przyklady/t1/osoby.json`.

## T2. JSON → CSV

- Wejście: `dane/osoby.json`.
- Wywołanie: `python main.py dane/osoby.json csv przyklady/t2`
- Oczekiwany rezultat: te same nagłówki, kolejność kolumn i wiersze.
- Faktyczny rezultat: kod 0, komunikat `Zapisano: przyklady\t2\osoby.csv`. Wiersze odczytane z wyniku są równe wierszom z `dane/osoby.csv`. Zapisany plik:

```text
imię,miasto,uwagi
Zosia,Łódź,uczennica
Jan,Kraków,
Michał,Gdańsk,w trakcie
```

- Status: OK.
- Dowód: `przyklady/t2/osoby.csv`.

## T3. TXT → DOCX

- Wejście: `dane/przyklad.txt` (UTF-8, linia „Zażółć gęślą jaźń”, pusta linia, drugi akapit).
- Wywołanie: `python main.py dane/przyklad.txt docx przyklady/t3`
- Oczekiwany rezultat: otwieralny DOCX, jedna linia to jeden akapit, bez dodatkowego akapitu od końcowego znaku nowej linii.
- Faktyczny rezultat: kod 0, komunikat `Zapisano: przyklady\t3\przyklad.docx`. Akapity odczytane z dokumentu:

```text
["Zażółć gęślą jaźń", "", "Drugi akapit: Łódź, Gdańsk i Kraków."]
```

- Status: OK.
- Dowód: `przyklady/t3/przyklad.docx`.

## T4. DOCX → PDF

- Wejście: `przyklady/t3/przyklad.docx`.
- Wywołanie: `python main.py przyklady/t3/przyklad.docx pdf przyklady/t4`
- Oczekiwany rezultat: otwieralny PDF z tą samą treścią i polskimi znakami. LibreOffice uruchamiany listą argumentów, bez powłoki.
- Faktyczny rezultat: kod 0, komunikat `Zapisano: przyklady\t4\przyklad.pdf`. Plik ma 20978 bajtów, zaczyna się od `%PDF-1.7` i ma jedną stronę. Tekst na stronie:

```text
Zażółć gęślą jaźń
Drugi akapit: Łódź, Gdańsk i Kraków.
```

Pusty akapit ze źródła widać jako odstęp między tymi zdaniami. Konwersja skończyła się w limicie 60 sekund.

- Status: OK.
- Dowód: `przyklady/t4/przyklad.pdf`.

## T5. Brak narzędzia

- Wejście: poprawny `przyklady/t3/przyklad.docx` oraz celowo nieistniejąca ścieżka programu.
- Wywołanie: `python main.py przyklady/t3/przyklad.docx pdf przyklady/t5 --program C:\nie-ma-libreoffice\soffice.com`
- Oczekiwany rezultat: kod różny od zera, komunikat z przyczyną i sposobem ustawienia ścieżki, bez nieobsłużonego wyjątku. Instalacja LibreOffice pozostaje na miejscu.
- Faktyczny rezultat: kod 1. Na standardowym wyjściu błędów:

```text
Błąd: Nie znaleziono LibreOffice pod ścieżką: C:\nie-ma-libreoffice\soffice.com. Zainstaluj LibreOffice i wskaż plik program\soffice.com (na Windows) albo ustaw zmienną środowiskową LIBREOFFICE_PATH.
```

Nie pojawił się traceback. W `przyklady/t5` nie powstał plik PDF.

- Status: OK.
- Dowód: kod zakończenia i komunikat powyżej.

## T6. Uszkodzony DOCX

- Wejście: `przyklady/t6/uszkodzony.docx`, czyli zwykły tekst „Zażółć gęślą jaźń” zapisany pod nazwą z rozszerzeniem `.docx`.
- Wywołanie: `python main.py przyklady/t6/uszkodzony.docx pdf przyklady/t6`
- Oczekiwany rezultat: brak fałszywego sukcesu.
- Faktyczny rezultat: kod 1. Program odrzuca plik przed uruchomieniem LibreOffice, bo to nie jest archiwum dokumentu:

```text
Błąd: Plik nie jest poprawnym dokumentem DOCX. Zmiana rozszerzenia nie tworzy dokumentu. Zapisz plik w edytorze jako DOCX.
```

Plik PDF nie powstał.

- Status: OK.
- Dowód: `przyklady/t6/uszkodzony.docx` oraz komunikat powyżej.

## T7. Istniejący wynik

- Wejście: ponowne `dane/przyklad.txt` do katalogu, w którym `przyklad.docx` już jest.
- Wywołanie: `python main.py dane/przyklad.txt docx przyklady/t3`
- Oczekiwany rezultat: odmowa nadpisania, dotychczasowy plik bez zmian.
- Faktyczny rezultat: kod 1.

```text
Błąd: Plik wynikowy już istnieje: przyklady\t3\przyklad.docx. Program nie nadpisuje wyników. Usuń ten plik albo wskaż inny katalog.
```

Rozmiar `przyklady/t3/przyklad.docx` przed powtórzeniem i po nim: 36661 bajtów i 36661 bajtów.

- Status: OK.
- Dowód: komunikat oraz niezmieniony rozmiar pliku.

Ta sama odmowa dla PDF jest w teście automatycznym: gdy plik wynikowy już istnieje, LibreOffice w ogóle nie jest uruchamiany.

## T8. Ścieżka ze spacjami

- Wejście: `przyklady/t8/katalog ze spacjami/notatka test.txt` o treści „Zażółć gęślą jaźń” i końcowym znaku nowej linii.
- Wywołanie bez powłoki, każdy argument osobno. W PowerShell trzeba dodać cudzysłowy:

```powershell
python main.py "przyklady/t8/katalog ze spacjami/notatka test.txt" docx "przyklady/t8/katalog ze spacjami"
python main.py "przyklady/t8/katalog ze spacjami/notatka test.docx" pdf "przyklady/t8/katalog ze spacjami"
```

- Oczekiwany rezultat: oba pliki powstają, a spacje w ścieżce nie rozbijają polecenia.
- Faktyczny rezultat: oba wywołania zakończyły się kodem 0.

```text
Zapisano: przyklady\t8\katalog ze spacjami\notatka test.docx
Zapisano: przyklady\t8\katalog ze spacjami\notatka test.pdf
```

PDF ma 17790 bajtów, nagłówek `%PDF-1.7`, a tekst na stronie to `Zażółć gęślą jaźń`. Test automatyczny dodatkowo sprawdza, że `subprocess.run` dostaje `shell=False`, limit 60 sekund oraz pełną ścieżkę jako jeden element listy, bez ręcznych cudzysłowów.

- Status: OK.
- Dowód: `przyklady/t8/katalog ze spacjami/notatka test.docx` i `notatka test.pdf`.

## Limit czasu

Osobny test nie zawiesza LibreOffice. Uruchamia `python -c "import time; time.sleep(30)"` z limitem 1 sekundy przez tę samą funkcję, która obsługuje proces. Wynik to wyjątek zamieniony na komunikat `Przekroczono czas konwersji (1 s)`. Przypadek zakończył się zgodnie z oczekiwaniem.

## Testy automatyczne

Polecenie: `python -m unittest testy.test_km2`

Wynik końcowy: 20 testów, czas 7,372 s, status OK. W tej puli jest rzeczywista konwersja DOCX → PDF programem LibreOffice, ścieżka ze spacjami, brak narzędzia, uszkodzony DOCX, odmowa nadpisania, kod zakończenia różny od zera oraz kod 0 bez utworzonego PDF.

## Źródła i narzędzia

Biblioteki i programy: Python 3.12.10, `python-docx` 1.2.0, LibreOffice 26.8.1.1. Dokumentacja: python-docx, moduł `subprocess` oraz parametry uruchamiania LibreOffice. Podstawa wymagań: instrukcja projektu z 5 października 2026, Lab. 3.

Przy tym etapie użyto asystenta w Cursorze (model Grok) do implementacji konwerterów dokumentów, rejestru, testów i tego raportu. Konwersja CSV → JSON powstała w poprzednim etapie i została podłączona do rejestru.
