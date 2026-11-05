"""Assemble le dossier de réalisation Power BI en une seule page HTML imprimable :
images, modèle (faits et dimensions), relations, couleurs, mesures DAX, check-list et contrôles.

Les mesures sont relues dans powerbi/mesures.dax et les tables dans powerbi/donnees/ :
le dossier reste donc à jour si on les modifie.

Lancer depuis la racine du dépôt :  python scripts/dossier_power_bi.py
Puis ouvrir powerbi/dossier_power_bi.html dans un navigateur et Imprimer -> Enregistrer en PDF
(le PDF du dépôt, powerbi/DOSSIER_POWER_BI.pdf, a été produit ainsi).
"""
import html
import re
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
PBI = RACINE / "powerbi"
DONNEES = PBI / "donnees"
e = html.escape

# ------------------------------------------------------------------ 1. tables (faits et dimensions)
DESCRIPTION_TABLES = {
    "Fait_Production_Horaire": ("Fait", "1 heure × 1 ligne de production (nov. 2024 → oct. 2026)",
                                "Production et temps de marche / d'arrêt de chaque ligne, heure par heure."),
    "Fait_Plan": ("Fait", "1 jour × 1 unité", "Plan de production journalier (déjà réduit les jours de grand arrêt planifié)."),
    "Fait_Arrets": ("Fait", "1 avis SAP PM", "Arrêts non planifiés : équipement, cause, impact sur la ligne, durée."),
    "Dim_Date": ("Dimension", "1 jour (2024 → 2026 complets)", "Calendrier : à marquer comme table de dates."),
    "Dim_Unite": ("Dimension", "1 unité (4)", "Unités du site, famille (Polymère / Intermédiaire), objectif de disponibilité."),
    "Dim_Equipement": ("Dimension", "1 équipement (28)", "Repère, libellé, type et ligne de chaque équipement."),
    "Dim_Cause": ("Dimension", "1 cause (5)", "Causes d'arrêt et leur famille (Technique / Procédé)."),
}
DESCRIPTION_COLONNES = {
    "Date_Heure": ("Date/heure", "Début de l'heure"),
    "Date": ("Date", "Jour (clé vers Dim_Date)"),
    "Heure": ("Nombre entier", "0 à 23"),
    "Poste": ("Texte", "Matin (6-14 h), Après-midi (14-22 h), Nuit"),
    "Code_Unite": ("Texte", "Clé vers Dim_Unite : VAPO, PEBD, PP, BUTA"),
    "Code_Ligne": ("Texte", "VAPO-L1, PEBD-L1/L2, PP-L1/L2, BUTA-L1"),
    "Production_t": ("Décimal", "Tonnes produites dans l'heure"),
    "Minutes_Calendrier": ("Décimal", "Toujours 60"),
    "Minutes_Marche": ("Décimal", "Minutes où la ligne a tourné"),
    "Minutes_Arret_Non_Planifie": ("Décimal", "Arrêt lié à un avis SAP PM « Arrêt ligne »"),
    "Minutes_Arret_Planifie": ("Décimal", "Grand arrêt programmé (inclus dans le plan)"),
    "Minutes_Micro_Arret": ("Décimal", "Arrêts courts (< 1 h) sans avis"),
    "Plan_t": ("Décimal", "Tonnes prévues dans la journée"),
    "Num_Avis": ("Texte", "Numéro d'avis SAP PM (jamais additionné)"),
    "Date_Heure_Debut": ("Date/heure", "Début de l'arrêt"),
    "Date_Heure_Fin": ("Date/heure", "Fin de l'arrêt"),
    "Code_Equipement": ("Texte", "Clé vers Dim_Equipement"),
    "Equipement": ("Texte", "Libellé, ex. « Compresseur K-201 »"),
    "Cause": ("Texte", "Clé vers Dim_Cause"),
    "Impact_Ligne": ("Texte", "Arrêt ligne / Débit réduit / Sans impact"),
    "Duree_h": ("Décimal", "Durée d'indisponibilité de l'équipement (h)"),
    "Statut": ("Texte", "Statut de l'avis"),
    "Annee": ("Nombre entier", ""), "Trimestre": ("Texte", "T1 à T4"), "Mois_Num": ("Nombre entier", "1 à 12"),
    "Mois": ("Texte", "janvier…"), "Mois_Annee": ("Texte", "« oct. 2026 », trier par Cle_Mois"),
    "Cle_Mois": ("Nombre entier", "202610"), "Jour": ("Nombre entier", "1 à 31 (colonnes de la carte de chaleur)"),
    "Jour_Semaine": ("Texte", "lundi…, trier par Num_Jour_Semaine"), "Num_Jour_Semaine": ("Nombre entier", "1 = lundi"),
    "Semaine_ISO": ("Nombre entier", ""), "Avec_Donnees": ("Vrai/faux", "Jour couvert par les faits"),
    "Unite": ("Texte", "Libellé affiché, trier par Ordre"), "Famille": ("Texte", "Polymère / Intermédiaire"),
    "Nb_Lignes": ("Nombre entier", "Lignes de production de l'unité"), "Ordre": ("Nombre entier", "Ordre d'affichage"),
    "Objectif_Dispo": ("Décimal", "0,95"), "Type_Equipement": ("Texte", "Compresseur, Pompe, Four…"),
    "Famille_Cause": ("Texte", "Technique / Procédé"),
}
RELATIONS = [
    ("Fait_Production_Horaire[Date]", "Dim_Date[Date]"),
    ("Fait_Production_Horaire[Code_Unite]", "Dim_Unite[Code_Unite]"),
    ("Fait_Plan[Date]", "Dim_Date[Date]"),
    ("Fait_Plan[Code_Unite]", "Dim_Unite[Code_Unite]"),
    ("Fait_Arrets[Date]", "Dim_Date[Date]"),
    ("Fait_Arrets[Code_Unite]", "Dim_Unite[Code_Unite]"),
    ("Fait_Arrets[Code_Equipement]", "Dim_Equipement[Code_Equipement]"),
    ("Fait_Arrets[Cause]", "Dim_Cause[Cause]"),
]


