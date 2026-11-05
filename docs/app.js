/* Tableau de bord production & maintenance — tout est calculé depuis les CSV de docs/data/.
   Aucun résultat n'est écrit en dur : seuls les PARAMÈTRES ci-dessous sont fixés. */

// ------------------------------------------------------------------ paramètres métier
const OBJECTIF_DISPO = 0.95;          // objectif de disponibilité par unité
const SEUIL_ZONE_ARRET = 0.90;        // jour "en incident" si production < 90 % du plan
const ECHELLE_BARRES_MIN = 0.85;      // les barres de disponibilité commencent à 85 %
const CLASSES_CHALEUR = [             // classes de la carte de chaleur (plus foncé = moins disponible)
  { min: 0.97, classe: "n1", libelle: "≥ 97 %" },
  { min: 0.93, classe: "n2", libelle: "93–97 %" },
  { min: 0.85, classe: "n3", libelle: "85–93 %" },
  { min: 0, classe: "n4", libelle: "< 85 %" },
];
const ABREVIATIONS = { "Polypropylène": "PP", "Polyéthylène BD": "PEBD", "Vapocraqueur": "VAPO", "Butadiène": "BUTA" };

// ------------------------------------------------------------------ format français
const nombre = (x, decimales = 0) =>
  new Intl.NumberFormat("fr-FR", { minimumFractionDigits: decimales, maximumFractionDigits: decimales }).format(x);
const pourcent = (x, decimales = 1) => `${nombre(x * 100, decimales)} %`;   // 0.964 -> "96,4 %"
const tonnes = (x) => `${nombre(x)} t`;                                      // 59739 -> "59 739 t"
const heures = (x) => `${nombre(x, 1)} h`;                                   // 39 -> "39,0 h"
const jourMois = (d) => d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" }); // "15 oct."
const jjmm = (d) => d.toLocaleDateString("fr-FR", { day: "2-digit", month: "2-digit" });   // "15/10"

// ------------------------------------------------------------------ lecture des CSV
/* Lecteur CSV minimal : suffisant ici car aucun champ ne contient de virgule ni de guillemet. */
function lireCsv(texte) {
  const [entete, ...lignes] = texte.trim().split(/\r?\n/);
  const colonnes = entete.split(",");
  return lignes.map((ligne) => {
    const valeurs = ligne.split(",");
    const objet = {};
    colonnes.forEach((col, i) => {
      const v = valeurs[i];
      objet[col] = /^-?\d+(\.\d+)?$/.test(v) ? Number(v) : v;   // nombre si possible
    });
    return objet;
  });
}

/* "2026-10-15" -> date locale (évite le décalage de fuseau horaire de new Date("2026-10-15")) */
function versDate(iso) {
  const [a, m, j] = iso.split("-").map(Number);
  return new Date(a, m - 1, j);
}

async function charger(nom) {
  const reponse = await fetch(`data/${nom}`);
  if (!reponse.ok) throw new Error(`Lecture impossible : data/${nom}`);
  return lireCsv(await reponse.text());
}

const somme = (liste, cle) => liste.reduce((total, ligne) => total + ligne[cle], 0);
const moyenne = (valeurs) => valeurs.reduce((a, b) => a + b, 0) / valeurs.length;

