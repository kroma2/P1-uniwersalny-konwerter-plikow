"""Okno konwertera. Wybór pliku i katalogu oraz uruchomienie pary z rejestru.

Konwersja idzie w wątku roboczym, żeby dłuższe wywołanie LibreOffice nie zamrażało okna.
Lista formatów pochodzi z rejestru, więc nowa para nie wymaga przebudowy tego ekranu.
"""

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from konwersja import PLIK_LOGU, konfiguruj_logi, zaladuj_konwertery
from konwersja.rejestr import ZlecenieKonwersji, dostepne_formaty, pary, wykonaj

KATALOG_PROJEKTU = Path(__file__).resolve().parent


class OknoKonwertera(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        zaladuj_konwertery()
        self.title("Konwerter plików")
        self.minsize(560, 300)
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
        self._zbuduj()
        self._odswiez_stan()
        self._po_odbiorze: str | None = self.after(100, self._odbierz_wynik)

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
        self.lista_formatow.bind("<<ComboboxSelected>>", lambda _zdarzenie: self._odswiez_stan())

        self.przycisk_konwertuj = ttk.Button(ramka, text="Konwertuj", command=self.konwertuj)
        self.przycisk_konwertuj.grid(row=3, column=0, sticky="w", pady=(12, 8))
        self.postep = ttk.Progressbar(ramka, mode="indeterminate", length=200)
        self.postep.grid(row=3, column=1, sticky="w", padx=8, pady=(12, 8))

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
        if wybrany:
            self.ustaw_plik(Path(wybrany))

    def wybierz_katalog(self) -> None:
        wybrany = filedialog.askdirectory(
            parent=self,
            initialdir=str(KATALOG_PROJEKTU),
            title="Wybierz katalog zapisu",
            mustexist=True,
        )
        if wybrany:
            self.ustaw_katalog(Path(wybrany))

    def ustaw_plik(self, sciezka: Path) -> None:
        self.sciezka_pliku.set(str(sciezka))
        formaty = dostepne_formaty(sciezka) if sciezka.is_file() else []
        self.lista_formatow["values"] = formaty
        self.formaty_widoczne = tuple(formaty)
        if formaty:
            self.format_docelowy.set(formaty[0])
            self.status.set("Dostępne formaty: " + ", ".join(formaty) + ".")
        else:
            self.format_docelowy.set("")
            self.status.set("Dla tego pliku nie ma konwersji. Wybierz inny plik.")
        self._odswiez_stan()

    def ustaw_katalog(self, sciezka: Path) -> None:
        self.sciezka_katalogu.set(str(sciezka))
        self._odswiez_stan()

    def _wybrane(self) -> ZlecenieKonwersji | None:
        """Zwraca zlecenie tylko wtedy, gdy plik, katalog i format tworzą dozwoloną parę."""
        tekst_pliku = self.sciezka_pliku.get()
        tekst_katalogu = self.sciezka_katalogu.get()
        if not tekst_pliku or not tekst_katalogu:
            return None
        plik = Path(tekst_pliku)
        katalog = Path(tekst_katalogu)
        format_wyniku = self.format_docelowy.get()
        if not plik.is_file() or not katalog.is_dir():
            return None
        if format_wyniku not in dostepne_formaty(plik):
            return None
        return ZlecenieKonwersji(plik, format_wyniku, katalog)

    def _odswiez_stan(self) -> None:
        wybor = ["disabled"] if self._pracuje else ["!disabled"]
        self.przycisk_pliku.state(wybor)
        self.przycisk_katalogu.state(wybor)
        self.lista_formatow.state(["disabled"] if self._pracuje else ["!disabled", "readonly"])
        gotowe = not self._pracuje and self._wybrane() is not None
        self.przycisk_konwertuj.state(["!disabled"] if gotowe else ["disabled"])

    def _zapytaj_o_nadpisanie(self, zlecenie: ZlecenieKonwersji) -> bool | None:
        """True: nadpisać, False: plik nie istnieje, None: użytkownik odmówił."""
        cel = zlecenie.plik_wynikowy()
        if not cel.exists():
            return False
        zgoda = self.pytanie_nadpisania(
            "Nadpisać plik?",
            f"Plik już istnieje:\n{cel}\n\nZastąpić go nowym wynikiem?",
            parent=self,
        )
        return True if zgoda else None

    def konwertuj(self) -> None:
        if self._pracuje:
            return
        zlecenie = self._wybrane()
        if zlecenie is None:
            self.status.set("Uzupełnij plik, katalog i format. Niedozwolona para nie zostanie uruchomiona.")
            return
        nadpisz = self._zapytaj_o_nadpisanie(zlecenie)
        if nadpisz is None:
            self.status.set("Anulowano. Istniejący plik pozostał bez zmian.")
            return

        self._pracuje = True
        self._odswiez_stan()
        self.postep.start(10)
        self.status.set("Trwa konwersja. Okno pozostaje aktywne.")

        def praca() -> None:
            try:
                wynik = wykonaj(zlecenie, nadpisz=nadpisz)
            except Exception as blad:
                self._wyniki.put(("blad", blad))
            else:
                self._wyniki.put(("ok", wynik))

        threading.Thread(target=praca, daemon=True).start()

    def _odbierz_wynik(self) -> None:
        try:
            while True:
                rodzaj, wartosc = self._wyniki.get_nowait()
                self._zakoncz_prace()
                if rodzaj == "ok":
                    self.status.set(f"Zapisano: {wartosc}")
                    self.informacja("Gotowe", f"Zapisano plik:\n{wartosc}", parent=self)
                else:
                    self.status.set(f"Błąd: {wartosc}")
                    self.okno_bledu("Nie udało się konwertować", self.status.get(), parent=self)
        except queue.Empty:
            pass
        try:
            self._po_odbiorze = self.after(100, self._odbierz_wynik)
        except tk.TclError:
            self._po_odbiorze = None

    def _zakoncz_prace(self) -> None:
        self._pracuje = False
        self.postep.stop()
        self._odswiez_stan()


def _filtry_plikow() -> list[tuple[str, str]]:
    rozszerzenia = sorted({wejscie for wejscie, _wyjscie in pary()})
    wzor = " ".join(f"*{rozszerzenie}" for rozszerzenie in rozszerzenia)
    return [("Obsługiwane pliki", wzor), ("Wszystkie pliki", "*.*")]


def uruchom() -> None:
    konfiguruj_logi()
    okno = OknoKonwertera()
    okno.mainloop()


if __name__ == "__main__":
    uruchom()
