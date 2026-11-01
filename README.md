# Uniwersalny konwerter plików

Projekt 1 z przedmiotu Programowanie V. Aplikacja desktopowa w Pythonie i Tkinter/ttk: wybierasz plik, katalog zapisu i jeden z formatów dostępnych dla tego pliku, a program wykonuje konwersję i pokazuje wynik albo czytelny błąd. Te same konwersje można uruchomić z wiersza poleceń.

Autor: Jakub. Projekt indywidualny, bez podziału pracy.

## Macierz formatów

| Grupa | Wejście | Wyjście | Narzędzie | Znane ograniczenia |
| --- | --- | --- | --- | --- |
| A. dane strukturalne | `.csv` | `.json` | `csv`, `json` (biblioteka standardowa) | Wymagany nagłówek bez pustych i powtórzonych nazw. Wiersz z większą liczbą pól niż nagłówek jest odrzucany. Brakujące pole staje się pustym napisem. Wszystkie wartości są zapisywane jako tekst. |
| A. dane strukturalne | `.json` | `.csv` | `csv`, `json` (biblioteka standardowa) | Przyjmowany jest tylko obiekt `{"kolumny": [...], "wiersze": [...]}`. Kolejność kolumn bierze się z listy `kolumny`, dodatkowe klucze wiersza są pomijane. `null` staje się pustą komórką, `true`/`false` są zapisywane małymi literami, a obiekt lub lista w komórce daje błąd. |
| B. tekst i dokumenty | `.txt` | `.docx` | `python-docx` | Jedna linia to jeden akapit, pusta linia to pusty akapit, końcowy znak nowej linii nie dodaje akapitu. Brak nagłówków, list i stylów. |
| B. tekst i dokumenty | `.docx` | `.txt` | `python-docx` | Każdy akapit treści głównej to jedna linia. Formatowanie, tabele, nagłówki i stopki strony oraz obrazy są pomijane. |
| C. formaty biurowe | `.docx` | `.pdf` | LibreOffice, tryb `--headless` | Układ stron i fonty mogą się różnić od Worda. Makra i osadzone obiekty nie są obsługiwane. |
| C. formaty biurowe | `.odt` | `.pdf` | LibreOffice, tryb `--headless` | Jak wyżej. Plik musi być prawdziwym dokumentem Writer, nie innym plikiem z rozszerzeniem `.odt`. |

Wszystkie pliki tekstowe są czytane i zapisywane w UTF-8. Przy odczycie dopuszczalny jest znacznik BOM. Konwersja z PDF do formatu edytowalnego nie jest obsługiwana.

Łańcuch TXT → DOCX → TXT odtwarza ten sam tekst. Łańcuch CSV → JSON → CSV odtwarza te same wiersze i kolejność kolumn.

## Wymagania

- Python 3.10 lub nowszy z modułem Tkinter (instalator z python.org zawiera go domyślnie). Projekt sprawdzono na Pythonie 3.12.10 w Windows 11.
- Pakiet `python-docx` z pliku `requirements.txt` (sprawdzono wersję 1.2.0).
- LibreOffice do kierunków DOCX → PDF i ODT → PDF (sprawdzono wersję 26.8.1.1). To osobny program, `pip` go nie instaluje. Pozostałe cztery kierunki działają bez niego.

## Instalacja

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Na Linuksie i macOS środowisko aktywuje się poleceniem `source .venv/bin/activate`.

