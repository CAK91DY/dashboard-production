# Version Power BI — guide de montage pas à pas

Objectif : reproduire `maquette_reference.png` dans Power BI Desktop, à partir du jeu de données
détaillé (105 120 lignes horaires). Les chiffres d'octobre 2026 doivent être **identiques** à ceux
déjà envoyés au client (PDF et page web).

Durée estimée : 2 à 3 h la première fois.

| Fichier | Rôle |
|---|---|
| `donnees/donnees_pilotage_production.xlsx` | les 7 tables, une feuille chacune (**source recommandée**) |
| `donnees/*.csv` | les mêmes tables en CSV (séparateur virgule, décimale point, UTF-8) |
| `mesures.dax` | toutes les mesures plus une requête de contrôle, à coller dans la vue Requête DAX |
| `theme_pilotage.json` | couleurs et styles de la maquette |
| `../scripts/generer_donnees_powerbi.py` | régénère les données (graine fixe : résultat identique) |

---

## 1. Le modèle de données

```
                 Dim_Date (1 096 j.)        Dim_Unite (4)
                   │  │  │                   │  │  │
      ┌────────────┘  │  └──────────┐ ┌──────┘  │  └───────┐
      ▼               ▼             ▼ ▼         ▼          ▼
Fait_Production_   Fait_Plan      Fait_Arrets ◄── Dim_Equipement (28)
Horaire (105 120)  (2 920)        (178)       ◄── Dim_Cause (5)
```

| Table | Grain | Colonnes utiles |
|---|---|---|
| `Fait_Production_Horaire` | 1 heure × 1 ligne de production (6 lignes : VAPO-L1, PEBD-L1/L2, PP-L1/L2, BUTA-L1), nov. 2024 → oct. 2026 | `Production_t`, `Minutes_Calendrier` (60), `Minutes_Marche`, `Minutes_Arret_Non_Planifie`, `Minutes_Arret_Planifie`, `Minutes_Micro_Arret`, `Poste` |
| `Fait_Plan` | 1 jour × 1 unité | `Plan_t` (déjà réduit les jours de grand arrêt planifié) |
| `Fait_Arrets` | 1 avis SAP PM d'arrêt non planifié | `Num_Avis`, `Equipement`, `Cause`, `Impact_Ligne`, `Duree_h` |
| `Dim_Unite` | 1 unité | `Unite`, `Famille` (Polymère / Intermédiaire), `Objectif_Dispo` (0,95), `Ordre` |
| `Dim_Date` | 1 jour, 2024 → 2026 complets | `Mois_Annee`, `Cle_Mois` (202610), `Jour`, `Annee`… |

**Rapprochement avec les CSV du client.** En octobre 2026, la somme de la production horaire des
lignes PEBD et PP de chaque jour vaut exactement `data/production_journaliere.csv`. Le ratio
marche ÷ calendrier de chaque unité et de chaque jour vaut exactement `data/disponibilite_unites.csv`.
Les 5 avis sont ceux de `data/arrets.csv`. Les 23 autres mois sont simulés.

---

## 2. Importer les données (15 min)

1. **Fichier → Options → Données actuelles → Chargement des données** : décocher
   **Date/heure automatique**. Sinon Power BI crée une table de dates cachée par colonne date.
2. **Accueil → Classeur Excel** → `donnees_pilotage_production.xlsx` → cocher les 7 feuilles →
   **Transformer les données**.
3. Dans Power Query, vérifier les types :
   - `Date` → **Date** (pas Date/heure) dans les 4 tables qui l'ont ;
   - `Date_Heure`, `Date_Heure_Debut`, `Date_Heure_Fin` → Date/heure ;
   - `Production_t`, `Minutes_*`, `Plan_t`, `Duree_h`, `Objectif_Dispo` → Nombre décimal ;
   - `Num_Avis` → **Texte**, pour qu'il ne soit jamais additionné.
4. **Fermer et appliquer.**

> Si tu passes par les CSV : à l'import, ouvre **Transformer**, puis pour chaque colonne numérique
> utilise **Type → Utilisation des paramètres régionaux → Nombre décimal / Anglais (États-Unis)**.
> Les fichiers utilisent le point décimal ; un Power BI réglé en français lirait `12.5` de travers.

---

## 3. Relations et réglages du modèle (15 min)

Vue **Modèle** : relations de type *plusieurs à un*, filtrage **unidirectionnel**.

