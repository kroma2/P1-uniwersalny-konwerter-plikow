"""Okno konwertera. Wybór pliku i katalogu oraz uruchomienie pary z rejestru.

Konwersja idzie w wątku roboczym, żeby dłuższe wywołanie LibreOffice nie zamrażało okna.
Lista formatów pochodzi z rejestru, więc nowa para nie wymaga przebudowy tego ekranu.
"""

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from konwersja import konfiguruj_logi, zaladuj_konwertery
from konwersja.rejestr import ZlecenieKonwersji, dostepne_formaty, pary, wykonaj

KATALOG_PROJEKTU = Path(__file__).resolve().parent


class OknoKonwertera(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        zaladuj_konwertery()
        self.title("Konwerter plików")
        self.minsize(620, 440)
        self.sciezka_pliku = tk.StringVar()
        self.sciezka_katalogu = tk.StringVar()
        self.format_docelowy = tk.StringVar()
        self.formaty_widoczne: tuple[str, ...] = ()
        self.status = tk.StringVar()
        self.pytanie_nadpisania = messagebox.askyesno
        self.informacja = messagebox.showinfo
        self.okno_bledu = messagebox.showerror
        self._pracuje = False
        self._wyniki: queue.Queue[tuple[str, Path | Exception]] = queue.Queue()
        self._ustaw_styl()
        self._zbuduj()
        self._pokaz("Wybierz plik, katalog zapisu i format wynikowy.")
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

    def _ustaw_styl(self) -> None:
        styl = ttk.Style(self)
        styl.configure("Tytul.TLabel", font=("Segoe UI", 16, "bold"))
        styl.configure("Sukces.TLabel", foreground="#15803d")
        styl.configure("Blad.TLabel", foreground="#b91c1c")

    def _zbuduj(self) -> None:
        ramka = ttk.Frame(self, padding=24)
        ramka.pack(fill="both", expand=True)

        ttk.Label(ramka, text="Konwerter plików", style="Tytul.TLabel").pack(anchor="w")
        formaty = sorted({rozszerzenie.lstrip(".").upper() for para in pary() for rozszerzenie in para})
        ttk.Label(ramka, text="Obsługiwane formaty: " + ", ".join(formaty)).pack(
            anchor="w", pady=(2, 16)
        )

        karta = ttk.Frame(ramka, padding=4)
        karta.pack(fill="x")
        karta.columnconfigure(0, weight=1)

        self.przycisk_pliku = self._pole_wyboru(
            karta, 0, "1. Plik wejściowy", self.sciezka_pliku, self.wybierz_plik
        )
        self.przycisk_katalogu = self._pole_wyboru(
            karta, 2, "2. Katalog zapisu", self.sciezka_katalogu, self.wybierz_katalog
        )
        ttk.Label(karta, text="3. Format wynikowy").grid(
            row=4, column=0, sticky="w", pady=(16, 6)
        )
        self.lista_formatow = ttk.Combobox(
            karta, textvariable=self.format_docelowy, state="readonly", width=16
        )
        self.lista_formatow.grid(row=5, column=0, sticky="w")
        self.lista_formatow.bind("<<ComboboxSelected>>", lambda _zdarzenie: self._odswiez_stan())

        dol = ttk.Frame(ramka)
        dol.pack(fill="x", pady=(20, 8))
        self.przycisk_konwertuj = ttk.Button(dol, text="Konwertuj", command=self.konwertuj)
        self.przycisk_konwertuj.pack(side="left")
        self.postep = ttk.Progressbar(dol, mode="indeterminate", length=180)

        self.etykieta_stanu = ttk.Label(
            ramka, textvariable=self.status, wraplength=560, justify="left"
        )
        self.etykieta_stanu.pack(anchor="w", fill="x")

    def _pole_wyboru(self, karta, wiersz, tytul, zmienna, polecenie) -> ttk.Button:
        ttk.Label(karta, text=tytul).grid(
            row=wiersz, column=0, sticky="w", pady=(16 if wiersz else 0, 6)
        )
        pole = ttk.Entry(karta, textvariable=zmienna, state="readonly")
        pole.grid(row=wiersz + 1, column=0, sticky="ew")
        przycisk = ttk.Button(karta, text="Wybierz…", command=polecenie)
        przycisk.grid(row=wiersz + 1, column=1, padx=(10, 0))
        return przycisk

    def _pokaz(self, tekst: str, rodzaj: str = "TLabel") -> None:
        self.status.set(tekst)
        styl = rodzaj if rodzaj == "TLabel" else f"{rodzaj}.TLabel"
        self.etykieta_stanu.configure(style=styl)

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
            self._pokaz("Dostępne formaty: " + ", ".join(formaty) + ".")
        else:
            self.format_docelowy.set("")
            self._pokaz("Dla tego pliku nie ma konwersji. Wybierz inny plik.", "Blad")
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
            self._pokaz("Uzupełnij plik, katalog i format. Niedozwolona para nie zostanie uruchomiona.", "Blad")
            return
        nadpisz = self._zapytaj_o_nadpisanie(zlecenie)
        if nadpisz is None:
            self._pokaz("Anulowano. Istniejący plik pozostał bez zmian.")
            return

        self._pracuje = True
        self._odswiez_stan()
        self.postep.pack(side="left", padx=16)
        self.postep.start(10)
        self._pokaz("Trwa konwersja. Okno pozostaje aktywne.")

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
                    self._pokaz(f"Zapisano: {wartosc}", "Sukces")
                    self.informacja("Gotowe", f"Zapisano plik:\n{wartosc}", parent=self)
                else:
                    self._pokaz(f"Błąd: {wartosc}", "Blad")
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
        self.postep.pack_forget()
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
