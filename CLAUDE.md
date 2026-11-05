# Projet 2 — Tableau de bord production et maintenance

## Contexte
Je suis Christophe, Data Analyst BI. Ce dépôt est un **prototype de démonstration** pour un client
industriel (site pétrochimique : vapocraqueur et unités de polymères). Aujourd'hui, ses données sont
dans SAP et analysées dans Excel. Le client veut un pilotage digitalisé : un tableau de bord
fiable, mis à jour automatiquement, qui montre en un coup d'œil si la production suit le plan et
où se trouvent les pertes de disponibilité.

Architecture visée en production (à montrer, pas à construire ici) : extractions SAP (PP, PM)
→ Cloud Storage → BigQuery → transformations SQL avec dbt → tableau de bord (Power BI ou web).

Le dépôt est **public** : il ne contient que des **données fictives** et **aucun nom de client**.

## Public
Direction d'exploitation et maintenance (non techniques) : lecture en moins d'une minute.
Le cabinet de conseil qui présente mon profil : il doit pouvoir ouvrir un lien et comprendre.

## Données (fictives, `data/`)
- `production_journaliere.csv` : `date, production_t, plan_t` (octobre 2026, 31 jours, plan 2 000 t/j).
- `disponibilite_unites.csv` : `date, unite, disponibilite` (0 à 1) pour Vapocraqueur,
  Polypropylène, Polyéthylène BD, Butadiène.
- `arrets.csv` : `date, equipement, unite, duree_h, cause` (5 arrêts non planifiés).
- Générées par `scripts/donnees_fictives.py` (graine fixe 42) ; `scripts/exporter_csv.py`
  les réécrit à l'identique. **Ne pas modifier les données** : elles doivent correspondre au PDF
  et au lien déjà envoyés au client.

## Chiffres de référence (pour vérifier les calculs)
- Production du mois : 59 739 t ; plan : 62 000 t ; réalisation 96,4 % (−3,6 pt).
- Jour le plus bas : 15 octobre, 1 440 t (arrêt du compresseur K-201, polypropylène, 14–16 oct.).
- Disponibilité moyenne : 95,1 % (objectif 95 %). Par unité : Vapocraqueur 98,9 %,
  Polyéthylène BD 96,6 %, Polypropylène 92,6 %, Butadiène 92,2 %.
- Arrêts non planifiés : 39,0 h, 5 avis ; cause principale Mécanique 25,5 h (65 %).
Si un calcul donne autre chose, c'est le code qui est faux, pas la référence.

## Ce qu'il faut construire
Une page web statique `docs/index.html` publiée par GitHub Pages, qui lit les CSV de `data/`
(copiés dans `docs/data/`) et reproduit la maquette `maquette_reference.png` :
1. Bandeau : titre « Pilotage production & maintenance — Octobre 2026 » + badge
   « Données entièrement fictives ».
2. Cinq indicateurs : production, réalisation du plan, disponibilité moyenne, heures d'arrêt,
   cause principale.
3. Courbe production journalière vs plan (ligne pointillée), zone colorée sur l'arrêt du 14 au
   16 octobre, info-bulle au survol.
4. Barres horizontales : disponibilité moyenne par unité, trait de l'objectif 95 %, mention
   « sous l'objectif » en texte (pas seulement en couleur).
5. Carte de chaleur : disponibilité jour par jour et par unité (plus foncé = moins disponible), légende.
6. Tableau des arrêts, trié par durée décroissante.
7. Pied de page : chaîne de données visée et mention « données fictives ».

Contraintes techniques : HTML + CSS + JavaScript, une seule bibliothèque de graphiques
(Chart.js ou D3, version fixée, depuis un CDN), aucun serveur. Nombres au format français
(59 739 t ; 96,4 %). Lisible sur téléphone. Mode clair suffisant.

## Travail à faire (dans l'ordre, une étape à la fois)
1. M'expliquer le plan de construction et les calculs de chaque indicateur.
2. Créer `docs/index.html` (+ `docs/app.js`, `docs/style.css`) et `docs/data/`.
3. Créer `scripts/verifier.py` qui recalcule les chiffres de référence en Python depuis les CSV
   et les compare à ceux attendus ci-dessus.
4. Tester en local : `python -m http.server 8000` dans `docs/`, puis ouvrir http://localhost:8000.
   (Ouvrir le fichier directement bloque la lecture des CSV.)
5. Écrire le README : objectif, captures, indicateurs et leur définition, architecture visée,
   limites, comment lancer.
6. Commit et push, puis GitHub Pages (branche `main`, dossier `/docs`).

## Règles de travail
- Répondre et commenter en **français**.
- Aucun chiffre écrit en dur dans la page : tout est calculé depuis les CSV.
- Aucune donnée réelle, aucun nom de client, aucune clé ou mot de passe dans le dépôt.
- Code simple et commenté : je dois pouvoir l'expliquer en entretien.

## Pour aller plus loin (si le temps le permet)
- Version Power BI ou Looker Studio à partir des mêmes CSV, pour montrer l'outil BI.
- Exemple de modèle dbt (staging → marts) qui produirait ces tables depuis des extractions SAP.