| De (côté plusieurs) | Vers (côté un) |
|---|---|
| `Fait_Production_Horaire[Date]` | `Dim_Date[Date]` |
| `Fait_Production_Horaire[Code_Unite]` | `Dim_Unite[Code_Unite]` |
| `Fait_Plan[Date]` | `Dim_Date[Date]` |
| `Fait_Plan[Code_Unite]` | `Dim_Unite[Code_Unite]` |
| `Fait_Arrets[Date]` | `Dim_Date[Date]` |
| `Fait_Arrets[Code_Unite]` | `Dim_Unite[Code_Unite]` |
| `Fait_Arrets[Code_Equipement]` | `Dim_Equipement[Code_Equipement]` |
| `Fait_Arrets[Cause]` | `Dim_Cause[Cause]` |

Ensuite :
- **Supprimer** la relation que Power BI aurait créée seul entre `Dim_Equipement[Code_Unite]` et
  `Dim_Unite`. Elle rendrait le modèle ambigu, et l'unité de l'avis passe déjà par `Fait_Arrets`.
- `Dim_Date` : clic droit → **Marquer comme table de dates** → colonne `Date`.
- Colonnes de tri :
  - `Dim_Date[Mois_Annee]` → *Trier par colonne* → `Cle_Mois` ;
  - `Dim_Date[Jour_Semaine]` → `Num_Jour_Semaine` ;
  - `Dim_Unite[Unite]` → `Ordre`.
- Masquer les clés côté faits (`Code_Unite`, `Date`… des tables `Fait_*`) : les visuels utilisent
  les colonnes des dimensions.

---

## 4. Créer les mesures (10 min)

1. **Modélisation → Nouvelle table** : `_Mesures = ROW("x", 0)`. Masquer ensuite la colonne `x` :
   la table passe en tête de liste avec l'icône calculatrice.
2. Ouvrir la vue **Requête DAX** (icône à gauche, Power BI Desktop 2024 ou plus récent). Coller tout
   le contenu de `mesures.dax`.
3. Cliquer **Mettre à jour le modèle avec les modifications** (bandeau au-dessus du code) : les
   mesures sont créées dans `_Mesures`.
4. **Exécuter (F5)**. Deux tableaux de contrôle s'affichent ; ils doivent donner :

| Contrôle (oct. 2026) | Attendu |
|---|---|
| Production | 59 739 |
| Plan | 62 000 |
| Réalisation | 0,9635 (→ 96,4 %) |
| Écart pt | −3,65 (→ « ▼ 3,6 pt ») |
| Jour mini | 1 440, le 15/10/2026 |
| Dispo moyenne | 0,9509 (→ 95,1 %) |
| Dispo ratio global | 0,9493 : **à ne pas afficher**, voir §8 |
| Arrêts NP (h) / Avis | 39 / 5 |
| Cause / Part | Mécanique / 0,654 |
| Dispo par unité | Vapocraqueur 0,9886 · Polyéthylène BD 0,9663 · Polypropylène 0,9261 · Butadiène 0,9224 |

Si une valeur diffère, vérifie d'abord les relations (§3) et les types (§2).

5. **Formats** à régler (sélectionner la mesure → onglet *Outils de mesure*) :

| Mesures | Format |
|---|---|
| `Production…`, `Plan…`, `Écart au plan (t)`, `Jour le plus bas (t)`, `Zone incident` | Nombre entier, séparateur de milliers |
| Toutes les mesures en `%` | Pourcentage, 1 décimale |
| `Écart … (pt)`, `Heures …`, `MTTR`, `MTBF` | Décimal, 1 décimale |
| `Date du jour le plus bas` | Date `dd/MM/yyyy` |