def bloc_tables():
    sortie = []
    for nom, (genre, grain, role) in DESCRIPTION_TABLES.items():
        fichier = DONNEES / f"{nom}.csv"
        df = pd.read_csv(fichier, nrows=3)
        nb = sum(1 for _ in open(fichier, encoding="utf-8-sig")) - 1
        lignes = "".join(
            f"<tr><td><code>{e(c)}</code></td><td>{e(DESCRIPTION_COLONNES.get(c, ('', ''))[0])}</td>"
            f"<td>{e(DESCRIPTION_COLONNES.get(c, ('', ''))[1])}</td><td class='ex'>{e(str(df[c].iloc[0]))}</td></tr>"
            for c in df.columns)
        sortie.append(f"""<div class="table-bloc">
          <h3><span class="etiquette {'fait' if genre == 'Fait' else 'dim'}">{genre}</span> {e(nom)}
              <small>{f'{nb:,}'.replace(',', ' ')} lignes · grain : {e(grain)}</small></h3>
          <p>{e(role)}</p>
          <table><thead><tr><th>Colonne</th><th>Type Power BI</th><th>Contenu</th><th>Exemple</th></tr></thead>
          <tbody>{lignes}</tbody></table></div>""")
    return "\n".join(sortie)


# ------------------------------------------------------------------ 2. mesures DAX (relues dans mesures.dax)
def bloc_mesures():
    texte = (PBI / "mesures.dax").read_text(encoding="utf-8")
    corps = texte.split("DEFINE", 1)[1]
    mesures_txt, controle = corps.split("// ------------------------------------------------------------- Contrôle", 1)
    sections = re.split(r"\n\s*// -{10,} (\d\. .+)\n", mesures_txt)
    sortie, nb = [], 0
    for i in range(1, len(sections), 2):
        titre, code = sections[i], sections[i + 1].strip("\n")
        code = "\n".join(l[4:] if l.startswith("    ") else l for l in code.split("\n"))
        nb += code.count("MEASURE ")
        sortie.append(f"<h3>{e(titre)}</h3><pre>{e(code)}</pre>")
    controle = "// Contrôle" + controle
    return nb, "\n".join(sortie), controle


