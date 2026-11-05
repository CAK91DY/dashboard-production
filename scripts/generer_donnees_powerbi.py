"""Jeu de données FICTIF détaillé (~105 000 lignes) pour la version Power BI du tableau de bord.

Principe
--------
Les CSV de `data/` (octobre 2026, déjà envoyés au client) restent la RÉFÉRENCE et ne sont pas
modifiés. Ce script produit un modèle en étoile plus fin (grain : heure x ligne de production,
novembre 2024 -> octobre 2026) dont les agrégats d'octobre 2026 retombent EXACTEMENT sur ces CSV :
  - production polymères journalière (PEBD + PP) = data/production_journaliere.csv ;
  - disponibilité journalière par unité          = data/disponibilite_unites.csv ;
  - avis d'arrêt non planifié d'octobre           = data/arrets.csv.
Les 23 autres mois sont simulés librement (graine fixe : résultats identiques à chaque lancement).

Tables produites (powerbi/donnees/) :
  Fait_Production_Horaire  105 120 lignes : 730 jours x 24 h x 6 lignes de production
  Fait_Plan                  2 920 lignes : plan journalier par unité
  Fait_Arrets                 ~250 lignes : avis SAP PM d'arrêt non planifié
  Dim_Date, Dim_Unite, Dim_Equipement, Dim_Cause

Lancer depuis la racine du dépôt :  python scripts/generer_donnees_powerbi.py
Dépendances : pandas, numpy, openpyxl (pour le classeur Excel).
"""
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "powerbi" / "donnees"
rng = np.random.default_rng(2026)

DEBUT, FIN = pd.Timestamp("2024-11-01"), pd.Timestamp("2026-10-31")
JOURS = pd.date_range(DEBUT, FIN, freq="D")
HEURES = pd.date_range(DEBUT, FIN + pd.Timedelta(hours=23), freq="h")
NJ, NH = len(JOURS), len(HEURES)                       # 730 jours, 17 520 heures
OCT26 = pd.Timestamp("2026-10-01")
H_OCT = int((OCT26 - DEBUT) / pd.Timedelta(hours=1))   # index de la 1re heure d'octobre 2026
J_OCT = int((OCT26 - DEBUT).days)

# ---------------------------------------------------------------- dimensions
UNITES = pd.DataFrame([
    # code, libellé (identique aux CSV), famille, nb lignes, ordre d'affichage
    ("VAPO", "Vapocraqueur", "Intermédiaire", 1, 1),
    ("PEBD", "Polyéthylène BD", "Polymère", 2, 2),
    ("PP", "Polypropylène", "Polymère", 2, 3),
    ("BUTA", "Butadiène", "Intermédiaire", 1, 4),
], columns=["Code_Unite", "Unite", "Famille", "Nb_Lignes", "Ordre"])
UNITES["Objectif_Dispo"] = 0.95

# Débit nominal d'une ligne qui tourne (t/h) et pertes "micro-arrêts" moyennes (min/jour/ligne)
LIGNES = {
    "VAPO-L1": dict(unite="VAPO", debit=100.0, micro=18),
    "PEBD-L1": dict(unite="PEBD", debit=27.0, micro=40),
    "PEBD-L2": dict(unite="PEBD", debit=27.0, micro=40),
    "PP-L1": dict(unite="PP", debit=16.2, micro=55),
    "PP-L2": dict(unite="PP", debit=16.2, micro=55),
    "BUTA-L1": dict(unite="BUTA", debit=12.5, micro=85),
}
CODE_UNITE = dict(zip(UNITES.Unite, UNITES.Code_Unite))