// ------------------------------------------------------------------ calculs des indicateurs
function calculer(production, dispo, arrets) {
  production.forEach((l) => (l.jour = versDate(l.date)));
  dispo.forEach((l) => (l.jour = versDate(l.date)));

  // Production et plan
  const totalProd = somme(production, "production_t");
  const totalPlan = somme(production, "plan_t");
  const realisation = totalProd / totalPlan;
  const ecartPoints = (realisation - 1) * 100;             // calculé AVANT arrondi : -3,65 -> "-3,6 pt"

  // Jour le plus bas
  const plusBas = production.reduce((min, l) => (l.production_t < min.production_t ? l : min));

  // Zone d'incident : jours consécutifs autour du jour le plus bas sous 90 % du plan
  const i0 = production.indexOf(plusBas);
  const enIncident = (l) => l.production_t < SEUIL_ZONE_ARRET * l.plan_t;
  let debut = i0, fin = i0;
  while (debut > 0 && enIncident(production[debut - 1])) debut--;
  while (fin < production.length - 1 && enIncident(production[fin + 1])) fin++;
  const jourDebut = production[debut].jour, jourFin = production[fin].jour;
  // Arrêt le plus long ayant commencé pendant la zone -> libellé de l'annotation
  const arretZone = arrets
    .filter((a) => versDate(a.date) >= jourDebut && versDate(a.date) <= jourFin)
    .sort((a, b) => b.duree_h - a.duree_h)[0];

  // Disponibilité : moyenne des jours par unité, puis moyenne SIMPLE des unités (1 unité = 1 poids)
  const nomsUnites = [...new Set(dispo.map((l) => l.unite))];
  const unites = nomsUnites
    .map((nom) => {
      const jours = dispo.filter((l) => l.unite === nom);
      return { nom, moyenne: moyenne(jours.map((l) => l.disponibilite)), jours };
    })
    .sort((a, b) => b.moyenne - a.moyenne);                 // tri : la plus disponible en haut
  const dispoMoyenne = moyenne(unites.map((u) => u.moyenne));

  // Arrêts non planifiés et cause principale (en heures)
  const totalArrets = somme(arrets, "duree_h");
  const parCause = {};
  arrets.forEach((a) => (parCause[a.cause] = (parCause[a.cause] || 0) + a.duree_h));
  const [cause, heuresCause] = Object.entries(parCause).sort((a, b) => b[1] - a[1])[0];

  return {
    production, totalProd, totalPlan, realisation, ecartPoints, plusBas,
    zone: { debut, fin, arret: arretZone },
    unites, dispoMoyenne,
    arrets: [...arrets].sort((a, b) => b.duree_h - a.duree_h),
    totalArrets, cause, heuresCause,
  };
}

// ------------------------------------------------------------------ affichage
const ecrire = (id, texte) => (document.getElementById(id).textContent = texte);

function afficherEntete(r) {
  const mois = r.production[0].jour.toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
  const moisMaj = mois.charAt(0).toUpperCase() + mois.slice(1);           // "Octobre 2026"
  ecrire("titre", `Pilotage production & maintenance — ${moisMaj}`);
  ecrire("filtre-periode", moisMaj);
  document.title = `Pilotage production & maintenance — ${moisMaj}`;
}

function afficherIndicateurs(r) {
  ecrire("kpi-prod", tonnes(r.totalProd));
  ecrire("kpi-prod-detail", `plan : ${tonnes(r.totalPlan)}`);

  ecrire("kpi-real", pourcent(r.realisation));
  const detail = document.getElementById("kpi-real-detail");
  const pts = nombre(Math.abs(r.ecartPoints), 1);
  detail.textContent = r.ecartPoints < 0 ? `▼ ${pts} pt sous le plan` : `▲ ${pts} pt au-dessus du plan`;
  detail.classList.toggle("alerte", r.ecartPoints < 0);

  ecrire("kpi-dispo", pourcent(r.dispoMoyenne));
  ecrire("kpi-dispo-detail", `${r.unites.length} unités, objectif ${pourcent(OBJECTIF_DISPO, 0)}`);

  ecrire("kpi-arrets", heures(r.totalArrets));
  ecrire("kpi-arrets-detail", `${r.arrets.length} avis SAP PM`);

  ecrire("kpi-cause", r.cause);
  ecrire("kpi-cause-detail", `${heures(r.heuresCause)}, soit ${pourcent(r.heuresCause / r.totalArrets, 0)} des arrêts`);
}