FORMATS = [
    ("Production…, Plan…, Écart au plan (t), Jour le plus bas (t), Zone incident, Marqueur", "Nombre entier, séparateur de milliers"),
    ("Toutes les mesures dont le nom finit par %", "Pourcentage, 1 décimale"),
    ("Écart … (pt), Heures …, MTTR (h), MTBF (h)", "Décimal, 1 décimale"),
    ("Date du jour le plus bas", "Date, format dd/MM/yyyy"),
    ("Textes, Couleurs, Libellés, Période, Titre", "Texte (aucun réglage)"),
]

# ------------------------------------------------------------------ 3. couleurs
COULEURS = [
    ("Fond de page", "#F4F5F7"), ("Cartes (fond)", "#FFFFFF"), ("Bordures", "#E3E6EB"),
    ("Bandeau", "#1B2433"), ("Liseré du bandeau, zone d'incident (85 % transp.)", "#E07B4F"),
    ("Badge « Données fictives »", "#F3C09F"), ("Texte principal", "#1B2433"), ("Texte secondaire, plan, objectif", "#5B6473"),
    ("Texte discret", "#8A92A0"), ("Série principale : production, barres", "#2A78D6"),
    ("Alerte : « ▼ sous le plan », annotation", "#B5482A"), ("Au-dessus du plan", "#2E7D32"),
    ("Carte de chaleur ≥ 97 %", "#DBE8FB"), ("Carte de chaleur 93–97 %", "#9EC5F4"),
    ("Carte de chaleur 85–93 %", "#3F7FD8"), ("Carte de chaleur < 85 %", "#163D73"),
]

