"""Données FICTIVES pour l'exemple de tableau de bord (graine fixe, reproductible)."""
import numpy as np, pandas as pd
rng = np.random.default_rng(42)
jours = pd.date_range("2026-10-01", "2026-10-31", freq="D")
unites = {"Vapocraqueur": 0.97, "Polypropylène": 0.93, "Polyéthylène BD": 0.95, "Butadiène": 0.91}
plan = 2000.0  # t/j polymères (PP + PEBD), fictif
prod = plan * rng.normal(0.985, 0.02, len(jours))
# incident fictif : arrêt partiel ligne PP du 14 au 16
prod[13:16] = plan * np.array([0.78, 0.72, 0.86])
prod[22] = plan * 0.9
df_prod = pd.DataFrame({"date": jours.date, "production_t": prod.round(0), "plan_t": plan})
dispo = []
for u, base in unites.items():
    for d in jours:
        v = min(1.0, rng.normal(base + 0.02, 0.015))
        if u == "Polypropylène" and d.day in (14, 15, 16): v = [0.70, 0.62, 0.81][d.day - 14]
        if u == "Butadiène" and d.day == 23: v = 0.75
        dispo.append({"date": d.date(), "unite": u, "disponibilite": round(v, 3)})
df_dispo = pd.DataFrame(dispo)
arrets = pd.DataFrame([
    {"date": "2026-10-14", "equipement": "Compresseur K-201", "unite": "Polypropylène", "duree_h": 22.5, "cause": "Mécanique"},
    {"date": "2026-10-23", "equipement": "Échangeur E-310", "unite": "Butadiène", "duree_h": 6.0, "cause": "Encrassement"},
    {"date": "2026-10-15", "equipement": "Extrudeuse X-102", "unite": "Polypropylène", "duree_h": 5.5, "cause": "Électrique"},
    {"date": "2026-10-08", "equipement": "Pompe P-118", "unite": "Polyéthylène BD", "duree_h": 3.0, "cause": "Mécanique"},
    {"date": "2026-10-27", "equipement": "Analyseur AT-45", "unite": "Vapocraqueur", "duree_h": 2.0, "cause": "Instrumentation"},
])
