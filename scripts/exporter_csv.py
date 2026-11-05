"""Régénère les CSV de data/ à partir du générateur fictif (graine fixe : résultats identiques)."""
from pathlib import Path

from donnees_fictives import arrets, df_dispo, df_prod

sortie = Path(__file__).resolve().parents[1] / "data"
sortie.mkdir(exist_ok=True)
df_prod.to_csv(sortie / "production_journaliere.csv", index=False)
df_dispo.to_csv(sortie / "disponibilite_unites.csv", index=False)
arrets.to_csv(sortie / "arrets.csv", index=False)
print("CSV écrits dans", sortie)