Pour t'y retrouver, range-les dans des dossiers d'affichage (*Propriétés → Dossier d'affichage*) :
Production, Disponibilité, Arrêts, Temps, Textes, Mise en forme.

---

## 5. Mise en page (canevas 16:9, 1280 × 720)

1. **Affichage → Thèmes → Parcourir les thèmes** → `theme_pilotage.json`.
2. **Format de page** : 16:9, fond `#F4F5F7`.
3. Segments, en haut sous le bandeau, à la place des « pastilles » de la maquette :
   - `Dim_Date[Mois_Annee]`, **sélection unique**, réglé sur *oct. 2026* ;
   - `Dim_Unite[Unite]`, sélection multiple (« Toutes » par défaut).

Placement indicatif (x, y, largeur, hauteur en pixels) :

| Zone | Position |
|---|---|
| Bandeau (rectangle `#1B2433` + titre + badge) | 20, 12, 1240, 60 |
| Segments | 20, 80, 1240, 32 |
| 5 cartes d'indicateurs | y = 120, hauteur 80, largeur 240 chacune, espacées de 10 |
| Courbe production vs plan | 20, 212, 740, 260 |
| Barres disponibilité par unité | 770, 212, 490, 260 |
| Carte de chaleur | 20, 482, 615, 210 |
| Tableau des arrêts | 645, 482, 615, 210 |
| Pied de page (zone de texte) | 20, 696, 1240, 20 |

---

## 6. Visuel par visuel

### Bandeau
- Forme **Rectangle**, remplissage `#1B2433`, bord gauche orange : un 2e rectangle de 6 px `#E07B4F`.
- Titre : visuel **Carte (nouveau)** avec `[Titre du rapport]`, sans étiquette de catégorie,
  texte blanc 20 pt, fond transparent. Le titre suit le segment de mois.
- Badge : forme **rectangle arrondi** `#F3C09F`, texte « Données entièrement fictives ».

### Les 5 cartes d'indicateurs
Visuel **Carte (nouveau)** : valeur principale + **Étiquette de référence** (*Reference label*)
pour la ligne du dessous.

| Carte | Valeur | Étiquette de référence |
|---|---|---|
| Production polymères | `[Production polymères (t)]` (format « 59 739 t » : unités d'affichage *Aucune*, suffixe « t ») | `[Texte plan]` |
| Réalisation du plan | `[Réalisation du plan %]` | `[Texte écart plan]`, couleur : *fx → Valeur du champ →* `[Couleur écart plan]` |
| Disponibilité moyenne | `[Disponibilité %]` | `[Texte disponibilité]` |
| Arrêts non planifiés | `[Heures arrêts non planifiés]` (suffixe « h ») | `[Texte avis]` |
| Cause principale | `[Cause principale]` | `[Texte cause]` |

> Ancienne version de Power BI sans *Carte (nouveau)* : une carte classique pour la valeur, plus
> une 2e carte (texte 9 pt, gris `#5B6473`) pour la mesure « Texte… », superposée dessous.

### Courbe « Production journalière vs plan (t/j) »
Visuel **Graphique en courbes et histogramme groupé** :
- **Axe X** : `Dim_Date[Date]`, type *Catégoriel*, étiquettes au format `d mmm`.
- **Axe Y colonne** : `[Zone incident]` → c'est la bande orange des 14–16 oct. : couleur
  `#E07B4F`, transparence 85 %, espacement entre catégories 0 %.
- **Axe Y ligne** : `[Production polymères (t)]` (bleu `#2A78D6`, 2 px),
  `[Plan polymères (t)]` (gris, style **tirets**), `[Marqueur jour le plus bas]` (épaisseur 0,
  **marqueurs activés** taille 6, **étiquette de données activée**).
- **Axe Y secondaire : désactivé**, pour que les lignes et la bande partagent le **même axe**
  (pas de double axe). Axe Y : minimum 1 400, maximum 2 200.
- Annotation « Arrêt compresseur K-201 (PP) » : une **Carte (nouveau)** transparente avec
  `[Libellé arrêt principal]` (texte `#B5482A`, 10 pt), posée près du point bas.
- Info-bulle : ajouter `[Réalisation du plan %]` dans *Info-bulles*.

### Barres « Disponibilité moyenne par unité »
Visuel **Graphique à barres groupées** :
- **Axe Y** : `Dim_Unite[Unite]` ; **Axe X** : `[Disponibilité %]`. Trier par `Disponibilité %`
  décroissant.
- Axe X : début **0,85**, fin **1**. Ajoute en sous-titre « échelle de 85 à 100 % » : l'axe ne
  part pas de 0, il faut le dire.
- **Volet Analytique → Ligne constante X** = 0,95, style tirets, libellé « objectif 95 % ».
- **Étiquettes de données → Valeur → champ** : `[Étiquette disponibilité]`. On lit ainsi
  « 92,6 % ▼ sous l'objectif » en texte, pas seulement en couleur.

### Carte de chaleur « Disponibilité jour par jour »
Visuel **Matrice** :
- **Lignes** : `Dim_Unite[Unite]` ; **Colonnes** : `Dim_Date[Jour]` ; **Valeurs** : `[Disponibilité %]`.
- *Éléments de cellule* → **Couleur d'arrière-plan** → *fx* → **Valeur du champ** →
  `[Couleur disponibilité]`. Faire de même pour **Couleur de police** : les chiffres disparaissent
  et seules les cases colorées restent. L'info-bulle affiche toujours la valeur.
- Désactiver **sous-totaux et totaux** (lignes et colonnes). Largeur de colonne ≈ 16 px.
  Bordures blanches 2 px.
- Légende : 4 petits carrés (formes) `#DBE8FB` ≥ 97 % · `#9EC5F4` 93–97 % · `#3F7FD8` 85–93 % ·
  `#163D73` < 85 %, avec leurs libellés.

### Tableau « Principaux arrêts du mois »
Visuel **Table** : `Fait_Arrets[Date]` (format `dd/MM`), `Fait_Arrets[Equipement]`,
`Dim_Unite[Unite]`, `Fait_Arrets[Cause]`, `Fait_Arrets[Duree_h]` (renommé « Durée », 1 décimale).
- Trier par Durée **décroissante**.
- Filtre du visuel : `Fait_Arrets[Num_Avis]` → **N premiers = 5** par `[Heures arrêts non planifiés]`.

### Pied de page
Zone de texte 8 pt grise : « Chaîne de données : extractions SAP (PP, PM) → Cloud Storage →
BigQuery → transformations SQL dbt → tableau de bord. Données entièrement fictives. »

---

## 7. Page 2 « Tendances » (en option, pour montrer la profondeur du modèle)

- Courbe mensuelle `[Réalisation du plan %]` par `Dim_Date[Mois_Annee]`, ligne constante à 100 %.
- Courbe mensuelle `[Disponibilité hors arrêts planifiés %]`, ligne constante à 95 %. Mets-la
  **dans un 2e visuel sous le premier**, pas sur un double axe.
- Pareto : histogramme `[Heures arrêts non planifiés]` par `Dim_Cause[Cause]` (tri décroissant),
  plus `[Pareto cumul %]` en info-bulle ou en étiquette.
- Cartes : `[MTTR (h)]`, `[MTBF (h)]`, `[Évolution vs N-1 %]`, `[Disponibilité 12 mois glissants %]`.
- Segment `Fait_Production_Horaire[Poste]` (Matin / Après-midi / Nuit) pour comparer les équipes.

Les images `graphiques/05_tendance_24_mois.png` et `06_pareto_causes_12_mois.png` montrent le
résultat attendu.

---

## 8. Pièges à connaître (et à savoir expliquer au client)

1. **Disponibilité moyenne = moyenne simple des 4 unités** (`AVERAGEX` sur `Dim_Unite`).
   PEBD et PP ont 2 lignes chacun. Un ratio global (Σ marche ÷ Σ calendrier) pondère ces deux
   unités deux fois et donne **94,9 %** (sous l'objectif) au lieu de **95,1 %**.
2. **Heures d'avis ≠ heures de ligne arrêtée.** `Duree_h` est la durée d'indisponibilité de
   l'*équipement*. S'il est doublé (pompe de secours, analyseur), la ligne continue : l'analyseur
   AT-45 compte 2 h d'arrêt le 27/10, avec un vapocraqueur à 100 % ce jour-là (`Impact_Ligne` =
   « Sans impact »).
3. **Disponibilité et arrêts planifiés.** `[Disponibilité %]` compte les grands arrêts programmés
   comme du temps perdu (creux de mai 2025 et avril 2026). Pour juger la fiabilité, utilise
   `[Disponibilité hors arrêts planifiés %]`. Octobre 2026 n'a aucun arrêt planifié : les deux
   mesures y sont égales.
4. **Les textes passent par `FORMAT(…, "fr-FR")`** : « 62 000 », « 3,6 », quelle que soit la
   langue du poste qui ouvre le rapport.
5. `Num_Avis` en **texte**, et pas de *Date/heure automatique* (§2).

---

## 9. Livrer

- **Fichier → Exporter → PDF** : une page par onglet. Comparer avec le PDF déjà envoyé.
- Publication : **Accueil → Publier** vers un espace de travail. Sans licence Pro, envoyer le
  `.pbix` ou le PDF.
- Ne pas versionner le `.pbix` s'il dépasse quelques dizaines de Mo. Le dépôt contient tout ce
  qu'il faut pour le reconstruire.