/* Extension Chart.js maison : zone colorée de l'incident + étiquette du jour le plus bas */
const extensionAnnotations = {
  id: "annotations",
  beforeDatasetsDraw(chart, _args, options) {
    const { ctx, chartArea, scales } = chart;
    const x0 = scales.x.getPixelForValue(options.debut) - 8;
    const x1 = scales.x.getPixelForValue(options.fin) + 8;
    ctx.save();
    ctx.fillStyle = "rgba(224, 123, 79, 0.12)";
    ctx.fillRect(x0, chartArea.top, x1 - x0, chartArea.bottom - chartArea.top);
    ctx.restore();
  },
  afterDatasetsDraw(chart, _args, options) {
    const { ctx, scales } = chart;
    const x = scales.x.getPixelForValue(options.indexMin);
    const y = scales.y.getPixelForValue(options.valeurMin);
    ctx.save();
    ctx.font = "600 12px Inter, 'Segoe UI', sans-serif";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#1b2433";
    ctx.textAlign = "right";
    // Espace insécable classique : l'espace fine (U+202F) est presque invisible sur le canevas
    ctx.fillText(tonnes(options.valeurMin).replace(/\u202f/g, "\u00a0"), x - 8, y);
    if (options.libelle) {
      ctx.fillStyle = "#b5482a";
      const largeur = ctx.measureText(options.libelle).width;
      if (x + 12 + largeur <= chart.chartArea.right) {
        ctx.textAlign = "left";                       // place à droite du point : on y écrit
        ctx.fillText(options.libelle, x + 12, y);
      } else {                                        // écran étroit : en haut de la zone colorée
        const x0 = scales.x.getPixelForValue(options.debut) - 8;
        ctx.textAlign = "left";
        ctx.fillText(options.libelle, Math.max(chart.chartArea.left, Math.min(x0, chart.chartArea.right - largeur)), chart.chartArea.top + 10);
      }
    }
    ctx.restore();
  },
};

function afficherCourbe(r) {
  const p = r.production;
  const valeurs = p.map((l) => l.production_t);
  const plan = p.map((l) => l.plan_t);
  const a = r.zone.arret;
  const libelle = a
    ? `Arrêt ${a.equipement.charAt(0).toLowerCase()}${a.equipement.slice(1)} (${ABREVIATIONS[a.unite] || a.unite})`
    : "";
  const bas = Math.floor(Math.min(...valeurs) / 200) * 200;            // axe arrondi à 200 t
  const haut = Math.ceil(Math.max(...valeurs, ...plan) / 200) * 200;

  new Chart(document.getElementById("courbe"), {
    type: "line",
    data: {
      labels: p.map((l) => jourMois(l.jour)),
      datasets: [
        { label: "Production", data: valeurs, borderColor: "#2a78d6", borderWidth: 2, tension: 0.25,
          pointRadius: valeurs.map((_, i) => (i === p.indexOf(r.plusBas) ? 4 : 0)),
          pointBackgroundColor: "#2a78d6", pointHoverRadius: 5 },
        { label: "Plan", data: plan, borderColor: "#5b6473", borderWidth: 1.5, borderDash: [5, 4],
          pointRadius: 0, pointHoverRadius: 0 },
      ],
    },
    options: {
      maintainAspectRatio: false,
      animation: false,                                            // affichage immédiat (capture, PDF)
      interaction: { mode: "index", intersect: false },            // info-bulle sur toute la verticale
      scales: {
        y: { min: bas, max: haut, ticks: { stepSize: 200, callback: (v) => nombre(v), color: "#8a92a0" },
             grid: { color: "#eef0f3" }, border: { display: false } },
        x: { grid: { display: false }, ticks: { color: "#8a92a0", maxRotation: 0, autoSkip: false,
             callback: (_v, i) => (i % 5 === 0 || i === p.length - 1 ? jourMois(p[i].jour) : "") } },
      },
      plugins: {
        legend: { display: true, position: "top", align: "start",
                  labels: { boxWidth: 18, boxHeight: 2, color: "#5b6473", font: { size: 12 } } },
        tooltip: {
          callbacks: {
            title: (items) => p[items[0].dataIndex].jour.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" }),
            label: (item) => ` ${item.dataset.label} : ${tonnes(item.raw)}`,
            afterBody: (items) => {
              const l = p[items[0].dataIndex];
              return `Réalisation : ${pourcent(l.production_t / l.plan_t)}`;
            },
          },
        },
        annotations: { debut: r.zone.debut, fin: r.zone.fin, indexMin: p.indexOf(r.plusBas),
                       valeurMin: r.plusBas.production_t, libelle },
      },
    },
    plugins: [extensionAnnotations],
  });
}