LibreOffice w Windows można zainstalować ze strony [libreoffice.org](https://www.libreoffice.org/download/) albo poleceniem:

```powershell
winget install --id TheDocumentFoundation.LibreOffice -e
```

### Ścieżka do LibreOffice

Program szuka narzędzia w tej kolejności:

1. argument `--program` w wierszu poleceń,
2. zmienna środowiskowa `LIBREOFFICE_PATH`,
3. polecenia `soffice.com`, `soffice` i `libreoffice` w PATH,
4. typowe miejsca instalacji: `C:\Program Files\LibreOffice\program\soffice.com`, `/Applications/LibreOffice.app/Contents/MacOS/soffice`, `/usr/bin/soffice`.

W Windows do pracy bez okna służy `soffice.com`, nie `soffice.exe`. Gdy LibreOffice jest w innym miejscu:

```powershell
$env:LIBREOFFICE_PATH = "D:\Programy\LibreOffice\program\soffice.com"
```

Sprawdzenie, co program znalazł:

```powershell
python main.py --srodowisko
```

## Uruchomienie

### Okno programu

```powershell
python main.py
```

1. „Wybierz” przy polu „Plik wejściowy”. Okno startuje w katalogu `dane`.
2. „Wybierz” przy polu „Katalog zapisu”.
3. Z listy „Format wynikowy” wybierz format. Lista zawiera tylko formaty dostępne dla rozszerzenia wybranego pliku. Dla nieobsługiwanego pliku lista jest pusta.
4. „Konwertuj”. Przycisk jest aktywny dopiero, gdy wszystkie trzy wybory tworzą dozwoloną parę.

Jeśli plik wynikowy już istnieje, program pyta, czy go zastąpić. Odmowa zostawia stary plik bez zmian. Zgoda podmienia go dopiero po udanej konwersji, więc nieudana próba niczego nie niszczy. Konwersja działa w osobnym wątku: okno nie zamiera, a pasek postępu i komunikat pod przyciskiem pokazują stan pracy. Na końcu pojawia się okno z wynikiem albo z przyczyną błędu i tym, co zrobić dalej.

### Wiersz poleceń

Składnia: `python main.py PLIK FORMAT KATALOG [--nadpisz] [--program ŚCIEŻKA]`. Katalog musi istnieć.

```powershell
mkdir wyniki
python main.py dane\osoby.csv json wyniki
python main.py dane\osoby.json csv wyniki
python main.py dane\przyklad.txt docx wyniki
python main.py dane\przyklad.docx txt wyniki
python main.py dane\przyklad.docx pdf wyniki
python main.py dane\przyklad.odt pdf wyniki
```

Sukces kończy się kodem 0 i komunikatem `Zapisano: ...`. Błąd kończy się kodem 1 i komunikatem z przyczyną oraz dalszym krokiem. Bez `--nadpisz` program odmawia zastąpienia istniejącego pliku.

Inne polecenia:

```powershell
python main.py --macierz
python main.py --srodowisko
python main.py --help
```

### Dziennik błędów

Każda konwersja uruchomiona z okna albo z wiersza poleceń jest zapisywana w `konwerter.log` w katalogu projektu: sukces z czasem trwania i nieudana próba z przyczyną. Plik jest pomijany przez git.

## Bezpieczne uruchamianie LibreOffice

- Polecenie to lista argumentów, a wywołanie ma `shell=False`. Ścieżka ze spacjami jest jednym elementem listy, bez ręcznych cudzysłowów.
- Limit czasu wynosi 60 sekund. Po jego przekroczeniu pojawia się komunikat zamiast zawieszenia programu.
- Kod zakończenia różny od 0 jest błędem i trafia do komunikatu razem z treścią stderr.
- Kod 0 nie wystarcza: musi powstać nowy, niepusty plik zaczynający się od `%PDF`.
- Konwersja odbywa się w pustym katalogu tymczasowym z osobnym profilem użytkownika LibreOffice. Wynik jest kopiowany do katalogu docelowego dopiero na końcu.
- Przed uruchomieniem program sprawdza, czy DOCX i ODT są prawdziwymi dokumentami. Zwykły tekst przemianowany na `.docx` nie dociera do LibreOffice.

## Struktura

| Ścieżka | Rola |
| --- | --- |
| `main.py` | Punkt startowy. Bez argumentów otwiera okno, z argumentami działa w wierszu poleceń. |
| `gui.py` | Okno Tkinter/ttk. Pobiera formaty z rejestru i uruchamia konwersję w wątku roboczym. |
| `konwersja/rejestr.py` | Rejestr par, zlecenie konwersji, walidacja wyboru, polityka nadpisywania i logowanie. |
| `konwersja/walidacja.py` | Wspólne sprawdzenia: plik wejściowy, katalog, istniejący wynik, poprawność DOCX i ODT. |
| `konwersja/csv_json.py` | CSV → JSON i JSON → CSV. |
| `konwersja/txt_docx.py` | TXT → DOCX i DOCX → TXT. |
| `konwersja/libreoffice.py` | DOCX → PDF i ODT → PDF, wyszukiwanie i bezpieczne uruchamianie LibreOffice. |
| `testy/` | Testy automatyczne konwerterów, rejestru, procesu i okna. |
| `dane/` | Dane wejściowe. |
| `przyklady/` | Wyniki wszystkich sześciu kierunków uzyskane z plików z `dane/`. |
| `raport-testow.md` | Raport testów z faktycznymi wynikami. |

Nowy kierunek to funkcja `(plik, katalog) -> Path` oznaczona dekoratorem `@konwerter(".we", ".wy")`. Okno i wiersz poleceń pobierają pary z rejestru, więc nie trzeba ich zmieniać.

## Dane testowe

| Plik | Zawartość | Oczekiwany wynik |
| --- | --- | --- |
| `dane/osoby.csv` | Nagłówek `imię,miasto,uwagi`, trzy wiersze z polskimi znakami i jedno puste pole. | JSON identyczny z `dane/osoby.json`. |
| `dane/osoby.json` | Ta sama tabela w przyjętej strukturze JSON. | CSV z tymi samymi wierszami i kolejnością kolumn co `dane/osoby.csv`. |
| `dane/przyklad.txt` | „Zażółć gęślą jaźń”, pusta linia, „Drugi akapit: Łódź, Gdańsk i Kraków.” | DOCX z trzema akapitami, w tym jednym pustym. |
| `dane/przyklad.docx` | Ten sam tekst jako dokument Word. | TXT identyczny z `dane/przyklad.txt` oraz jednostronicowy PDF z tym tekstem. |
| `dane/przyklad.odt` | Ten sam tekst jako dokument LibreOffice Writer. | Jednostronicowy PDF z tym tekstem. |
| `dane/bledne/zly.json` | JSON urwany w połowie. | Błąd „Niepoprawny JSON” z numerem wiersza, brak pliku wynikowego. |
| `dane/bledne/uszkodzony.docx` | Zwykły tekst z rozszerzeniem `.docx`. | Błąd „Plik nie jest poprawnym dokumentem DOCX”, brak pliku wynikowego. |

## Testy

```powershell
python -m unittest discover -s testy -v
```

40 testów obejmuje wszystkie kierunki, błędne i uszkodzone pliki, brak LibreOffice i `python-docx`, kod zakończenia, limit czasu, listę argumentów, nadpisywanie, ścieżki ze spacjami, logowanie oraz zachowanie okna. Test rzeczywistej konwersji LibreOffice jest pomijany, gdy program nie jest zainstalowany. Wyniki i opis przypadków są w `raport-testow.md`.

## Źródła i biblioteki

- Instrukcja projektu „Uniwersalny konwerter plików”, wersja 5 października 2026, oraz materiały do kamienia milowego 2.
- [python-docx](https://python-docx.readthedocs.io/) (licencja MIT): tworzenie i odczyt dokumentów DOCX.
- [LibreOffice, parametry uruchamiania](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html): `--headless`, `--convert-to`, `--outdir`, osobny profil użytkownika.
- [subprocess](https://docs.python.org/3/library/subprocess.html): `run()`, lista argumentów, kod zakończenia, limit czasu.
- [tkinter.ttk](https://docs.python.org/3/library/tkinter.ttk.html) i [tkinter.filedialog](https://docs.python.org/3/library/dialog.html): okno, lista wyboru, okna wyboru pliku i katalogu.
- [logging](https://docs.python.org/3/library/logging.html): dziennik konwersji.

## Narzędzia AI

Przy projekcie korzystałem z asystenta Claude (Anthropic) w edytorze Cursor. Zakres pomocy:

- szkic konwerterów JSON → CSV, TXT ↔ DOCX, DOCX → PDF i ODT → PDF oraz dopasowanie istniejącego CSV → JSON do rejestru,
- szkic rejestru, walidacji, polityki nadpisywania, logowania i okna Tkinter z wątkiem roboczym,
- propozycja testów automatycznych i struktury raportu oraz pomoc przy tym README.

Wygenerowany kod został uruchomiony i sprawdzony testami opisanymi w raporcie. Wyniki w raporcie pochodzą z rzeczywistych uruchomień. W raporcie z kamienia milowego 2 omyłkowo podałem model Grok. Właściwym narzędziem był Claude.

## Dziennik etapów

| Etap | Commit | Zakres |
| --- | --- | --- |
| Lab. 2 | `f670baa` | CSV → JSON z zachowaniem nagłówków i UTF-8, dane przykładowe. |
| Lab. 3, kamień milowy 2 | `4c0d844` | JSON → CSV, TXT → DOCX, DOCX → PDF przez LibreOffice, rejestr par, testy T1–T8. |
| Lab. 4, kamień milowy 3 | `0113b44` | Okno Tkinter: formaty zależne od pliku, pytanie o nadpisanie, konwersja w wątku. |
| Lab. 5, oddanie | kolejny commit | DOCX → TXT i ODT → PDF, wspólna walidacja, logowanie, bezpieczne nadpisywanie, obsługa braku `python-docx`, testy, README i raport. |

## Oddanie

Archiwum według zasad przedmiotu ma nazwę `Nazwisko_Imie_P1.zip`. Najprościej utworzyć je z ostatniego commita, bez środowiska `.venv` i plików tymczasowych:

```powershell
git archive -o Nazwisko_Imie_P1.zip HEAD
```