EQUIPEMENTS = pd.DataFrame([
    ("F-101", "Four de craquage F-101", "Four", "VAPO-L1"),
    ("F-102", "Four de craquage F-102", "Four", "VAPO-L1"),
    ("K-150", "Compresseur de gaz craqué K-150", "Compresseur", "VAPO-L1"),
    ("P-130", "Pompe d'huile de trempe P-130", "Pompe", "VAPO-L1"),
    ("E-120", "Échangeur de trempe E-120", "Échangeur", "VAPO-L1"),
    ("C-160", "Colonne de fractionnement C-160", "Colonne", "VAPO-L1"),
    ("AT-45", "Analyseur AT-45", "Analyseur", "VAPO-L1"),
    ("K-410", "Hypercompresseur K-410", "Compresseur", "PEBD-L1"),
    ("R-420", "Réacteur tubulaire R-420", "Réacteur", "PEBD-L1"),
    ("P-118", "Pompe P-118", "Pompe", "PEBD-L1"),
    ("X-430", "Extrudeuse X-430", "Extrudeuse", "PEBD-L1"),
    ("K-411", "Hypercompresseur K-411", "Compresseur", "PEBD-L2"),
    ("R-421", "Réacteur tubulaire R-421", "Réacteur", "PEBD-L2"),
    ("P-119", "Pompe P-119", "Pompe", "PEBD-L2"),
    ("X-431", "Extrudeuse X-431", "Extrudeuse", "PEBD-L2"),
    ("K-201", "Compresseur K-201", "Compresseur", "PP-L1"),
    ("R-210", "Réacteur R-210", "Réacteur", "PP-L1"),
    ("X-101", "Extrudeuse X-101", "Extrudeuse", "PP-L1"),
    ("P-220", "Pompe P-220", "Pompe", "PP-L1"),
    ("K-202", "Compresseur K-202", "Compresseur", "PP-L2"),
    ("R-211", "Réacteur R-211", "Réacteur", "PP-L2"),
    ("X-102", "Extrudeuse X-102", "Extrudeuse", "PP-L2"),
    ("P-221", "Pompe P-221", "Pompe", "PP-L2"),
    ("E-310", "Échangeur E-310", "Échangeur", "BUTA-L1"),
    ("C-320", "Colonne d'extraction C-320", "Colonne", "BUTA-L1"),
    ("P-330", "Pompe de solvant P-330", "Pompe", "BUTA-L1"),
    ("K-350", "Compresseur K-350", "Compresseur", "BUTA-L1"),
    ("AT-340", "Analyseur AT-340", "Analyseur", "BUTA-L1"),
], columns=["Code_Equipement", "Equipement", "Type_Equipement", "Code_Ligne"])
EQUIPEMENTS["Code_Unite"] = EQUIPEMENTS.Code_Ligne.map(lambda l: LIGNES[l]["unite"])

CAUSES = pd.DataFrame([
    ("Mécanique", "Technique", 1), ("Électrique", "Technique", 2),
    ("Instrumentation", "Technique", 3), ("Encrassement", "Procédé", 4), ("Procédé", "Procédé", 5),
], columns=["Cause", "Famille_Cause", "Ordre"])

# Cause probable selon le type d'équipement, et impact de l'avis sur la ligne
CAUSE_PAR_TYPE = {
    "Four": {"Encrassement": .5, "Procédé": .3, "Instrumentation": .2},
    "Compresseur": {"Mécanique": .6, "Électrique": .2, "Instrumentation": .2},
    "Pompe": {"Mécanique": .7, "Électrique": .3},
    "Échangeur": {"Encrassement": .7, "Mécanique": .3},
    "Extrudeuse": {"Mécanique": .5, "Électrique": .4, "Instrumentation": .1},
    "Réacteur": {"Procédé": .6, "Instrumentation": .4},
    "Colonne": {"Encrassement": .5, "Procédé": .5},
    "Analyseur": {"Instrumentation": 1.0},
}
IMPACT_PAR_TYPE = {  # équipements redondés (pompe de secours, analyseur) : souvent sans arrêt de ligne
    "Pompe": {"Arrêt ligne": .3, "Débit réduit": .3, "Sans impact": .4},
    "Analyseur": {"Débit réduit": .3, "Sans impact": .7},
}
IMPACT_DEFAUT = {"Arrêt ligne": .6, "Débit réduit": .3, "Sans impact": .1}

# Grands arrêts PLANIFIÉS (pris en compte dans le plan) : ligne, début, nb de jours
ARRETS_PLANIFIES = [("PEBD-L2", "2025-03-03", 5), ("VAPO-L1", "2025-05-12", 10),
                    ("PP-L1", "2025-06-16", 5), ("PEBD-L1", "2026-02-09", 4),
                    ("BUTA-L1", "2026-04-13", 7)]

