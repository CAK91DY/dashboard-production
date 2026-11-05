"""Vérifie les chiffres du tableau de bord : on les recalcule en Python depuis les CSV et on les
compare aux chiffres de référence du CLAUDE.md (ceux du PDF déjà envoyé au client).

Trois blocs de contrôles :
  1. les indicateurs d'octobre 2026, recalculés depuis data/ ;
  2. docs/data/ (lu par la page web) est une copie exacte de data/ ;
  3. si le jeu Power BI existe (powerbi/donnees/), ses agrégats d'octobre 2026 retombent
     exactement sur les CSV de référence.

On compare les valeurs telles qu'elles sont AFFICHÉES (arrondies), car ce sont elles que le
client voit. Les calculs suivent les mêmes règles que docs/app.js et powerbi/mesures.dax.

Lancer depuis la racine du dépôt :  python scripts/verifier.py
Code de sortie : 0 si tout est conforme, 1 sinon (utilisable en intégration continue).
"""
import filecmp
import sys
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
DATA = RACINE / "data"
SEUIL_ZONE_ARRET = 0.90   # même règle que la page : jour "en incident" si production < 90 % du plan

# Chiffres de référence (CLAUDE.md). Si un calcul donne autre chose, c'est le code qui est faux.
REFERENCE = {
    "Production du mois (t)": 59739,
    "Plan du mois (t)": 62000,
    "Réalisation du plan (%)": 96.4,
    "Écart au plan (pt)": -3.6,
    "Jour le plus bas (date)": "2026-10-15",
    "Jour le plus bas (t)": 1440,
    "Zone d'incident": "14–16 oct.",
    "Arrêt de la zone d'incident": "Compresseur K-201 (Polypropylène)",
    "Disponibilité moyenne (%)": 95.1,
    "Disponibilité Vapocraqueur (%)": 98.9,
    "Disponibilité Polyéthylène BD (%)": 96.6,
    "Disponibilité Polypropylène (%)": 92.6,
    "Disponibilité Butadiène (%)": 92.2,
    "Arrêts non planifiés (h)": 39.0,
    "Nombre d'avis": 5,
    "Cause principale": "Mécanique",
    "Heures cause principale (h)": 25.5,
    "Part cause principale (%)": 65,
}

resultats = []   # (bloc, contrôle, attendu, obtenu)


def controler(bloc, nom, attendu, obtenu):
    resultats.append((bloc, nom, attendu, obtenu))


# ------------------------------------------------------------------ 1. indicateurs d'octobre 2026
prod = pd.read_csv(DATA / "production_journaliere.csv", parse_dates=["date"])
dispo = pd.read_csv(DATA / "disponibilite_unites.csv", parse_dates=["date"])
arrets = pd.read_csv(DATA / "arrets.csv", parse_dates=["date"])
B1 = "Indicateurs"

total_prod, total_plan = prod.production_t.sum(), prod.plan_t.sum()
realisation = total_prod / total_plan
controler(B1, "Production du mois (t)", REFERENCE["Production du mois (t)"], round(total_prod))
controler(B1, "Plan du mois (t)", REFERENCE["Plan du mois (t)"], round(total_plan))
controler(B1, "Réalisation du plan (%)", REFERENCE["Réalisation du plan (%)"], round(realisation * 100, 1))
# Écart calculé AVANT arrondi (96,35 % - 100 = -3,65 -> -3,6), comme la page et le DAX
controler(B1, "Écart au plan (pt)", REFERENCE["Écart au plan (pt)"], round((realisation - 1) * 100, 1))

i_min = prod.production_t.idxmin()
controler(B1, "Jour le plus bas (date)", REFERENCE["Jour le plus bas (date)"], f"{prod.date[i_min]:%Y-%m-%d}")
controler(B1, "Jour le plus bas (t)", REFERENCE["Jour le plus bas (t)"], round(prod.production_t[i_min]))

# Zone d'incident : jours consécutifs autour du jour le plus bas sous 90 % du plan
incident = prod.production_t < SEUIL_ZONE_ARRET * prod.plan_t
debut = fin = i_min
while debut > 0 and incident[debut - 1]:
    debut -= 1
while fin < len(prod) - 1 and incident[fin + 1]:
    fin += 1
controler(B1, "Zone d'incident", REFERENCE["Zone d'incident"], f"{prod.date[debut].day}–{prod.date[fin].day} oct.")
dans_zone = arrets[(arrets.date >= prod.date[debut]) & (arrets.date <= prod.date[fin])]
plus_long = dans_zone.loc[dans_zone.duree_h.idxmax()]
controler(B1, "Arrêt de la zone d'incident", REFERENCE["Arrêt de la zone d'incident"],
          f"{plus_long.equipement} ({plus_long.unite})")

# Disponibilité : moyenne des jours par unité, puis moyenne SIMPLE des unités (1 unité = 1 poids)
par_unite = dispo.groupby("unite").disponibilite.mean()
controler(B1, "Disponibilité moyenne (%)", REFERENCE["Disponibilité moyenne (%)"], round(par_unite.mean() * 100, 1))
for unite, valeur in par_unite.items():
    cle = f"Disponibilité {unite} (%)"
    controler(B1, cle, REFERENCE.get(cle, "(unité inconnue)"), round(valeur * 100, 1))