function afficherBarres(r) {
  const position = (v) => ((v - ECHELLE_BARRES_MIN) / (1 - ECHELLE_BARRES_MIN)) * 100;   // en % de la piste
  const conteneur = document.getElementById("barres");
  conteneur.innerHTML = r.unites.map((u) => {
    const sous = u.moyenne < OBJECTIF_DISPO;
    return `<div class="barre-ligne">
        <span class="barre-nom">${u.nom}</span>
        <div class="barre-piste">
          <div class="barre" style="width:${Math.max(position(u.moyenne), 1)}%"></div>
          <span class="barre-valeur">${pourcent(u.moyenne)}${sous ? ' <span class="sous">▼<span class="mot"> sous l\'objectif</span></span>' : ""}</span>
        </div>
      </div>`;
  }).join("");
  // Trait de l'objectif, positionné dans la zone des pistes
  const premierePiste = conteneur.querySelector(".barre-piste");
  const decalage = premierePiste.offsetLeft;
  const trait = document.createElement("div");
  trait.className = "objectif";
  trait.style.left = `calc(${decalage}px + (100% - ${decalage}px) * ${position(OBJECTIF_DISPO) / 100})`;
  trait.innerHTML = `<span>objectif ${pourcent(OBJECTIF_DISPO, 0)}</span>`;
  conteneur.appendChild(trait);
  ecrire("barres-note", `▼ sous l'objectif · échelle de ${pourcent(ECHELLE_BARRES_MIN, 0)} à 100 %`);
}

function afficherChaleur(r) {
  const classeDe = (v) => CLASSES_CHALEUR.find((c) => v >= c.min);
  const nbJours = r.unites[0].jours.length;
  const grille = document.getElementById("chaleur");
  grille.style.gridTemplateColumns = `auto repeat(${nbJours}, minmax(10px, 1fr))`;

  let html = "";
  r.unites.forEach((u) => {
    html += `<span class="nom">${u.nom}</span>`;
    u.jours.forEach((j) => {
      const texte = `${u.nom} · ${jourMois(j.jour)} : ${pourcent(j.disponibilite)}`;
      html += `<span class="cellule ${classeDe(j.disponibilite).classe}" role="img" aria-label="${texte}" data-info="${texte}"></span>`;
    });
  });
  // Ligne des numéros de jour (1, 10, 20, 30)
  html += `<span></span>`;
  for (let d = 1; d <= nbJours; d++) html += `<span class="jour">${d === 1 || d % 10 === 0 ? d : ""}</span>`;
  grille.innerHTML = html;

  document.getElementById("legende").innerHTML = CLASSES_CHALEUR
    .map((c) => `<li><i class="${c.classe}"></i>${c.libelle}</li>`).join("");

  // Info-bulle au survol (souris) ou au toucher (téléphone)
  const bulle = document.createElement("div");
  bulle.className = "infobulle";
  bulle.hidden = true;
  document.body.appendChild(bulle);
  grille.addEventListener("pointermove", (e) => {
    const info = e.target.dataset && e.target.dataset.info;
    bulle.hidden = !info;
    if (info) {
      bulle.textContent = info;
      bulle.style.left = `${Math.min(e.clientX + 12, window.innerWidth - bulle.offsetWidth - 8)}px`;
      bulle.style.top = `${e.clientY - 36}px`;
    }
  });
  grille.addEventListener("pointerleave", () => (bulle.hidden = true));
}

function afficherTableau(r) {
  document.getElementById("arrets").innerHTML = r.arrets.map((a) => `<tr>
      <td>${jjmm(versDate(a.date))}</td><td>${a.equipement}</td><td>${a.unite}</td>
      <td>${a.cause}</td><td class="num">${heures(a.duree_h)}</td></tr>`).join("");
}

// ------------------------------------------------------------------ démarrage
async function demarrer() {
  try {
    const [production, dispo, arrets] = await Promise.all([
      charger("production_journaliere.csv"), charger("disponibilite_unites.csv"), charger("arrets.csv"),
    ]);
    const r = calculer(production, dispo, arrets);
    afficherEntete(r);
    afficherIndicateurs(r);
    afficherCourbe(r);
    afficherBarres(r);
    afficherChaleur(r);
    afficherTableau(r);
  } catch (err) {
    const zone = document.getElementById("erreur");
    zone.hidden = false;
    zone.textContent = `${err.message}. Ouvrez la page via un serveur (python -m http.server 8000 dans docs/), pas en double-cliquant sur le fichier.`;
    console.error(err);
  }
}
demarrer();
