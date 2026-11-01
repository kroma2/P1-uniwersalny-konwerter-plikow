"""Okno konwertera. Wybór pliku i katalogu oraz uruchomienie pary z rejestru.

Konwersja idzie w wątku roboczym, żeby dłuższe wywołanie LibreOffice nie zamrażało okna.
Lista formatów pochodzi z rejestru, więc nowa para nie wymaga przebudowy tego ekranu.
"""

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from konwersja import zaladuj_konwertery
from konwersja.rejestr import ZlecenieKonwersji, dostepne_formaty, pary, wykonaj

KATALOG_PROJEKTU = Path(__file__).resolve().parent


class OknoKonwertera(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        zaladuj_konwertery()
        self.title("Konwerter plików")
        self.minsize(560, 280)
        self.sciezka_pliku = tk.StringVar()
        self.sciezka_katalogu = tk.StringVar()
        self.format_docelowy = tk.StringVar()
        self.formaty_widoczne: tuple[str, ...] = ()
        self.status = tk.StringVar(value="Wybierz plik, katalog zapisu i format wynikowy.")
        self.pytanie_nadpisania = messagebox.askyesno
        self.informacja = messagebox.showinfo
        self.okno_bledu = messagebox.showerror
        self._pracuje = False
        self._wyniki: queue.Queue[tuple[str, Path | Exception]] = queue.Queue()
        self._po_odbiorze = None
        self._zbuduj()
        self._ustaw_przycisk()
        self._po_odbiorze = self.after(100, self._odbierz_wynik)

    def destroy(self) -> None:
        if self._po_odbiorze is not None:
            try:
                self.after_cancel(self._po_odbiorze)
            except tk.TclError:
                pass
            self._po_odbiorze = None
        super().destroy()

    def _zbuduj(self) -> None:
        ramka = ttk.Frame(self, padding=16)
        ramka.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        ramka.columnconfigure(1, weight=1)

        ttk.Label(ramka, text="Plik wejściowy").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(ramka, textvariable=self.sciezka_pliku, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=8
        )
        self.przycisk_pliku = ttk.Button(ramka, text="Wybierz", command=self.wybierz_plik)
        self.przycisk_pliku.grid(row=0, column=2)

        ttk.Label(ramka, text="Katalog zapisu").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(ramka, textvariable=self.sciezka_katalogu, state="readonly").grid(
            row=1, column=1, sticky="ew", padx=8
        )
        self.przycisk_katalogu = ttk.Button(ramka, text="Wybierz", command=self.wybierz_katalog)
        self.przycisk_katalogu.grid(row=1, column=2)

        ttk.Label(ramka, text="Format wynikowy").grid(row=2, column=0, sticky="w", pady=4)
        self.lista_formatow = ttk.Combobox(
            ramka,
            textvariable=self.format_docelowy,
            state="readonly",
            width=18,
        )
        self.lista_formatow.grid(row=2, column=1, sticky="w", padx=8)
        self.lista_formatow.bind("<<ComboboxSelected>>", lambda _zdarzenie: self._ustaw_przycisk())

        self.przycisk_konwertuj = ttk.Button(ramka, text="Konwertuj", command=self.konwertuj)
        self.przycisk_konwertuj.grid(row=3, column=0, columnspan=3, sticky="w", pady=(12, 8))

        ttk.Label(ramka, textvariable=self.status, wraplength=500, justify="left").grid(
            row=4, column=0, columnspan=3, sticky="ew"
        )

    def wybierz_plik(self) -> None:
        start = KATALOG_PROJEKTU / "dane"
        wybrany = filedialog.askopenfilename(
            parent=self,
            initialdir=str(start if start.is_dir() else Path.home()),
            title="Wybierz plik wejściowy",
            filetypes=_filtry_plikow(),
        )
        if not wybrany:
            return
        self.ustaw_plik(Path(wybrany))

    def wybierz_katalog(self) -> None:
        start = KATALOG_PROJEKTU
        wybrany = filedialog.askdirectory(
            parent=self,
            initialdir=str(start),
            title="Wybierz katalog zapisu",
            mustexist=True,
        )
        if not wybrany:
            return
        self.ustaw_katalog(Path(wybrany))

    def ustaw_plik(self, sciezka: Path) -> None:
        self.sciezka_pliku.set(str(sciezka))
        self._odswiez_formaty()

    def ustaw_katalog(self, sciezka: Path) -> None:
        self.sciezka_katalogu.set(str(sciezka))
        self._ustaw_przycisk()

    def _odswiez_formaty(self) -> None:
        plik = Path(self.sciezka_pliku.get())
        formaty = dostepne_formaty(plik) if plik.is_file() else []
        self.lista_formatow["values"] = formaty
        self.formaty_widoczne = tuple(formaty)
        if formaty:
            self.format_docelowy.set(formaty[0])
            self._wpis("Dostępne formaty: " + ", ".join(formaty) + ".")
        else:
            self.format_docelowy.set("")
            self._wpis("Dla tego pliku nie ma konwersji. Wybierz inny plik.")
        self._ustaw_przycisk()

    def _gotowe(self) -> bool:
        plik = Path(self.sciezka_pliku.get())
        katalog = Path(self.sciezka_katalogu.get())
        if not plik.is_file() or not katalog.is_dir():
            return False
        return self.format_docelowy.get() in dostepne_formaty(plik)

    def _ustaw_przycisk(self) -> None:
        if self._pracuje:
            self._zablokuj(True)
            return
        if self._gotowe():
            self.przycisk_konwertuj.state(["!disabled"])
        else:
            self.przycisk_konwertuj.state(["disabled"])

    def _zablokuj(self, zablokowane: bool) -> None:
        stan = ["disabled"] if zablokowane else ["!disabled"]
        self.przycisk_pliku.state(stan)
        self.przycisk_katalogu.state(stan)
        self.lista_formatow.state(["disabled"] if zablokowane else ["readonly"])
        if zablokowane or not self._gotowe():
            self.przycisk_konwertuj.state(["disabled"])
        else:
            self.przycisk_konwertuj.state(["!disabled"])

    def _wpis(self, tekst: str) -> None:
        self.status.set(tekst)

    def _przygotuj_zlecenie(self) -> ZlecenieKonwersji | None:
        if not self._gotowe():
            self._wpis("Uzupełnij plik, katalog i format. Niedozwolona para nie zostanie uruchomiona.")
            return None
        plik = Path(self.sciezka_pliku.get())
        katalog = Path(self.sciezka_katalogu.get())
        format_wyniku = self.format_docelowy.get()
        cel = katalog / f"{plik.stem}{format_wyniku}"
        if cel.exists():
            zgoda = self.pytanie_nadpisania(
                "Nadpisać plik?",
                f"Plik już istnieje:\n{cel}\n\nZastąpić go nowym wynikiem?",
                parent=self,
            )
            if not zgoda:
                self._wpis("Anulowano. Istniejący plik pozostał bez zmian.")
                return None
            try:
                cel.unlink()
            except OSError as blad:
                self._wpis(f"Błąd: nie można usunąć istniejącego pliku ({blad}). Zamknij go i spróbuj ponownie.")
                self.okno_bledu("Nie udało się konwertować", self.status.get(), parent=self)
                return None
        return ZlecenieKonwersji(plik, format_wyniku, katalog)

    def konwertuj(self) -> None:
        if self._pracuje:
            return
        zlecenie = self._przygotuj_zlecenie()
        if zlecenie is None:
            return
        self._pracuje = True
        self._zablokuj(True)
        self._wpis("Trwa konwersja. Okno pozostaje aktywne.")

        def praca() -> None:
            try:
                wynik = wykonaj(zlecenie)
            except Exception as blad:
                self._wyniki.put(("blad", blad))
            else:
                self._wyniki.put(("ok", wynik))

        threading.Thread(target=praca, daemon=True).start()

    def _odbierz_wynik(self) -> None:
        try:
            while True:
                rodzaj, wartosc = self._wyniki.get_nowait()
                if rodzaj == "ok" and isinstance(wartosc, Path):
                    self._pokaz_sukces(wartosc)
                elif isinstance(wartosc, Exception):
                    self._pokaz_blad(wartosc)
        except queue.Empty:
            pass
        try:
            self._po_odbiorze = self.after(100, self._odbierz_wynik)
        except tk.TclError:
            self._po_odbiorze = None

    def _pokaz_sukces(self, wynik: Path) -> None:
        self._pracuje = False
        self._zablokuj(False)
        self._wpis(f"Zapisano: {wynik}")
        self.informacja("Gotowe", f"Zapisano plik:\n{wynik}", parent=self)

    def _pokaz_blad(self, blad: Exception) -> None:
        self._pracuje = False
        self._zablokuj(False)
        self._wpis(f"Błąd: {blad}")
        self.okno_bledu("Nie udało się konwertować", self.status.get(), parent=self)


def _filtry_plikow() -> list[tuple[str, str]]:
    rozszerzenia = sorted({wejscie for wejscie, _wyjscie in pary()})
    wzor = " ".join(f"*{rozszerzenie}" for rozszerzenie in rozszerzenia)
    return [("Obsługiwane pliki", wzor), ("Wszystkie pliki", "*.*")]


def uruchom() -> None:
    okno = OknoKonwertera()
    okno.mainloop()


if __name__ == "__main__":
    uruchom()