total_arrets = arrets.duree_h.sum()
par_cause = arrets.groupby("cause").duree_h.sum().sort_values(ascending=False)
controler(B1, "Arrêts non planifiés (h)", REFERENCE["Arrêts non planifiés (h)"], round(total_arrets, 1))
controler(B1, "Nombre d'avis", REFERENCE["Nombre d'avis"], len(arrets))
controler(B1, "Cause principale", REFERENCE["Cause principale"], par_cause.index[0])
controler(B1, "Heures cause principale (h)", REFERENCE["Heures cause principale (h)"], round(par_cause.iloc[0], 1))
controler(B1, "Part cause principale (%)", REFERENCE["Part cause principale (%)"],
          round(par_cause.iloc[0] / total_arrets * 100))

# ------------------------------------------------------------------ 2. copie lue par la page web
B2 = "Copie docs/data"
for fichier in sorted(DATA.glob("*.csv")):
    copie = RACINE / "docs" / "data" / fichier.name
    identique = copie.exists() and filecmp.cmp(fichier, copie, shallow=False)
    controler(B2, f"docs/data/{fichier.name}", "identique à data/", "identique à data/" if identique
              else ("absent" if not copie.exists() else "DIFFÉRENT"))

# ------------------------------------------------------------------ 3. jeu détaillé Power BI
D = RACINE / "powerbi" / "donnees"
if (D / "Fait_Production_Horaire.csv").exists():
    B3 = "Jeu Power BI"
    unites = pd.read_csv(D / "Dim_Unite.csv")
    fait = pd.read_csv(D / "Fait_Production_Horaire.csv", parse_dates=["Date"]).merge(unites, on="Code_Unite")
    plan = pd.read_csv(D / "Fait_Plan.csv", parse_dates=["Date"]).merge(unites, on="Code_Unite")
    avis = pd.read_csv(D / "Fait_Arrets.csv", parse_dates=["Date"])
    oct_ = fait[(fait.Date >= prod.date.min()) & (fait.Date <= prod.date.max())]

    # 730 jours (nov. 2024 -> oct. 2026) x 24 heures x 6 lignes de production
    attendu_lignes = fait.Date.nunique() * 24 * fait.Code_Ligne.nunique()
    controler(B3, "Lignes horaires (730 j × 24 h × 6 lignes)", 105120, len(fait))
    controler(B3, "Aucune heure manquante ni en double", attendu_lignes, len(fait.drop_duplicates(["Date_Heure", "Code_Ligne"])))

    # Production polymères (PEBD + PP) de chaque jour = production_journaliere.csv
    jour = oct_[oct_.Famille == "Polymère"].groupby("Date").Production_t.sum().round(3)
    ecarts = (jour.reindex(prod.date).values - prod.production_t.values)
    controler(B3, "Production de chaque jour", "31 jours identiques",
              f"{(abs(ecarts) < 1e-6).sum()} jours identiques")

    plan_oct = plan[(plan.Date >= prod.date.min()) & (plan.Date <= prod.date.max()) & (plan.Famille == "Polymère")]
    controler(B3, "Plan polymères (t)", REFERENCE["Plan du mois (t)"], round(plan_oct.Plan_t.sum()))

    # Disponibilité de chaque unité et de chaque jour = disponibilite_unites.csv
    calc = (oct_.groupby(["Date", "Unite"]).apply(lambda g: g.Minutes_Marche.sum() / g.Minutes_Calendrier.sum())
            .round(3).rename("calc").reset_index())
    comp = dispo.merge(calc, left_on=["date", "unite"], right_on=["Date", "Unite"], how="left")
    controler(B3, "Disponibilité de chaque jour × unité", f"{len(dispo)} valeurs identiques",
              f"{(abs(comp.calc - comp.disponibilite) < 1e-9).sum()} valeurs identiques")

    # Le piège du ratio global : il pondère PEBD et PP deux fois (2 lignes chacun)
    ratio_global = oct_.Minutes_Marche.sum() / oct_.Minutes_Calendrier.sum()
    controler(B3, "Ratio global pondéré, piège (%)", 94.9, round(ratio_global * 100, 1))

    # Avis d'octobre = arrets.csv
    avis_oct = avis[(avis.Date >= prod.date.min()) & (avis.Date <= prod.date.max())]
    a = avis_oct[["Date", "Equipement", "Duree_h", "Cause"]].sort_values(["Date", "Equipement"]).values.tolist()
    b = arrets[["date", "equipement", "duree_h", "cause"]].sort_values(["date", "equipement"]).values.tolist()
    controler(B3, "Avis d'octobre", "5 avis identiques à arrets.csv",
              "5 avis identiques à arrets.csv" if a == b else f"{len(a)} avis, différents")

# ------------------------------------------------------------------ rapport
largeur = max(len(r[1]) for r in resultats)
nb_ecarts = 0
bloc_courant = None
for bloc, nom, attendu, obtenu in resultats:
    if bloc != bloc_courant:
        print(f"\n— {bloc} —")
        bloc_courant = bloc
    ok = attendu == obtenu
    nb_ecarts += not ok
    print(f"  {'OK    ' if ok else 'ÉCART '} {nom:<{largeur}}  attendu : {attendu!s:<34} obtenu : {obtenu}")

print(f"\n{len(resultats) - nb_ecarts}/{len(resultats)} contrôles conformes.")
if nb_ecarts:
    print("Au moins un écart : c'est le code qui est faux, pas la référence (voir CLAUDE.md).")
sys.exit(1 if nb_ecarts else 0)