# ------------------------------------------------------------------ 4. check-list point par point
CHECKLIST = [
    ("Phase 1 – Données (15 min)", [
        "Fichier → Options et paramètres → Options → Fichier actif → Chargement des données : décocher <b>Date/heure automatique</b>.",
        "Accueil → Obtenir les données → Classeur Excel → <code>powerbi/donnees/donnees_pilotage_production.xlsx</code>.",
        "Cocher les <b>7 feuilles</b> → <b>Transformer les données</b>.",
        "Types : <code>Date</code> → <b>Date</b> (4 tables) ; <code>Date_Heure*</code> → Date/heure ; <code>Production_t</code>, <code>Plan_t</code>, <code>Duree_h</code>, <code>Minutes_*</code>, <code>Objectif_Dispo</code> → Nombre décimal ; <code>Num_Avis</code> → <b>Texte</b>.",
        "<b>Fermer et appliquer</b>.",
    ]),
    ("Phase 2 – Modèle (15 min)", [
        "Vue Modèle : supprimer les relations automatiques et créer les <b>8 relations</b> du tableau « Relations » (plusieurs-à-un, unidirectionnelles).",
        "Vérifier qu'il n'y a <b>aucune</b> relation entre <code>Dim_Equipement</code> et <code>Dim_Unite</code>.",
        "<code>Dim_Date</code> → Outils de table → <b>Marquer comme table de dates</b> → colonne <code>Date</code>.",
        "Outils de colonne → Trier par colonne : <code>Mois_Annee</code> par <code>Cle_Mois</code> ; <code>Jour_Semaine</code> par <code>Num_Jour_Semaine</code> ; <code>Unite</code> par <code>Ordre</code>.",
    ]),
    ("Phase 3 – Mesures (10 min)", [
        "Modélisation → Nouvelle table : <code>_Mesures = ROW(\"x\", 0)</code>.",
        "Vue <b>Requête DAX</b> : coller tout le fichier <code>powerbi/mesures.dax</code>.",
        "Cliquer <b>Mettre à jour le modèle avec les modifications</b>.",
        "<b>F5</b> : comparer avec le tableau « Contrôles » de ce dossier. En cas d'écart, revoir les phases 1 et 2.",
        "Masquer la colonne <code>x</code> ; régler les formats (tableau « Formats des mesures »).",
    ]),
    ("Phase 4 – Décor (5 min)", [
        "Affichage → Thèmes → Parcourir les thèmes → <code>powerbi/theme_pilotage.json</code>.",
        "Clic sur le fond du canevas → Format de page → Paramètres du canevas → <b>16:9</b>.",
        "Arrière-plan du canevas → Parcourir → <code>powerbi/fond_de_page_1280x720.png</code>, ajustement <b>Ajuster</b>, transparence <b>0 %</b>.",
        "Pour chaque visuel : Format → Général → Propriétés → <b>Taille et position</b> = valeurs du « Plan de montage ».",
    ]),
    ("Phase 5 – En-tête et filtres (15 min)", [
        "<b>①</b> Carte (nouveau) <code>[Titre du rapport]</code> — 36, 30, 880, 34 : étiquette de catégorie désactivée, valeur blanche Segoe UI Semibold 20, alignée à gauche.",
        "<b>②</b> Segment <code>Dim_Date[Mois_Annee]</code> — 20, 76, 200, 30 : liste déroulante, <b>sélection unique</b>, choisir <b>oct. 2026</b>, en-tête masqué.",
        "<b>③</b> Segment <code>Dim_Unite[Unite]</code> — 228, 76, 204, 30 : liste déroulante, « Tout sélectionner » activé.",
    ]),
    ("Phase 6 – Les 5 indicateurs (20 min)", [
        "Cartes (nouveau) de 224 × 46 à <b>y = 140</b> : étiquette de catégorie désactivée, valeur Segoe UI Bold 22 <code>#1B2433</code>, mesure « Texte » en <b>Étiquette de référence</b> 9 pt <code>#5B6473</code>.",
        "<b>④</b> x = 28 : <code>[Production polymères (t)]</code> (suffixe « t ») + <code>[Texte plan]</code>.",
        "<b>⑤</b> x = 278 : <code>[Réalisation du plan %]</code> + <code>[Texte écart plan]</code> ; couleur de l'étiquette : fx → Valeur du champ → <code>[Couleur écart plan]</code>.",
        "<b>⑥</b> x = 528 : <code>[Disponibilité %]</code> + <code>[Texte disponibilité]</code>.",
        "<b>⑦</b> x = 778 : <code>[Heures arrêts non planifiés]</code> (suffixe « h ») + <code>[Texte avis]</code>.",
        "<b>⑧</b> x = 1028 : <code>[Cause principale]</code> + <code>[Texte cause]</code>.",
    ]),
    ("Phase 7 – ⑨ Courbe production vs plan (25 min)", [
        "Graphique en courbes et histogramme groupé — 28, 236, 734, 218.",
        "Axe X : <code>Dim_Date[Date]</code> ; Axe Y de colonne : <code>[Zone incident]</code> ; Axe Y de ligne : <code>[Production polymères (t)]</code>, <code>[Plan polymères (t)]</code>, <code>[Marqueur jour le plus bas]</code>.",
        "Renommer les séries : « Production », « Plan », « Jour le plus bas », « Arrêt (&lt; 90 % du plan) ».",
        "Axe X : type <b>Catégoriel</b>, sans titre. Axe Y : min <b>1400</b>, max <b>2200</b>, sans titre. <b>Axe Y secondaire désactivé</b> (un seul axe).",
        "Lignes : Production <code>#2A78D6</code> 2 px ; Plan <code>#5B6473</code> <b>tirets</b> ; Jour le plus bas : largeur 0, <b>marqueurs</b> taille 6.",
        "Colonnes : <code>#E07B4F</code>, <b>transparence 85 %</b>, espacement entre catégories <b>0</b>.",
        "Étiquettes de données : seulement sur « Jour le plus bas » (affiche 1 440). Légende en haut à gauche.",
        "Annotation : Carte (nouveau) transparente <code>[Libellé arrêt principal]</code>, <code>#B5482A</code> 10 pt, à droite du point bas.",
    ]),
    ("Phase 8 – ⑩ Barres de disponibilité (15 min)", [
        "Graphique à barres groupées — 788, 236, 464, 218 : Axe Y <code>Dim_Unite[Unite]</code>, Axe X <code>[Disponibilité %]</code>.",
        "… → Trier l'axe → Disponibilité %, <b>décroissant</b>.",
        "Axe X : plage <b>0,85 → 1</b>, étiquettes visibles. Barres <code>#2A78D6</code>.",
        "Étiquettes de données : Valeur → <b>Champ</b> → <code>[Étiquette disponibilité]</code> (« 92,6 % ▼ sous l'objectif »).",
        "Volet Analytique → <b>Ligne constante X</b> = 0,95, nom « objectif 95 % », tirets <code>#5B6473</code>, étiquette = nom.",
    ]),
    ("Phase 9 – ⑪ Carte de chaleur (20 min)", [
        "Matrice — 28, 506, 604, 150 : Lignes <code>Dim_Unite[Unite]</code>, Colonnes <code>Dim_Date[Jour]</code>, Valeurs <code>[Disponibilité %]</code>.",
        "Sous-totaux et totaux <b>désactivés</b> (lignes et colonnes).",
        "Éléments de cellule → <b>Couleur d'arrière-plan</b> → fx → Valeur du champ → <code>[Couleur disponibilité]</code>.",
        "Même chose pour la <b>Couleur de police</b> : les chiffres disparaissent.",
        "Quadrillage blanc 2 px ; en-têtes de colonnes 8 pt ; colonnes réduites à ~16 px (31 jours visibles).",
    ]),
    ("Phase 10 – ⑫ Tableau des arrêts (10 min)", [
        "Table — 658, 506, 594, 178 : <code>Fait_Arrets[Date]</code>, <code>[Equipement]</code>, <code>Dim_Unite[Unite]</code>, <code>[Cause]</code>, <code>[Duree_h]</code>.",
        "Format de <code>Date</code> : <code>dd/MM</code> ; <code>Duree_h</code> renommé « Durée », 1 décimale.",
        "Tri par <b>Durée décroissante</b>.",
        "Volet Filtres : <code>Num_Avis</code> → <b>N premiers = 5</b> par <code>[Heures arrêts non planifiés]</code>.",
    ]),
    ("Phase 11 – Contrôle et livraison (15 min)", [
        "Comparer avec la page web : 59 739 t · 96,4 % · ▼ 3,6 pt · 95,1 % · 39,0 h · Mécanique 25,5 h (65 %) · 1 440 t le 15/10 · 98,9 / 96,6 / 92,6 / 92,2 %.",
        "Segment Mois = <b>sept. 2026</b> : tout doit changer. Segment Unités = <b>Vapocraqueur</b> : production polymères vide (normal).",
        "Remettre <b>oct. 2026</b>, enregistrer le <code>.pbix</code>.",
        "Fichier → Exporter → <b>PDF</b> ; comparer avec le PDF déjà envoyé au client.",
    ]),
]

