"""Memory : retrouve toutes les paires de cartes avec le moins de coups possible.

- 18 niveaux : on part de 2 paires, la difficulté monte par paliers (pas toujours +1 paire :
  certains niveaux ajoutent des fonds de couleur, d'autres sautent plusieurs paires)
- carte des niveaux : on peut rejouer n'importe quel niveau débloqué pour battre son record
- étoiles + meilleur score par niveau, sauvegardés dans un fichier JSON
"""

import json
import math
import random
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

# ----------------------------------------------------------------------------- données

# Emojis à copier depuis https://emojipedia.org/
SYMBOLES = ["🍎", "🐱", "🚀", "🌸", "🎲", "🎧", "🦊", "🍕", "🐶", "🌙", "⚽", "🎸"]

CREME = "#f6f1e7"
COULEURS_FOND = ["#8ecbff", "#ffe27a", "#ffa8c5", "#a8f0b0"]  # bleu, jaune, rose, vert

# (nombre de symboles, nombre de fonds de couleur) -> paires = symboles x fonds.
# Un 🐶 sur fond bleu et un 🐶 sur fond jaune sont deux cartes DIFFÉRENTES.
# Paires : 2 3 4 4 5 6 7 8 9 10 12 12 14 15 16 18 20 24
NIVEAUX = [
    (2, 1), (3, 1), (4, 1), (2, 2), (5, 1), (3, 2),
    (7, 1), (4, 2), (3, 3), (5, 2), (6, 2), (4, 3),
    (7, 2), (5, 3), (8, 2), (6, 3), (5, 4), (6, 4),
]

DELAI_VERIFICATION_MS = 400
DELAI_RETOURNEMENT_MS = 550

# ----------------------------------------------------------------------------- apparence

FOND = "#1b1b2f"
PANNEAU = "#2b2b45"
PANNEAU_SURVOL = "#3a3a5c"
VERROUILLE = "#232338"
TEXTE = "#f2f2f7"
DISCRET = "#8b8fb5"
OR = "#ffcc4d"
VERT = "#5fd38d"
ACCENT = "#7c83ff"
DOS = "#4b4f7a"
DOS_SURVOL = "#5d629a"
DOS_CONTOUR = "#6c71a8"

if sys.platform == "win32":
    POLICE, POLICE_EMOJI = "Segoe UI", "Segoe UI Emoji"
elif sys.platform == "darwin":
    POLICE, POLICE_EMOJI = "Helvetica", "Apple Color Emoji"
else:
    POLICE, POLICE_EMOJI = "Helvetica", "Noto Color Emoji"

LARGEUR_FENETRE, HAUTEUR_FENETRE = 860, 700
PLATEAU_MAX_L, PLATEAU_MAX_H = 780, 470
ESPACE = 10

# ----------------------------------------------------------------------------- sauvegarde