# Avis d'octobre 2026 = data/arrets.csv, complétés de l'heure de début et de l'impact
AVIS_OCTOBRE = {  # équipement -> (ligne, heure de début, impact)
    "Compresseur K-201": ("PP-L1", "2026-10-14 10:00", "Arrêt ligne"),
    "Échangeur E-310": ("BUTA-L1", "2026-10-23 08:00", "Arrêt ligne"),
    "Extrudeuse X-102": ("PP-L2", "2026-10-15 13:00", "Arrêt ligne"),
    "Pompe P-118": ("PEBD-L1", "2026-10-08 09:00", "Débit réduit"),   # pompe de secours démarrée
    "Analyseur AT-45": ("VAPO-L1", "2026-10-27 15:00", "Sans impact"),  # dispo du jour = 100 %
}


def choix(dico):
    """Tire une clé d'un dictionnaire {valeur: probabilité}."""
    return rng.choice(list(dico), p=list(dico.values()))


def ajouter_intervalle(tableau, debut, duree_h, valeur=None):
    """Répartit un intervalle [debut, debut + durée] sur les heures du tableau (minutes par heure).
    Si `valeur` est donnée, écrit cette valeur (facteur de débit) au lieu des minutes."""
    t0 = (pd.Timestamp(debut) - DEBUT) / pd.Timedelta(minutes=1)
    t1 = t0 + duree_h * 60
    for h in range(int(t0 // 60), min(int(np.ceil(t1 / 60)), NH)):
        recouvrement = min(t1, (h + 1) * 60) - max(t0, h * 60)
        if recouvrement > 0:
            if valeur is None:
                tableau[h] += recouvrement
            else:
                tableau[h] = min(tableau[h], valeur)


# ---------------------------------------------------------------- 1. arrêts planifiés
arret_np = {l: np.zeros(NH) for l in LIGNES}     # minutes d'arrêt non planifié par heure
arret_pl = {l: np.zeros(NH) for l in LIGNES}     # minutes d'arrêt planifié
micro = {l: np.zeros(NH) for l in LIGNES}        # micro-arrêts (< 1 h, sans avis)
facteur = {l: np.ones(NH) for l in LIGNES}       # facteur de débit (débit réduit, redémarrage)

for ligne, debut, nb_jours in ARRETS_PLANIFIES:
    ajouter_intervalle(arret_pl[ligne], debut, nb_jours * 24)

# ---------------------------------------------------------------- 2. avis non planifiés simulés
avis = []
for ligne in LIGNES:
    equip_ligne = EQUIPEMENTS[EQUIPEMENTS.Code_Ligne == ligne]
    for j, jour in enumerate(JOURS):
        if jour >= OCT26 or rng.random() > 0.045:      # ~1,4 avis par ligne et par mois
            continue
        eq = equip_ligne.sample(1, random_state=int(rng.integers(1e9))).iloc[0]
        duree = float(np.clip(np.round(rng.lognormal(np.log(3.0), 0.8) * 2) / 2, 0.5, 36))
        debut = jour + pd.Timedelta(minutes=int(rng.integers(0, 24 * 60 // 30)) * 30)
        h0 = int((debut - DEBUT) / pd.Timedelta(hours=1))
        h1 = int(np.ceil(h0 + duree))
        # pas de chevauchement avec un arrêt planifié / un autre avis, ni de débordement sur octobre
        if debut + pd.Timedelta(hours=duree) > OCT26 or arret_pl[ligne][h0:h1].any() \
                or arret_np[ligne][h0:h1].any() or (facteur[ligne][h0:h1] < 1).any():
            continue
        impact = choix(IMPACT_PAR_TYPE.get(eq.Type_Equipement, IMPACT_DEFAUT))
        avis.append(dict(Date_Heure_Debut=debut, Code_Ligne=ligne, Code_Equipement=eq.Code_Equipement,
                         Cause=choix(CAUSE_PAR_TYPE[eq.Type_Equipement]), Impact_Ligne=impact,
                         Duree_h=duree))
        if impact == "Arrêt ligne":
            ajouter_intervalle(arret_np[ligne], debut, duree)
            if duree >= 3:   # redémarrage progressif sur 6 h
                for k, f in enumerate(np.linspace(0.6, 0.95, 6)):
                    if h1 + k < NH:
                        facteur[ligne][h1 + k] = min(facteur[ligne][h1 + k], f)
        elif impact == "Débit réduit":
            ajouter_intervalle(facteur[ligne], debut, duree, valeur=0.7)

# Avis d'octobre 2026 (référence client)
ref_arrets = pd.read_csv(RACINE / "data" / "arrets.csv")
for r in ref_arrets.itertuples():
    ligne, debut, impact = AVIS_OCTOBRE[r.equipement]
    code_eq = r.equipement.split()[-1]
    avis.append(dict(Date_Heure_Debut=pd.Timestamp(debut), Code_Ligne=ligne, Code_Equipement=code_eq,
                     Cause=r.cause, Impact_Ligne=impact, Duree_h=float(r.duree_h)))
    if impact == "Arrêt ligne":
        ajouter_intervalle(arret_np[ligne], debut, r.duree_h)
    elif impact == "Débit réduit":
        ajouter_intervalle(facteur[ligne], debut, r.duree_h, valeur=0.85)

# ---------------------------------------------------------------- 3. micro-arrêts
def placer_micro(ligne, j, total_cmin):
    """Place `total_cmin` centièmes de minute de micro-arrêts dans le jour j de la ligne,
    par morceaux de 5 à 45 min, dans les heures où la ligne tourne encore."""
    h_jour = np.arange(j * 24, j * 24 + 24)
    reste = int(round(total_cmin))
    essais = 0
    while reste > 0:
        libre = 60 - arret_np[ligne][h_jour] - arret_pl[ligne][h_jour] - micro[ligne][h_jour]
        candidates = h_jour[libre > 0.01]
        if len(candidates) == 0:
            raise ValueError(f"Plus de place pour les micro-arrêts : {ligne}, jour {j}")
        h = rng.choice(candidates)
        morceau = min(reste, int(rng.integers(500, 4500)), int(round((60 - arret_np[ligne][h]
                      - arret_pl[ligne][h] - micro[ligne][h]) * 100)))
        micro[ligne][h] += morceau / 100
        reste -= morceau
        essais += 1
        if essais > 10_000:
            raise RuntimeError("Boucle de placement bloquée")


for ligne, p in LIGNES.items():
    for j in range(J_OCT):                      # avant octobre 2026 : simulation libre
        h = slice(j * 24, (j + 1) * 24)
        libre = 1440 - arret_pl[ligne][h].sum() - arret_np[ligne][h].sum()
        # micro-arrêts proportionnels au temps où la ligne tourne (0 si arrêt toute la journée)
        total = rng.gamma(2.0, p["micro"] / 2) * libre / 1440 * 100
        placer_micro(ligne, j, min(total, libre * 0.3 * 100))

# Octobre 2026 : le temps d'arrêt journalier de chaque unité est imposé par la référence
ref_dispo = pd.read_csv(RACINE / "data" / "disponibilite_unites.csv", parse_dates=["date"])
for r in ref_dispo.itertuples():
    code = CODE_UNITE[r.unite]
    lignes_u = [l for l, p in LIGNES.items() if p["unite"] == code]
    j = int((r.date - DEBUT).days)
    # arrêt total imposé (en centièmes de minute) = (1 - dispo) x 1 440 min x nb de lignes
    imposé = int(round((1 - r.disponibilite) * 1440 * len(lignes_u) * 100))
    deja = sum(int(round(arret_np[l][j * 24:(j + 1) * 24].sum() * 100)) for l in lignes_u)
    reste = imposé - deja
    assert reste >= 0, f"Avis plus longs que l'arrêt de référence : {r.unite} {r.date:%d/%m}"
    # répartition du reste entre les lignes de l'unité (au prorata du temps encore disponible)
    libres = np.array([1440 * 100 - arret_np[l][j * 24:(j + 1) * 24].sum() * 100 for l in lignes_u])
    parts = np.floor(reste * libres / libres.sum()).astype(int)
    parts[0] += reste - parts.sum()
    for l, part in zip(lignes_u, parts):
        placer_micro(l, j, part)

# ---------------------------------------------------------------- 4. production horaire
mois = HEURES.month.values
saison = np.where(np.isin(mois, [7, 8]), 0.98, 1.0)      # chaleur estivale : débit -2 %
lignes_fait = []
for ligne, p in LIGNES.items():
    derive = np.zeros(NJ)                              # dérive journalière AR(1)
    for j in range(1, NJ):
        derive[j] = 0.6 * derive[j - 1] + rng.normal(0, 0.012)
    efficacite = 1.0 + np.repeat(derive, 24) + rng.normal(0, 0.008, NH)
    marche = 60 - arret_np[ligne] - arret_pl[ligne] - micro[ligne]
    assert (marche >= -1e-9).all(), ligne
    prod = p["debit"] * marche / 60 * np.clip(efficacite * saison, 0.8, 1.06) * facteur[ligne]
    lignes_fait.append(pd.DataFrame({
        "Date_Heure": HEURES, "Code_Ligne": ligne, "Code_Unite": p["unite"], "Production_t": prod,
        "Minutes_Calendrier": 60.0, "Minutes_Marche": marche.round(2),
        "Minutes_Arret_Non_Planifie": arret_np[ligne].round(2),
        "Minutes_Arret_Planifie": arret_pl[ligne].round(2),
        "Minutes_Micro_Arret": micro[ligne].round(2),
    }))
fait = pd.concat(lignes_fait, ignore_index=True)
fait["Date"] = fait.Date_Heure.dt.normalize()

# Octobre 2026 : production polymères journalière recalée exactement sur la référence.
# Jours d'incident PP (14-16) : l'écart est porté par le PP ; sinon répartition proportionnelle.
ref_prod = pd.read_csv(RACINE / "data" / "production_journaliere.csv", parse_dates=["date"])
poly = fait.Code_Unite.isin(["PEBD", "PP"])
for r in ref_prod.itertuples():
    jour = fait.Date == r.date
    if r.date.day in (14, 15, 16):
        pebd = fait.loc[jour & (fait.Code_Unite == "PEBD"), "Production_t"].sum()
        masque = jour & (fait.Code_Unite == "PP")
        fait.loc[masque, "Production_t"] *= (r.production_t - pebd) / fait.loc[masque, "Production_t"].sum()
    else:
        masque = jour & poly
        fait.loc[masque, "Production_t"] *= r.production_t / fait.loc[masque, "Production_t"].sum()

# Arrondi au kg, puis correction du résidu d'arrondi sur l'heure la plus productive du jour
fait["Production_kg"] = (fait.Production_t * 1000).round().astype("int64")
for r in ref_prod.itertuples():
    masque = (fait.Date == r.date) & poly
    residu = int(round(r.production_t * 1000)) - fait.loc[masque, "Production_kg"].sum()
    fait.loc[fait.loc[masque, "Production_kg"].idxmax(), "Production_kg"] += residu
fait["Production_t"] = fait.Production_kg / 1000
fait["Heure"] = fait.Date_Heure.dt.hour
fait["Poste"] = pd.cut(fait.Heure, [-1, 5, 13, 21, 23], labels=["Nuit", "Matin", "Après-midi", "Nuit"],
                       ordered=False).astype(str)
fait = fait[["Date_Heure", "Date", "Heure", "Poste", "Code_Unite", "Code_Ligne", "Production_t",
             "Minutes_Calendrier", "Minutes_Marche", "Minutes_Arret_Non_Planifie",
             "Minutes_Arret_Planifie", "Minutes_Micro_Arret"]]

# ---------------------------------------------------------------- 5. plan journalier par unité
PLAN_T_J = {  # plan journalier "pleine marche" par unité, par année
    2024: {"VAPO": 2300, "PEBD": 1220, "PP": 730, "BUTA": 280},
    2025: {"VAPO": 2300, "PEBD": 1220, "PP": 730, "BUTA": 280},
    2026: {"VAPO": 2350, "PEBD": 1250, "PP": 750, "BUTA": 290},
}
pl_jour = (fait.assign(Pl=fait.Minutes_Arret_Planifie)
           .groupby(["Date", "Code_Unite"], as_index=False)
           .agg(Pl=("Pl", "sum"), Cal=("Minutes_Calendrier", "sum")))
pl_jour["Plan_t"] = [PLAN_T_J[d.year][u] * (1 - pl / cal) for d, u, pl, cal
                     in zip(pl_jour.Date, pl_jour.Code_Unite, pl_jour.Pl, pl_jour.Cal)]
fait_plan = pl_jour[["Date", "Code_Unite"]].assign(Plan_t=pl_jour.Plan_t.round(1))

# ---------------------------------------------------------------- 6. table des avis
arrets = pd.DataFrame(avis).sort_values("Date_Heure_Debut", ignore_index=True)
arrets["Num_Avis"] = 30_045_000 + np.arange(len(arrets)) * 7 + rng.integers(0, 7, len(arrets))
arrets["Date"] = arrets.Date_Heure_Debut.dt.normalize()
arrets["Date_Heure_Fin"] = arrets.Date_Heure_Debut + pd.to_timedelta(arrets.Duree_h, unit="h")
arrets = arrets.merge(EQUIPEMENTS[["Code_Equipement", "Equipement"]], on="Code_Equipement")
arrets["Code_Unite"] = arrets.Code_Ligne.map(lambda l: LIGNES[l]["unite"])
arrets["Statut"] = "Clôturé"
arrets = arrets.sort_values("Date_Heure_Debut", ignore_index=True)[[
    "Num_Avis", "Date", "Date_Heure_Debut", "Date_Heure_Fin", "Code_Unite", "Code_Ligne",
    "Code_Equipement", "Equipement", "Cause", "Impact_Ligne", "Duree_h", "Statut"]]

# ---------------------------------------------------------------- 7. calendrier (années complètes)
dates = pd.date_range("2024-01-01", "2026-12-31", freq="D")
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
        "octobre", "novembre", "décembre"]
MOIS_COURT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.",
              "nov.", "déc."]
JOURS_SEM = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
dim_date = pd.DataFrame({
    "Date": dates, "Annee": dates.year, "Trimestre": "T" + dates.quarter.astype(str),
    "Mois_Num": dates.month, "Mois": [MOIS[m - 1] for m in dates.month],
    "Mois_Annee": [f"{MOIS_COURT[d.month - 1]} {d.year}" for d in dates],
    "Cle_Mois": dates.year * 100 + dates.month, "Jour": dates.day,
    "Jour_Semaine": [JOURS_SEM[d] for d in dates.dayofweek], "Num_Jour_Semaine": dates.dayofweek + 1,
    "Semaine_ISO": dates.isocalendar().week.values.astype(int),
    "Avec_Donnees": (dates >= DEBUT) & (dates <= FIN),
})

# ---------------------------------------------------------------- 8. export
tables = {
    "Fait_Production_Horaire": fait, "Fait_Plan": fait_plan, "Fait_Arrets": arrets,
    "Dim_Date": dim_date, "Dim_Unite": UNITES, "Dim_Equipement": EQUIPEMENTS, "Dim_Cause": CAUSES,
}
SORTIE.mkdir(parents=True, exist_ok=True)
for nom, df in tables.items():
    # CSV : séparateur virgule, décimale point, UTF-8 avec BOM (accents lisibles dans Excel).
    # Colonne "Date" sans heure ; colonnes "Date_Heure..." avec heure.
    csv = df.copy()
    for col in csv.columns:
        if col == "Date":
            csv[col] = csv[col].dt.strftime("%Y-%m-%d")
        elif col.startswith("Date_Heure"):
            csv[col] = csv[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    csv.to_csv(SORTIE / f"{nom}.csv", index=False, encoding="utf-8-sig")
with pd.ExcelWriter(SORTIE / "donnees_pilotage_production.xlsx", engine="openpyxl") as xl:
    for nom, df in tables.items():
        xls = df.copy()
        if "Date" in xls.columns:
            xls["Date"] = xls["Date"].dt.date      # cellule Date (sans heure) dans Excel
        xls.to_excel(xl, sheet_name=nom, index=False)

for nom, df in tables.items():
    print(f"{nom:<25} {len(df):>8,} lignes".replace(",", " "))
print("Fichiers écrits dans", SORTIE)
