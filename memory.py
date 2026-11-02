"""Memory : retrouve toutes les paires de cartes avec le moins de coups possible."""

import random
import tkinter as tk
from tkinter import messagebox

SYMBOLES = ["🍎", "🐱", "🚀", "🌸", "🎲", "🎧", "🦊", "🍕"] #copier a partir du site: https://emojipedia.org/
LIGNES, COLONNES = 4, 4
DELAI_RETOURNEMENT_MS = 800


class Memory:
    def __init__(self, racine):
        self.racine = racine
        racine.title("Memory")
        racine.resizable(False, False)

        self.label_coups = tk.Label(racine, font=("Arial", 14))
        self.label_coups.grid(row=0, column=0, columnspan=COLONNES, pady=8)

        self.cadre = tk.Frame(racine)
        self.cadre.grid(row=1, column=0, columnspan=COLONNES, padx=10)

        tk.Button(racine, text="Nouvelle partie", command=self.nouvelle_partie).grid(
            row=2, column=0, columnspan=COLONNES, pady=10
        )

        self.boutons = []
        for i in range(LIGNES * COLONNES):
            bouton = tk.Button(
                self.cadre,
                text="?",
                width=4,
                height=2,
                font=("Arial", 24),
                command=lambda i=i: self.cliquer(i),
            )
            bouton.grid(row=i // COLONNES, column=i % COLONNES, padx=3, pady=3)
            self.boutons.append(bouton)

        self.nouvelle_partie()

    def nouvelle_partie(self):
        self.cartes = SYMBOLES * 2
        random.shuffle(self.cartes)
        self.trouvees = set()
        self.selection = []
        self.coups = 0
        self.bloque = False
        for bouton in self.boutons:
            bouton.config(text="?", state="normal", bg="SystemButtonFace")
        self.maj_coups()

    def maj_coups(self):
        self.label_coups.config(text=f"Coups : {self.coups}")

    def cliquer(self, i):
        if self.bloque or i in self.trouvees or i in self.selection:
            return

        self.boutons[i].config(text=self.cartes[i])
        self.selection.append(i)

        if len(self.selection) == 2:
            self.coups += 1
            self.maj_coups()
            self.verifier()

    def verifier(self):
        a, b = self.selection
        if self.cartes[a] == self.cartes[b]:
            self.trouvees.update((a, b))
            for i in (a, b):
                self.boutons[i].config(state="disabled", bg="#b7f0b1")
            self.selection = []
            if len(self.trouvees) == len(self.cartes):
                messagebox.showinfo("Bravo !", f"Gagné en {self.coups} coups !")
        else:
            self.bloque = True
            self.racine.after(DELAI_RETOURNEMENT_MS, self.cacher, a, b)

    def cacher(self, a, b):
        for i in (a, b):
            self.boutons[i].config(text="?")
        self.selection = []
        self.bloque = False


if __name__ == "__main__":
    fenetre = tk.Tk()
    Memory(fenetre)
    fenetre.mainloop()
