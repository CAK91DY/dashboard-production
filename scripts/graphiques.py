"""Graphiques PNG à remettre au client (données FICTIVES), prêts pour un support de présentation.

- 01 à 04 : octobre 2026, calculés depuis les CSV de référence de data/ (mêmes chiffres que la page web).
- 05 et 06 : vision 24 mois, depuis le jeu détaillé powerbi/donnees/ (lancer d'abord
  scripts/generer_donnees_powerbi.py).

Lancer depuis la racine du dépôt :  python scripts/graphiques.py
Dépendances : pandas, matplotlib.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "graphiques"
SORTIE.mkdir(exist_ok=True)

OBJECTIF = 0.95
BLEU, GRIS, TEXTE, TEXTE2, ALERTE, ORANGE = "#2a78d6", "#5b6473", "#1b2433", "#8a92a0", "#b5482a", "#e07b4f"
CHALEUR = [(0.97, "#dbe8fb", "≥ 97 %"), (0.93, "#9ec5f4", "93–97 %"), (0.85, "#3f7fd8", "85–93 %"),
           (0.0, "#163d73", "< 85 %")]
MOIS_COURT = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]

plt.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"], "font.size": 10, "axes.edgecolor": "#e3e6eb",
    "axes.labelcolor": TEXTE2, "xtick.color": TEXTE2, "ytick.color": TEXTE2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.titleweight": "semibold", "axes.titlesize": 12,
    "axes.titlelocation": "left", "axes.titlecolor": TEXTE, "figure.dpi": 100,
})


def fr(x, d=0):
    """Nombre au format français : 59739 -> '59 739', 0.5 -> '0,5'."""
    return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


def pct(x, d=1):
    return f"{fr(x * 100, d)} %"


def enregistrer(fig, nom):
    fig.text(0.01, -0.04, "Données entièrement fictives", fontsize=8, color=TEXTE2)
    fig.savefig(SORTIE / nom, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("écrit :", SORTIE / nom)


# ------------------------------------------------------------------ données de référence
prod = pd.read_csv(RACINE / "data" / "production_journaliere.csv", parse_dates=["date"])
dispo = pd.read_csv(RACINE / "data" / "disponibilite_unites.csv", parse_dates=["date"])
arrets = pd.read_csv(RACINE / "data" / "arrets.csv", parse_dates=["date"])
mois = f"{MOIS_COURT[prod.date.iloc[0].month - 1].rstrip('.')}"
periode = prod.date.iloc[0].strftime("%m/%Y")

# 01 — Production journalière vs plan
fig, ax = plt.subplots(figsize=(9, 4))
incident = prod.production_t < 0.9 * prod.plan_t
i0 = prod.production_t.idxmin()
deb, fin = i0, i0
while deb > 0 and incident[deb - 1]:
    deb -= 1
while fin < len(prod) - 1 and incident[fin + 1]:
    fin += 1
ax.axvspan(prod.date[deb] - pd.Timedelta(hours=12), prod.date[fin] + pd.Timedelta(hours=12),
           color=ORANGE, alpha=0.12, lw=0)
ax.plot(prod.date, prod.plan_t, color=GRIS, lw=1.5, ls=(0, (5, 4)), label="Plan")
ax.plot(prod.date, prod.production_t, color=BLEU, lw=2, label="Production polymères")
ax.scatter([prod.date[i0]], [prod.production_t[i0]], color=BLEU, s=36, zorder=3, edgecolor="white", lw=1.5)
a = arrets[(arrets.date >= prod.date[deb]) & (arrets.date <= prod.date[fin])].nlargest(1, "duree_h")
libelle = f"{fr(prod.production_t[i0])} t — arrêt {a.equipement.iloc[0][0].lower()}{a.equipement.iloc[0][1:]}" \
    if len(a) else f"{fr(prod.production_t[i0])} t"
ax.annotate(libelle, (prod.date[i0], prod.production_t[i0]), xytext=(10, -2), textcoords="offset points",
            color=ALERTE, fontsize=9.5, fontweight="semibold", va="center")
ax.set_ylim(1400, 2200)
ax.yaxis.set_major_formatter(lambda v, _: fr(v))
ax.set_xticks(prod.date[::5].tolist() + [prod.date.iloc[-1]])
ax.set_xticklabels([f"{d.day} {MOIS_COURT[d.month - 1]}" for d in prod.date[::5]] + [f"{prod.date.iloc[-1].day} {MOIS_COURT[prod.date.iloc[-1].month - 1]}"])
ax.grid(axis="y", color="#eef0f3")
ax.set_title(f"Production journalière vs plan (t/j) — réalisation {pct(prod.production_t.sum() / prod.plan_t.sum())}")
ax.legend(loc="lower left", frameon=False, ncol=2)
enregistrer(fig, "01_production_vs_plan.png")

# 02 — Disponibilité moyenne par unité
moy = dispo.groupby("unite").disponibilite.mean().sort_values()
fig, ax = plt.subplots(figsize=(7, 3.4))
ax.barh(moy.index, moy.values - 0.85, left=0.85, color=BLEU, height=0.55)
ax.axvline(OBJECTIF, color=GRIS, ls=(0, (4, 3)), lw=1.5)
ax.set_ylim(-0.9, len(moy) - 0.5)
ax.text(OBJECTIF + 0.002, -0.75, f"objectif {pct(OBJECTIF, 0)}", ha="left", color=TEXTE2, fontsize=9)
for i, (u, v) in enumerate(moy.items()):
    sous = v < OBJECTIF
    ax.text(max(v, OBJECTIF) + 0.002, i, pct(v) + ("  ▼ sous l'objectif" if sous else ""),
            va="center", fontsize=9.5, fontweight="semibold", color=ALERTE if sous else TEXTE)
ax.set_xlim(0.85, 1.03)
ax.set_xticks([0.85, 0.90, 0.95, 1.0])
ax.xaxis.set_major_formatter(lambda v, _: pct(v, 0))
ax.tick_params(axis="y", length=0)
ax.set_title(f"Disponibilité moyenne par unité — moyenne {pct(moy.mean())}")
enregistrer(fig, "02_disponibilite_par_unite.png")

# 03 — Carte de chaleur
ordre = moy.index[::-1]
grille = dispo.pivot(index="unite", columns="date", values="disponibilite").loc[ordre]
fig, ax = plt.subplots(figsize=(10, 2.8))
for r, u in enumerate(grille.index):
    for c, v in enumerate(grille.loc[u]):
        couleur = next(col for seuil, col, _ in CHALEUR if v >= seuil)
        ax.add_patch(plt.Rectangle((c + 0.06, r + 0.06), 0.88, 0.88, color=couleur, lw=0))
ax.set_xlim(0, grille.shape[1])
ax.set_ylim(grille.shape[0], 0)
ax.set_yticks([r + 0.5 for r in range(len(ordre))], ordre)
ax.set_xticks([c + 0.5 for c in range(grille.shape[1])], [str(d.day) if d.day in (1, 10, 20, 31) else ""
                                                          for d in grille.columns])
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
ax.legend(handles=[Patch(color=c, label=l) for _, c, l in CHALEUR], loc="upper center",
          bbox_to_anchor=(0.5, -0.18), ncol=4, frameon=False, fontsize=9)
ax.set_title("Disponibilité jour par jour (plus foncé = moins disponible)")
enregistrer(fig, "03_disponibilite_jour_par_jour.png")

# 04 — Arrêts non planifiés du mois
tri = arrets.sort_values("duree_h")
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.barh([f"{e}  ({d:%d/%m})" for e, d in zip(tri.equipement, tri.date)], tri.duree_h, color=BLEU, height=0.55)
for i, r in enumerate(tri.itertuples()):
    ax.text(r.duree_h + 0.3, i, f"{fr(r.duree_h, 1)} h · {r.cause} · {r.unite}", va="center", fontsize=9, color=TEXTE)
ax.set_xlim(0, tri.duree_h.max() * 1.75)
ax.set_xticks([])
for s in ["bottom", "left"]:
    ax.spines[s].set_visible(False)
ax.tick_params(axis="y", length=0)
principale = arrets.groupby("cause").duree_h.sum().sort_values(ascending=False)
ax.set_title(f"Arrêts non planifiés : {fr(arrets.duree_h.sum(), 1)} h, {len(arrets)} avis — "
             f"{principale.index[0]} {pct(principale.iloc[0] / arrets.duree_h.sum(), 0)}")
enregistrer(fig, "04_arrets_non_planifies.png")

# ------------------------------------------------------------------ vision 24 mois (jeu détaillé)
D = RACINE / "powerbi" / "donnees"
if (D / "Fait_Production_Horaire.csv").exists():
    unites = pd.read_csv(D / "Dim_Unite.csv")
    fait = pd.read_csv(D / "Fait_Production_Horaire.csv", parse_dates=["Date"]).merge(unites, on="Code_Unite")
    plan = pd.read_csv(D / "Fait_Plan.csv", parse_dates=["Date"]).merge(unites, on="Code_Unite")
    avis = pd.read_csv(D / "Fait_Arrets.csv", parse_dates=["Date"])
    fait["Mois"] = fait.Date.dt.to_period("M")
    plan["Mois"] = plan.Date.dt.to_period("M")
    poly = fait[fait.Famille == "Polymère"].groupby("Mois").Production_t.sum()
    plan_poly = plan[plan.Famille == "Polymère"].groupby("Mois").Plan_t.sum()
    realisation = poly / plan_poly
    dispo_m = (fait.groupby(["Mois", "Unite"]).apply(lambda g: g.Minutes_Marche.sum() / g.Minutes_Calendrier.sum())
               .groupby("Mois").mean())   # moyenne simple des unités, comme la page et le DAX
    etiquettes = [f"{MOIS_COURT[m.month - 1]}\n{m.year}" if m.month in (1, 11) or i == 0 else MOIS_COURT[m.month - 1]
                  for i, m in enumerate(realisation.index)]

    # 05 — deux petits graphiques empilés (pas de double axe)
    fig, (h, b) = plt.subplots(2, 1, figsize=(10, 5.2), sharex=True)
    x = range(len(realisation))
    h.plot(x, realisation.values, color=BLEU, lw=2, marker="o", ms=3.5)
    h.axhline(1, color=GRIS, ls=(0, (5, 4)), lw=1.2)
    h.set_title("Réalisation du plan polymères, par mois")
    h.yaxis.set_major_formatter(lambda v, _: pct(v, 0))
    b.plot(x, dispo_m.values, color=BLEU, lw=2, marker="o", ms=3.5)
    b.axhline(OBJECTIF, color=GRIS, ls=(0, (5, 4)), lw=1.2)
    b.text(0, OBJECTIF, " objectif 95 %", color=TEXTE2, fontsize=8.5, va="bottom", ha="left")
    b.set_title("Disponibilité moyenne des unités, par mois")
    b.yaxis.set_major_formatter(lambda v, _: pct(v, 0))
    for axe in (h, b):
        axe.grid(axis="y", color="#eef0f3")
    b.set_xticks(list(x), etiquettes, fontsize=8)
    for axe, serie in ((h, realisation), (b, dispo_m)):
        axe.annotate(pct(serie.iloc[-1]), (len(x) - 1, serie.iloc[-1]), xytext=(6, 0),
                     textcoords="offset points", va="center", fontsize=9, fontweight="semibold", color=TEXTE)
    fig.tight_layout()
    enregistrer(fig, "05_tendance_24_mois.png")

    # 06 — Pareto des causes d'arrêt sur 12 mois glissants
    # 12 mois calendaires complets (nov. 2025 -> oct. 2026), comme DATESINPERIOD en DAX
    debut12 = fait.Date.max() + pd.Timedelta(days=1) - pd.DateOffset(months=12)
    a12 = avis[avis.Date >= debut12]
    causes = a12.groupby("Cause").Duree_h.sum().sort_values(ascending=False)
    cumul = causes.cumsum() / causes.sum()
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.bar(causes.index, causes.values, color=BLEU, width=0.6)
    for i, (c, v) in enumerate(causes.items()):
        ax.text(i, v + causes.max() * 0.02, f"{fr(v, 0)} h\n{pct(cumul[c], 0)} cumulé", ha="center", fontsize=8.5,
                color=TEXTE)
    ax.set_ylim(0, causes.max() * 1.25)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="x", length=0)
    ax.set_title(f"Heures d'arrêt non planifié par cause — 12 derniers mois ({len(a12)} avis, {fr(causes.sum(), 0)} h)")
    enregistrer(fig, "06_pareto_causes_12_mois.png")