CONTROLES = [
    ("Production polymères (t)", "59 739"), ("Plan polymères (t)", "62 000"), ("Réalisation du plan %", "96,4 %"),
    ("Écart réalisation (pt)", "−3,6"), ("Jour le plus bas", "1 440 t le 15/10/2026"),
    ("Disponibilité %", "95,1 %"), ("Vapocraqueur / PEBD / PP / Butadiène", "98,9 / 96,6 / 92,6 / 92,2 %"),
    ("Heures arrêts non planifiés / Nb avis", "39,0 h / 5"), ("Cause principale", "Mécanique, 25,5 h, 65 %"),
    ("Libellé arrêt principal", "Arrêt compresseur K-201 (PP)"),
    ("Disponibilité ratio global % (à ne pas afficher)", "94,9 %"),
]

PIEGES = [
    "<b>Disponibilité moyenne = moyenne simple des 4 unités</b> (<code>[Disponibilité %]</code>, 95,1 %). "
    "Le ratio global pondère PEBD et PP (2 lignes chacun) deux fois : 94,9 %, ce qui contredirait le PDF.",
    "<b>Heures d'avis ≠ heures de ligne arrêtée</b> : <code>Duree_h</code> mesure l'indisponibilité de l'équipement. "
    "L'analyseur AT-45 compte 2 h le 27/10, alors que le vapocraqueur est à 100 % ce jour-là (« Sans impact »).",
    "<b>Arrêts planifiés</b> : <code>[Disponibilité %]</code> les compte comme du temps perdu (creux de mai 2025 et avril 2026). "
    "Pour la fiabilité, utiliser <code>[Disponibilité hors arrêts planifiés %]</code>. Aucun en octobre 2026.",
    "<b>Formats en français</b> : les textes utilisent <code>FORMAT(…, \"fr-FR\")</code>, d'où « 62 000 » et « 3,6 » quel que soit le poste.",
    "<code>Num_Avis</code> en <b>texte</b> et <b>Date/heure automatique désactivée</b>, sinon totaux et filtres faussés.",
]