def dossier_donnees():
    """Dossier du script, ou de l'exécutable une fois compilé avec PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


FICHIER_PROGRESSION = dossier_donnees() / "memory_progression.json"


def charger_progression():
    try:
        donnees = json.loads(FICHIER_PROGRESSION.read_text(encoding="utf-8"))
        niveaux = donnees.get("niveaux", {})
        return niveaux if isinstance(niveaux, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def sauvegarder_progression(progression):
    try:
        FICHIER_PROGRESSION.write_text(
            json.dumps({"niveaux": progression}, indent=2), encoding="utf-8"
        )
    except OSError:
        pass  # dossier en lecture seule : le jeu continue sans sauvegarder


# ----------------------------------------------------------------------------- outils


def calcul_etoiles(coups, paires):
    ratio = coups / paires
    if ratio <= 1.6:
        return 3
    if ratio <= 2.4:
        return 2
    return 1


def dimensions_grille(nb_cartes):
    """(lignes, colonnes) la plus carrée possible, avec lignes <= colonnes."""
    meilleur = (2, nb_cartes // 2)
    for lignes in range(2, math.isqrt(nb_cartes) + 1):
        if nb_cartes % lignes == 0:
            meilleur = (lignes, nb_cartes // lignes)
    return meilleur


def decrire(nb_symboles, nb_fonds):
    paires = nb_symboles * nb_fonds
    if nb_fonds == 1:
        return f"{paires} paires"
    return f"{paires} paires · {nb_symboles} symboles × {nb_fonds} fonds"


def eclaircir(couleur, facteur=0.18):
    r, g, b = (int(couleur[k:k + 2], 16) for k in (1, 3, 5))
    r, g, b = (int(v + (255 - v) * facteur) for v in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def rect_arrondi(canvas, x1, y1, x2, y2, rayon, **options):
    rayon = max(1, min(rayon, (x2 - x1) / 2, (y2 - y1) / 2))
    points = [
        x1 + rayon, y1, x2 - rayon, y1, x2, y1, x2, y1 + rayon,
        x2, y2 - rayon, x2, y2, x2 - rayon, y2, x1 + rayon, y2,
        x1, y2, x1, y2 - rayon, x1, y1 + rayon, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **options)


def bouton(parent, texte, commande, bg=ACCENT, fg=FOND, taille=12):
    """Bouton stylé (un Label cliquable : les couleurs fonctionnent sur tous les systèmes)."""
    b = tk.Label(parent, text=texte, bg=bg, fg=fg, font=(POLICE, taille, "bold"),
                 padx=18, pady=8, cursor="hand2")
    b.bind("<Button-1>", lambda e: commande())
    b.bind("<Enter>", lambda e: b.config(bg=eclaircir(bg)))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


# ----------------------------------------------------------------------------- application


class Application:
    def __init__(self, racine):
        self.racine = racine
        racine.title("Memory")
        racine.configure(bg=FOND)
        racine.resizable(False, False)
        x = max((racine.winfo_screenwidth() - LARGEUR_FENETRE) // 2, 0)
        y = max((racine.winfo_screenheight() - HAUTEUR_FENETRE) // 2 - 20, 0)
        racine.geometry(f"{LARGEUR_FENETRE}x{HAUTEUR_FENETRE}+{x}+{y}")
        racine.bind("<Escape>", lambda e: self.afficher_menu())

        self.progression = charger_progression()
        self.partie_id = 0  # sert à ignorer les minuteries d'une partie abandonnée

        self.ecran_menu = tk.Frame(racine, bg=FOND)
        self.ecran_jeu = tk.Frame(racine, bg=FOND)
        self.construire_menu()
        self.construire_jeu()
        self.afficher_menu()

    # ------------------------------------------------------------------ navigation

    def afficher_menu(self):
        self.partie_id += 1
        self.ecran_jeu.pack_forget()
        self.ecran_menu.pack(fill="both", expand=True)
        self.dessiner_menu()

    def afficher_jeu(self):
        self.ecran_menu.pack_forget()
        self.ecran_jeu.pack(fill="both", expand=True)

    def est_debloque(self, n):
        return n == 1 or str(n - 1) in self.progression

    # ------------------------------------------------------------------ carte des niveaux

    def construire_menu(self):
        f = self.ecran_menu
        tk.Label(f, text="Memory", font=(POLICE, 38, "bold"), bg=FOND, fg=TEXTE).pack(pady=(26, 0))
        tk.Label(f, text="Choisis un niveau — tu peux rejouer les anciens pour battre ton record",
                 font=(POLICE, 12), bg=FOND, fg=DISCRET).pack()
        self.label_total = tk.Label(f, font=(POLICE, 16, "bold"), bg=FOND, fg=OR)
        self.label_total.pack(pady=(10, 6))

        self.taille_tuile, self.espace_tuile, self.colonnes_menu = 112, 18, 6
        largeur = self.colonnes_menu * self.taille_tuile + (self.colonnes_menu - 1) * self.espace_tuile
        self.marge_menu = 19
        lignes = math.ceil(len(NIVEAUX) / self.colonnes_menu)
        hauteur = lignes * self.taille_tuile + (lignes - 1) * self.espace_tuile
        self.canvas_menu = tk.Canvas(f, width=largeur + 2 * self.marge_menu, height=hauteur + 10,
                                     bg=FOND, highlightthickness=0)
        self.canvas_menu.pack(pady=6)

        reset = tk.Label(f, text="Réinitialiser la progression", font=(POLICE, 10, "underline"),
                         bg=FOND, fg=DISCRET, cursor="hand2")
        reset.pack(side="bottom", pady=14)
        reset.bind("<Button-1>", lambda e: self.reinitialiser())

    def dessiner_menu(self):
        c = self.canvas_menu
        c.delete("all")
        c.config(cursor="")
        t, gap, marge = self.taille_tuile, self.espace_tuile, self.marge_menu

        for idx, (ns, nf) in enumerate(NIVEAUX):
            n = idx + 1
            col, lig = idx % self.colonnes_menu, idx // self.colonnes_menu
            x1, y1 = marge + col * (t + gap), 5 + lig * (t + gap)
            cx = x1 + t / 2
            debloque = self.est_debloque(n)
            info = self.progression.get(str(n))
            tag = f"niv{n}"

            rect_arrondi(c, x1, y1, x1 + t, y1 + t, 20,
                         fill=PANNEAU if debloque else VERROUILLE,
                         outline=VERT if info else "", width=2, tags=(tag, f"fond{n}"))

            if debloque:
                c.create_text(cx, y1 + 32, text=str(n), fill=TEXTE, font=(POLICE, 26, "bold"), tags=tag)
                for k in range(3):
                    gagne = info is not None and k < info["etoiles"]
                    c.create_text(cx + (k - 1) * 26, y1 + 68, text="★",
                                  fill=OR if gagne else "#4a4a6a", font=(POLICE, 18), tags=tag)
            else:
                c.create_text(cx, y1 + 46, text="🔒", fill=DISCRET,
                              font=(POLICE_EMOJI, 24), tags=tag)

            # petits ronds = fonds de couleur du niveau, sinon le nombre de paires
            if nf > 1:
                for k in range(nf):
                    px = cx + (k - (nf - 1) / 2) * 14
                    c.create_oval(px - 4, y1 + 90, px + 4, y1 + 98,
                                  fill=COULEURS_FOND[k], outline="", tags=tag)
            else:
                c.create_text(cx, y1 + 94, text=f"{ns * nf} paires", fill=DISCRET,
                              font=(POLICE, 10), tags=tag)

            if debloque:
                c.tag_bind(tag, "<Button-1>", lambda e, n=n: self.lancer_niveau(n))
                c.tag_bind(tag, "<Enter>", lambda e, n=n: self.survol_tuile(n, True))
                c.tag_bind(tag, "<Leave>", lambda e, n=n: self.survol_tuile(n, False))

        total = sum(v["etoiles"] for v in self.progression.values())
        self.label_total.config(text=f"★ {total} / {3 * len(NIVEAUX)}")

    def survol_tuile(self, n, dessus):
        self.canvas_menu.itemconfig(f"fond{n}", fill=PANNEAU_SURVOL if dessus else PANNEAU)
        self.canvas_menu.config(cursor="hand2" if dessus else "")

    def reinitialiser(self):
        if messagebox.askyesno("Réinitialiser", "Effacer toute ta progression et tes records ?"):
            self.progression = {}
            sauvegarder_progression(self.progression)
            self.dessiner_menu()

    # ------------------------------------------------------------------ écran de jeu

    def construire_jeu(self):
        f = self.ecran_jeu
        entete = tk.Frame(f, bg=FOND)
        entete.pack(fill="x", padx=24, pady=(18, 4))
        entete.columnconfigure(1, weight=1)

        bouton(entete, "← Niveaux", self.afficher_menu, bg=PANNEAU, fg=TEXTE, taille=11).grid(
            row=0, column=0, sticky="w")
        self.label_titre = tk.Label(entete, font=(POLICE, 24, "bold"), bg=FOND, fg=TEXTE)
        self.label_titre.grid(row=0, column=1)
        stats = tk.Frame(entete, bg=FOND)
        stats.grid(row=0, column=2, sticky="e")
        self.label_coups = tk.Label(stats, font=(POLICE, 14, "bold"), bg=FOND, fg=TEXTE, anchor="e")
        self.label_coups.pack(anchor="e")
        self.label_record = tk.Label(stats, font=(POLICE, 10), bg=FOND, fg=DISCRET, anchor="e")
        self.label_record.pack(anchor="e")

        self.label_info = tk.Label(f, font=(POLICE, 11), bg=FOND, fg=DISCRET,
                                   wraplength=760, justify="center")
        self.label_info.pack(pady=(0, 4))

        self.plateau = tk.Canvas(f, bg=FOND, highlightthickness=0)
        self.plateau.pack(expand=True)

        bouton(f, "↻  Recommencer", self.nouvelle_partie, bg=PANNEAU, fg=TEXTE, taille=11).pack(pady=(0, 18))

        self.overlay = tk.Frame(f, bg=PANNEAU, highlightbackground=ACCENT, highlightthickness=2)

    def lancer_niveau(self, n):
        self.niveau = n
        self.afficher_jeu()
        self.nouvelle_partie()

    def nouvelle_partie(self):
        self.partie_id += 1
        self.overlay.place_forget()

        ns, nf = NIVEAUX[self.niveau - 1]
        symboles = random.sample(SYMBOLES, ns)
        fonds = random.sample(COULEURS_FOND, nf) if nf > 1 else [CREME]
        self.cartes = [(s, f) for s in symboles for f in fonds] * 2
        random.shuffle(self.cartes)

        self.etat = ["cache"] * len(self.cartes)  # cache | visible | trouve
        self.selection = []
        self.anim = set()
        self.survol = None
        self.coups = 0
        self.bloque = False
        self.fini = False

        self.label_titre.config(text=f"Niveau {self.niveau}")
        info = decrire(ns, nf)
        if nf > 1:
            info += "\nAttention : un même symbole existe sur plusieurs fonds, seule la combinaison identique forme une paire !"
        self.label_info.config(text=info)
        self.maj_infos()
        self.construire_plateau()

    def maj_infos(self):
        self.label_coups.config(text=f"Coups : {self.coups}")
        info = self.progression.get(str(self.niveau))
        self.label_record.config(text=f"Record : {info['coups']} coups" if info else "Record : —")

    def construire_plateau(self):
        n = len(self.cartes)
        lignes, colonnes = dimensions_grille(n)
        self.taille = min(100,
                          (PLATEAU_MAX_L - ESPACE) // colonnes - ESPACE,
                          (PLATEAU_MAX_H - ESPACE) // lignes - ESPACE)
        pas = self.taille + ESPACE
        c = self.plateau
        c.delete("all")
        c.config(width=colonnes * pas + ESPACE, height=lignes * pas + ESPACE, cursor="")

        self.centres = [
            (ESPACE + (i % colonnes) * pas + self.taille / 2,
             ESPACE + (i // colonnes) * pas + self.taille / 2)
            for i in range(n)
        ]
        for i in range(n):
            self.dessiner(i)
            tag = f"c{i}"
            c.tag_bind(tag, "<Button-1>", lambda e, i=i: self.cliquer(i))
            c.tag_bind(tag, "<Enter>", lambda e, i=i: self.survoler(i, True))
            c.tag_bind(tag, "<Leave>", lambda e, i=i: self.survoler(i, False))

    # ------------------------------------------------------------------ dessin des cartes

    def dessiner(self, i, echelle=1.0, face_haut=None):
        c = self.plateau
        c.delete(f"c{i}")
        if face_haut is None:
            face_haut = self.etat[i] != "cache"
        cx, cy = self.centres[i]
        t = self.taille
        demi = max(t / 2 * echelle, 2)

        if face_haut:
            fond = self.cartes[i][1]
            trouvee = self.etat[i] == "trouve"
            contour, epaisseur = (OR, 4) if trouvee else ("#d9d2c3", 1)
        else:
            fond = DOS_SURVOL if (self.survol == i and echelle == 1.0 and i not in self.anim) else DOS
            contour, epaisseur = DOS_CONTOUR, 2

        rect_arrondi(c, cx - demi, cy - t / 2, cx + demi, cy + t / 2, 16, fill=fond,
                     outline=contour, width=epaisseur, tags=(f"c{i}", f"cf{i}"))
        if echelle > 0.45:
            if face_haut:
                c.create_text(cx, cy, text=self.cartes[i][0], font=(POLICE_EMOJI, int(t * 0.42)),
                              fill="#222222", tags=f"c{i}")
            else:
                c.create_text(cx, cy, text="?", font=(POLICE, int(t * 0.4), "bold"),
                              fill="#aab0e8", tags=f"c{i}")

    def survoler(self, i, dessus):
        # itemconfig (et non un redessin) pour ne pas déclencher d'événements Enter/Leave en boucle
        self.survol = i if dessus else None
        peut = i < len(self.etat) and self.etat[i] == "cache" and i not in self.anim
        if peut:
            self.plateau.itemconfig(f"cf{i}", fill=DOS_SURVOL if dessus else DOS)
        self.plateau.config(cursor="hand2" if dessus and peut else "")

    def retourner(self, i, vers_haut):
        """Animation de retournement : la carte s'aplatit puis se redéploie."""
        partie = self.partie_id
        self.anim.add(i)
        avant, apres = not vers_haut, vers_haut
        images = [(0.7, avant), (0.4, avant), (0.1, avant),
                  (0.1, apres), (0.4, apres), (0.7, apres)]

        def etape(k):
            if partie != self.partie_id:
                return
            if k == len(images):
                self.anim.discard(i)
                self.dessiner(i)
                return
            echelle, face = images[k]
            self.dessiner(i, echelle, face)
            self.racine.after(22, etape, k + 1)

        etape(0)

    # ------------------------------------------------------------------ logique de jeu

    def cliquer(self, i):
        if self.bloque or self.fini or self.etat[i] != "cache" or i in self.anim:
            return
        self.etat[i] = "visible"
        self.selection.append(i)
        self.retourner(i, True)

        if len(self.selection) == 2:
            self.coups += 1
            self.maj_infos()
            self.bloque = True
            self.racine.after(DELAI_VERIFICATION_MS, self.verifier, self.partie_id)

    def verifier(self, partie):
        if partie != self.partie_id:
            return
        a, b = self.selection
        if self.cartes[a] == self.cartes[b]:  # même symbole ET même fond
            for i in (a, b):
                self.etat[i] = "trouve"
                self.dessiner(i)
            self.selection = []
            self.bloque = False
            if all(e == "trouve" for e in self.etat):
                self.racine.after(450, self.victoire, partie)
        else:
            self.racine.after(DELAI_RETOURNEMENT_MS, self.cacher, a, b, partie)

    def cacher(self, a, b, partie):
        if partie != self.partie_id:
            return
        for i in (a, b):
            self.etat[i] = "cache"
            self.retourner(i, False)
        self.selection = []
        self.racine.after(180, self.debloquer, partie)

    def debloquer(self, partie):
        if partie == self.partie_id:
            self.bloque = False

    def victoire(self, partie):
        if partie != self.partie_id:
            return
        self.fini = True
        paires = len(self.cartes) // 2
        etoiles = calcul_etoiles(self.coups, paires)
        cle = str(self.niveau)
        ancien = self.progression.get(cle)
        record = ancien is None or self.coups < ancien["coups"]
        if record:
            self.progression[cle] = {"coups": self.coups, "etoiles": etoiles}
            sauvegarder_progression(self.progression)
        self.maj_infos()
        self.afficher_victoire(etoiles, record)

    def afficher_victoire(self, etoiles, record):
        o = self.overlay
        for w in o.winfo_children():
            w.destroy()
        tk.Label(o, text="Niveau réussi !", font=(POLICE, 24, "bold"), bg=PANNEAU, fg=TEXTE).pack(
            padx=50, pady=(22, 0))
        tk.Label(o, text="★" * etoiles + "☆" * (3 - etoiles), font=(POLICE, 38), bg=PANNEAU, fg=OR).pack()
        tk.Label(o, text=f"Terminé en {self.coups} coups", font=(POLICE, 14), bg=PANNEAU, fg=TEXTE).pack()
        meilleur = self.progression[str(self.niveau)]["coups"]
        texte = "🏆 Nouveau record !" if record else f"Record : {meilleur} coups"
        tk.Label(o, text=texte, font=(POLICE, 12, "bold"), bg=PANNEAU,
                 fg=VERT if record else DISCRET).pack(pady=(2, 0))

        boutons = tk.Frame(o, bg=PANNEAU)
        boutons.pack(padx=24, pady=(16, 22))
        bouton(boutons, "Carte", self.afficher_menu, bg=FOND, fg=TEXTE, taille=11).pack(side="left", padx=5)
        bouton(boutons, "Rejouer", self.nouvelle_partie, bg=FOND, fg=TEXTE, taille=11).pack(side="left", padx=5)
        if self.niveau < len(NIVEAUX):
            bouton(boutons, "Niveau suivant →", lambda: self.lancer_niveau(self.niveau + 1)).pack(
                side="left", padx=5)
        else:
            tk.Label(o, text="🎉 Tous les niveaux sont terminés !", font=(POLICE, 11),
                     bg=PANNEAU, fg=OR).pack(pady=(0, 16))

        o.place(relx=0.5, rely=0.5, anchor="center")
        o.lift()


if __name__ == "__main__":
    fenetre = tk.Tk()
    Application(fenetre)
    fenetre.mainloop()