# ------------------------------------------------------------------ assemblage
def construire():
    nb_mesures, mesures_html, controle_dax = bloc_mesures()
    couleurs = "".join(f"<tr><td><i style='background:{c}'></i></td><td><code>{c}</code></td><td>{e(r)}</td></tr>"
                       for r, c in COULEURS)
    relations = "".join(f"<tr><td><code>{a}</code></td><td>→</td><td><code>{b}</code></td></tr>" for a, b in RELATIONS)
    formats = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td></tr>" for a, b in FORMATS)
    checklist = ""
    n = 0
    for titre, etapes in CHECKLIST:
        items = ""
        for etape in etapes:
            n += 1
            items += f"<li><span class='case'></span><span class='num'>{n}.</span><span>{etape}</span></li>"
        checklist += f"<h3>{e(titre)}</h3><ul class='coches'>{items}</ul>"
    controles = "".join(f"<tr><td>{e(a)}</td><td><b>{e(b)}</b></td></tr>" for a, b in CONTROLES)
    pieges = "".join(f"<li>{p}</li>" for p in PIEGES)

    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<title>Dossier de réalisation Power BI — Pilotage production & maintenance</title>
<style>
  @page {{ size: A4; margin: 14mm 13mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font: 10pt/1.45 "Segoe UI", Inter, sans-serif; color: #1B2433; margin: 0; }}
  h1 {{ font-size: 22pt; margin: 0 0 4px; }}
  h2 {{ font-size: 15pt; margin: 0 0 8px; padding-bottom: 4px; border-bottom: 3px solid #E07B4F; break-after: avoid; }}
  h3 {{ font-size: 11.5pt; margin: 14px 0 6px; break-after: avoid; }}
  h3 small {{ font-weight: 400; color: #5B6473; font-size: 9pt; margin-left: 6px; }}
  section {{ break-before: page; }}
  section.premiere {{ break-before: auto; }}
  .couverture {{ background: #1B2433; color: #fff; border-left: 8px solid #E07B4F; border-radius: 8px; padding: 18px 22px; margin-bottom: 14px; }}
  .couverture p {{ margin: 4px 0 0; color: #F0A37F; font-size: 9pt; letter-spacing: .1em; text-transform: uppercase; font-weight: 600; }}
  .badge {{ display: inline-block; background: #F3C09F; color: #1B2433; border-radius: 99px; padding: 2px 10px; font-weight: 600; font-size: 9pt; margin-top: 8px; }}
  img {{ width: 100%; border: 1px solid #E3E6EB; border-radius: 6px; }}
  figure {{ margin: 0 0 10px; break-inside: avoid; }}
  figcaption {{ font-size: 8.5pt; color: #5B6473; margin-top: 3px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 8.8pt; margin-bottom: 8px; break-inside: auto; }}
  th {{ text-align: left; background: #F4F5F7; color: #5B6473; font-weight: 600; padding: 4px 6px; border-bottom: 1px solid #E3E6EB; }}
  td {{ padding: 3.5px 6px; border-bottom: 1px solid #EEF0F3; vertical-align: top; }}
  tr {{ break-inside: avoid; }}
  td.ex {{ color: #5B6473; font-size: 8.3pt; }}
  td i {{ display: inline-block; width: 30px; height: 16px; border-radius: 3px; border: 1px solid #E3E6EB; }}
  code {{ font-family: Consolas, "DejaVu Sans Mono", monospace; font-size: 8.6pt; background: #F4F5F7; padding: 0 3px; border-radius: 3px; }}
  pre {{ font: 7.9pt/1.38 Consolas, "DejaVu Sans Mono", monospace; background: #F7F8FA; border: 1px solid #E3E6EB; border-left: 3px solid #2A78D6;
         border-radius: 4px; padding: 8px 10px; white-space: pre-wrap; margin: 0 0 6px; }}
  .table-bloc {{ break-inside: avoid; }}
  .table-bloc p {{ margin: 0 0 4px; color: #5B6473; }}
  .etiquette {{ font-size: 8pt; padding: 1px 7px; border-radius: 99px; vertical-align: 2px; }}
  .fait {{ background: #2A78D6; color: #fff; }} .dim {{ background: #DBE8FB; color: #1C5CAB; }}
  ul.coches {{ list-style: none; padding: 0; margin: 0 0 6px; }}
  ul.coches li {{ display: flex; gap: 6px; padding: 3px 0; border-bottom: 1px solid #EEF0F3; break-inside: avoid; }}
  .case {{ flex: none; width: 11px; height: 11px; border: 1.5px solid #5B6473; border-radius: 2px; margin-top: 3px; }}
  .num {{ flex: none; color: #5B6473; width: 22px; }}
  .schema {{ font: 8.5pt/1.3 Consolas, "DejaVu Sans Mono", monospace; background: #F7F8FA; border: 1px solid #E3E6EB; border-radius: 4px; padding: 10px; white-space: pre; }}
  .encadre {{ background: #FDF3EE; border-left: 4px solid #E07B4F; padding: 8px 12px; border-radius: 4px; margin: 8px 0; }}
  .sommaire li {{ margin: 2px 0; }}
  .deux {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
</style></head>
<body>

<section class="premiere">
  <div class="couverture">
    <p>Dossier de réalisation · Power BI</p>
    <h1>Pilotage production &amp; maintenance</h1>
    <div>Tout ce qu'il faut pour reproduire le tableau de bord dans Power BI Desktop</div>
    <span class="badge">Données entièrement fictives</span>
  </div>
  <ol class="sommaire">
    <li>Aperçu du résultat attendu, image de fond et plan de montage</li>
    <li>Modèle de données : tables de faits, dimensions, relations</li>
    <li>Couleurs</li>
    <li>Mesures DAX ({nb_mesures} mesures) et formats</li>
    <li>Check-list point par point ({n} étapes)</li>
    <li>Contrôles et pièges</li>
  </ol>
  <p><b>Fichiers du dépôt</b> (<code>github.com/CAK91DY/dashboard-production</code>) :
     <code>powerbi/donnees/donnees_pilotage_production.xlsx</code> (données), <code>powerbi/mesures.dax</code> (mesures à coller),
     <code>powerbi/theme_pilotage.json</code> (thème), <code>powerbi/fond_de_page_1280x720.png</code> (image de fond).</p>
  <h2>1. Résultat attendu</h2>
  <figure><img src="../graphiques/tableau_de_bord_octobre_2026.png" alt="Tableau de bord attendu">
    <figcaption>Version web du tableau de bord (octobre 2026) : la version Power BI doit afficher les mêmes chiffres.</figcaption></figure>
</section>

<section>
  <h2>1. Image de fond et plan de montage</h2>
  <figure><img src="fond_de_page_1280x720.png" alt="Image de fond">
    <figcaption>Image de fond du canevas (1280 × 720) : bandeau, cadres, titres, légende et pied de page déjà dessinés.</figcaption></figure>
  <figure><img src="plan_de_montage.png" alt="Plan de montage">
    <figcaption>Plan de montage : chaque visuel ①…⑫ avec sa position (X, Y, largeur, hauteur en pixels).</figcaption></figure>
</section>

<section>
  <h2>2. Modèle de données</h2>
  <div class="schema">                  Dim_Date (1 096 j.)          Dim_Unite (4)
                    │   │   │                    │   │   │
       ┌────────────┘   │   └───────────┐ ┌──────┘   │   └────────┐
       ▼                ▼               ▼ ▼          ▼            ▼
 Fait_Production_    Fait_Plan       Fait_Arrets  ◄── Dim_Equipement (28)
 Horaire (105 120)   (2 920)         (178)        ◄── Dim_Cause (5)</div>
  <h3>Relations (plusieurs-à-un, filtrage unidirectionnel)</h3>
  <table><thead><tr><th>De (côté plusieurs)</th><th></th><th>Vers (côté un)</th></tr></thead><tbody>{relations}</tbody></table>
  <div class="encadre">Aucune relation entre <code>Dim_Equipement</code> et <code>Dim_Unite</code> : elle rendrait le modèle ambigu.
    En octobre 2026, les agrégats retombent exactement sur les CSV envoyés au client (contrôlé par <code>scripts/verifier.py</code>).</div>
  {bloc_tables()}
</section>

<section>
  <h2>3. Couleurs</h2>
  <table><thead><tr><th></th><th>Code</th><th>Usage</th></tr></thead><tbody>{couleurs}</tbody></table>
  <p>Le thème <code>theme_pilotage.json</code> applique ces couleurs et rend les visuels transparents et sans titre,
     car les cadres et les titres sont dans l'image de fond.</p>
</section>

<section>
  <h2>4. Mesures DAX</h2>
  <div class="encadre">Ne pas recopier à la main : créer la table <code>_Mesures = ROW("x", 0)</code>, coller <b>tout</b> le fichier
    <code>powerbi/mesures.dax</code> dans la vue <b>Requête DAX</b>, puis <b>Mettre à jour le modèle avec les modifications</b> et <b>F5</b>.
    Le code ci-dessous est le même, pour lecture et explication.</div>
  <h3>Formats des mesures</h3>
  <table><thead><tr><th>Mesures</th><th>Format</th></tr></thead><tbody>{formats}</tbody></table>
  {mesures_html}
  <h3>Requête de contrôle (fin du fichier)</h3>
  <pre>{e(controle_dax.strip())}</pre>
</section>

<section>
  <h2>5. Check-list point par point</h2>
  {checklist}
</section>

<section>
  <h2>6. Contrôles (octobre 2026)</h2>
  <table><thead><tr><th>Mesure</th><th>Valeur attendue</th></tr></thead><tbody>{controles}</tbody></table>
  <h2 style="margin-top:16px">Pièges à connaître et à savoir expliquer au client</h2>
  <ul>{pieges}</ul>
</section>
</body></html>"""


sortie = PBI / "dossier_power_bi.html"
sortie.write_text(construire(), encoding="utf-8")
print("écrit :", sortie)
