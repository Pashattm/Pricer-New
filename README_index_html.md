# `templates/index.html` — l'interface du pricer

## Ce que fait ce fichier

C'est **toute l'interface** : une seule page HTML qui contient sa structure (HTML), son apparence (CSS) et son comportement (JavaScript). Flask la renvoie telle quelle sur la route `/` ; ensuite, la page parle au serveur uniquement par des appels `/api/...` en JSON.

**Pourquoi un seul fichier, sans React ni Vue ?**
- Pas d'étape de compilation, pas de `npm install` : un étudiant ouvre un fichier et voit tout.
- Le pricer n'a besoin que de formulaires, de tableaux et de graphiques simples : le JavaScript du navigateur suffit.
- Les graphiques sont dessinés en **SVG à la main** (une centaine de lignes) plutôt qu'avec une bibliothèque : aucune dépendance externe, et l'on comprend exactement ce qui est tracé.

**Limite atteinte :** le fichier devient long à mesure que les produits s'ajoutent. Pour le garder lisible, tout ce qui est commun à plusieurs onglets est écrit **une seule fois** : appels au serveur (`appelApi`), comportement des formulaires (`surSoumission`), recherche de ticker, données de marché, choix de la volatilité, tracé des graphiques, export PDF. Un onglet ne contient que ce qui lui est propre.

**Règle de partage des rôles :** la page aide l'utilisateur (champs masqués, messages, bornes affichées), mais **le serveur revalide tout** (`validation.py`). Une vérification côté page n'est qu'un confort ; elle ne remplace jamais celle du serveur.

**Style visuel :** un terminal de marché (fond noir, texte ambre, bandeaux bleus, chiffres en chasse fixe). Les chiffres sont en police à chasse fixe (`IBM Plex Mono`, `tabular-nums`) pour que les colonnes de nombres restent alignées.

Le fichier se lit en cinq parties : l'en-tête, le CSS, le HTML, le JavaScript, la fin de page.

---

# Le code, ligne par ligne

## Partie 1 — l'en-tête de la page

### 1. En-tête du document

```html
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PRICER — Options, Forward, Stratégies &amp; Produits structurés</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
…
</style>
</head>
<body>
```

- `<!doctype html>` : la page est du HTML5 moderne (sans cette ligne, le navigateur passe en mode « quirks » et calcule les tailles différemment).
- `<html lang="fr">` : la langue sert aux lecteurs d'écran et à la césure.
- `<meta charset="utf-8">` : les accents, σ, ρ, ₀ s'affichent correctement.
- `<meta name="viewport" ...>` : sur téléphone, la page prend la largeur de l'écran au lieu d'être réduite.
- `<title>` : le titre de l'onglet du navigateur, qui annonce les produits de **cette** version.
- Les trois `<link>` vers Google Fonts : `preconnect` ouvre la connexion à l'avance (affichage plus rapide), puis la feuille charge **IBM Plex Mono** (chiffres) et **IBM Plex Sans Condensed** (texte). `display=swap` affiche d'abord une police de secours pour ne jamais bloquer la page. Sans internet, les polices de secours définies plus bas prennent le relais.
- `<style>` ouvre la partie CSS ; `</style></head><body>` la ferme et commence le contenu visible.

## Partie 2 — le CSS (apparence)

### 2. Les variables de couleur (`:root`)

```css
/* Terminal de marché : fond noir, texte ambre, bandeaux bleus, chiffres en chasse fixe. */
:root{
  --bg:#000;            /* fond de l'écran */
  --panel:#07090d;      /* fond des panneaux */
  --bar:#102a52;        /* bandeaux de titre bleus */
  --line:#262b33;       /* séparateurs */
  --amber:#ffa028;      /* couleur maîtresse : titres, saisies, focus */
  --yellow:#f5d547;     /* mise en avant ponctuelle */
  --text:#e6e6e6;       /* valeurs */
  --muted:#8a8f98;      /* libellés secondaires */
  --cyan:#5cc8ff;
  --green:#3ddc84;
  --red:#ff5c5c;
  --mono:'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  --cond:'IBM Plex Sans Condensed', 'Arial Narrow', system-ui, sans-serif;
}
```

- `:root{...}` définit des **variables CSS** (`--nom: valeur`), réutilisées partout avec `var(--nom)`. Pour changer le thème, on ne modifie que ces lignes.
- Chaque couleur a un rôle écrit en commentaire : fond, panneaux, bandeaux, séparateurs, ambre (couleur maîtresse : titres, saisies, focus), jaune (mise en avant), texte, gris (libellés secondaires), cyan, vert (gain), rouge (perte, erreur).
- `--mono` et `--cond` : les deux familles de polices, chacune suivie de polices de secours si la police web n'est pas chargée.

### 3. Base de la page

```css
/* --- Base de la page --- */
*{box-sizing:border-box}
html{color-scheme:dark}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 var(--cond)}
```

- `*{box-sizing:border-box}` : la largeur d'un élément **inclut** sa bordure et sa marge intérieure. Sans cette règle, un champ `width:100%` avec du padding déborde de son conteneur.
- `html{color-scheme:dark}` : demande au navigateur des contrôles natifs sombres (barres de défilement, listes déroulantes).
- `body{...}` : pas de marge par défaut, fond noir, texte clair, police condensée 14 px avec un interligne de 1,45.

### 4. Barre de commande en haut

```css
/* --- Barre de commande en haut --- */
.topbar{display:flex;align-items:stretch;border-bottom:1px solid var(--line);background:#000;font-family:var(--mono);font-size:13px}
.brand{background:var(--amber);color:#000;font-weight:600;padding:8px 14px;letter-spacing:.06em}
.cmd{flex:1;display:flex;align-items:center;gap:10px;padding:0 14px;color:var(--amber);min-width:0}
.cmd .prompt{color:var(--muted)}
.cmd .go{border:1px solid var(--green);color:var(--green);padding:0 6px;font-size:11px;line-height:18px}
.cmd .caret{display:inline-block;width:8px;height:15px;background:var(--amber);animation:blink 1.1s steps(1) infinite;vertical-align:-2px}
.cmd .desc{color:var(--muted);overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.clock{padding:0 14px;display:flex;align-items:center;gap:12px;color:var(--yellow);font-variant-numeric:tabular-nums;white-space:nowrap}
.clock .live{color:var(--green)}
.clock .live::before{content:'';display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--green);margin-right:6px;vertical-align:1px}
@keyframes blink{50%{opacity:0}}
```

- `.topbar` : une ligne flexible (`display:flex`) en police à chasse fixe.
- `.brand` : le pavé ambre « PRICER ».
- `.cmd` : la zone de commande, qui prend toute la place restante (`flex:1`) ; `min-width:0` autorise le texte à rétrécir au lieu de pousser l'horloge hors de l'écran.
- `.prompt`, `.go` : le chevron `>` et l'étiquette verte `<GO>`, comme sur un terminal.
- `.caret` : le curseur clignotant, un petit rectangle animé par `@keyframes blink` (opacité 0 à mi-parcours ; `steps(1)` donne un clignotement net, sans fondu).
- `.desc` : la description de la fonction ; `text-overflow:ellipsis` la coupe avec « … » si l'écran est étroit.
- `.clock` : l'horloge en jaune ; `tabular-nums` évite que les chiffres « dansent » quand les secondes changent. `.live::before` dessine la pastille verte devant « PARIS ».

### 5. Zone principale

```css
/* --- Zone principale --- */
main{max-width:1320px;margin:auto;padding:14px 16px 28px}
```

- `main` : largeur maximale de 1 320 px, centrée (`margin:auto`), avec des marges intérieures.

### 6. Menu des onglets

```css
/* --- Menu des fonctions, numérotées comme sur un terminal --- */
.tabs{display:flex;flex-wrap:wrap;gap:2px;margin-bottom:12px;border-bottom:1px solid var(--line)}
.tab{background:none;border:0;border-bottom:2px solid transparent;color:var(--text);font:500 14px var(--cond);padding:8px 14px 7px;cursor:pointer}
.tab .key{color:var(--amber);font-family:var(--mono);font-size:12px;margin-right:4px}
.tab:hover{background:#0e1218}
.tab.active{background:var(--bar);border-bottom-color:var(--amber);color:#fff}
.tab:focus-visible{outline:1px solid var(--amber);outline-offset:-1px}
```

- `.tabs` : les boutons d'onglet sur une ligne, qui passent à la ligne si besoin (`flex-wrap`).
- `.tab` : bouton sans fond ni bordure, sauf un trait bas transparent qui devient ambre quand l'onglet est actif.
- `.tab .key` : le numéro « 1) », « 2) »… en ambre : c'est aussi le raccourci clavier.
- `.tab:hover`, `.tab.active` : survol et onglet actif (bandeau bleu).
- `.tab:focus-visible` : un contour visible quand on navigue **au clavier** (et seulement au clavier : `focus-visible` ne s'affiche pas au clic de souris).

### 7. Mise en page en deux colonnes

```css
/* --- Mise en page : formulaire à gauche, résultats à droite --- */
.grid{display:grid;grid-template-columns:340px minmax(0,1fr);gap:12px;align-items:start}
.card{background:var(--panel);border:1px solid var(--line);border-radius:2px}
.grid > .card{position:sticky;top:12px;max-height:calc(100vh - 24px);overflow-y:auto;scrollbar-color:#333 transparent}
form{padding:0 14px 16px}
```

- `.grid` : une grille CSS à deux colonnes : 340 px pour le formulaire, le reste pour les résultats. `minmax(0,1fr)` empêche un graphique large de faire déborder la colonne.
- `.card` : le panneau de base (fond, bordure).
- `.grid > .card` : le formulaire est **collant** (`position:sticky`) : il reste visible quand on fait défiler des résultats longs, et défile lui-même s'il est plus haut que l'écran.
- `form{padding:...}` : marges intérieures des formulaires.

### 8. Titres de section

```css
/* --- Titres de section : bandeau bleu pleine largeur, texte ambre --- */
h2{margin:0 -14px 12px;padding:5px 14px;background:var(--bar);color:var(--amber);font:600 12px var(--mono);text-transform:uppercase;letter-spacing:.08em}
form h2{margin-top:0}
form h2 + .fields, form h2 + .hint{margin-top:0}
.chart-card h2{margin:-14px -14px 12px}
```

- `h2` : bandeau bleu en majuscules. Les marges négatives (`margin:0 -14px`) font déborder le bandeau sur le padding du panneau : il touche les deux bords.
- `form h2 + .fields` : le sélecteur `+` vise l'élément **juste après** un titre, pour supprimer un espace en double.
- `.chart-card h2` : même effet dans les cartes de résultats, qui ont 14 px de padding.

### 9. Champs de formulaire

```css
/* --- Champs de formulaire --- */
.fields{display:grid;grid-template-columns:1fr 1fr;gap:10px 10px;margin-bottom:16px}
.full{grid-column:1/-1}
label{display:block;font-size:12px;font-weight:500;color:var(--muted);margin-bottom:3px}
input,select{width:100%;background:#0d0f13;border:1px solid #343a44;border-radius:2px;color:var(--amber);padding:6px 8px;font:500 14px var(--mono);min-height:32px;font-variant-numeric:tabular-nums}
input::placeholder{color:#5b616b}
input:disabled{color:var(--muted);background:#0a0b0e}
input:focus,select:focus{outline:none;border-color:var(--amber);box-shadow:0 0 0 1px var(--amber)}
input:invalid:not(:focus):not(:placeholder-shown){border-color:var(--red)}
select{appearance:none;cursor:pointer;padding-right:26px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0h10L5 6z' fill='%23ffa028'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 9px center}
select:disabled{opacity:.7;cursor:default}
input[type=number]::-webkit-inner-spin-button{opacity:.35}
.hint{font-size:12px;color:var(--muted);margin:6px 0 0}
.check{display:flex;align-items:flex-start;gap:8px;font-size:13px;font-weight:500;color:var(--text);cursor:pointer;margin:0}
.check input{width:14px;height:14px;min-height:0;margin:2px 0 0;accent-color:var(--amber);flex:none}
```

- `.fields` : une grille de deux colonnes de champs ; `.full` fait occuper toute la ligne à un champ (`grid-column:1/-1` = de la première à la dernière colonne).
- `label` : libellés en gris, au-dessus du champ.
- `input,select` : fond sombre, texte ambre en chasse fixe, hauteur minimale de 32 px (facile à cliquer).
- `::placeholder`, `:disabled` : texte d'exemple et champs désactivés en gris.
- `:focus` : bordure ambre au lieu du contour bleu par défaut du navigateur.
- `input:invalid:not(:focus):not(:placeholder-shown)` : un champ invalide (hors `min`/`max`, ou refusé par `setCustomValidity`) passe en rouge, mais **pas pendant la saisie** et pas s'il est vide : on ne crie pas sur l'utilisateur avant qu'il ait fini.
- `select{appearance:none; background-image:url("data:image/svg+xml,...")}` : on retire la flèche native (différente selon les navigateurs) et on dessine un petit triangle ambre en SVG directement dans le CSS (une « data URL » : pas de fichier image à part).
- `::-webkit-inner-spin-button` : les petites flèches des champs numériques, rendues discrètes.
- `.hint` : les phrases d'aide sous les champs.
- `.check` et `.check input` : les cases à cocher avec leur libellé sur la même ligne ; `accent-color` colore la case en ambre ; `flex:none` empêche la case de s'écraser quand le texte est long.

### 10. Blocs repliables

```css
/* --- Blocs repliables (details) --- */
details{border-top:1px solid var(--line);padding-top:10px;margin-bottom:12px}
details summary{cursor:pointer;color:var(--amber);font:500 12px var(--mono);text-transform:uppercase;letter-spacing:.06em;list-style:none}
details summary::-webkit-details-marker{display:none}
details summary::before{content:'+ ';color:var(--muted)}
details[open] summary::before{content:'− '}
```

- `<details>`/`<summary>` est l'élément HTML natif « cliquer pour déplier » : aucun JavaScript nécessaire.
- `list-style:none` et `::-webkit-details-marker{display:none}` retirent le triangle par défaut (deux règles car Chrome/Safari et Firefox ne le gèrent pas pareil).
- `summary::before` affiche « + » replié et « − » déplié (`details[open]`).

### 11. Bouton Calculer et messages d'état

```css
/* --- Bouton Calculer et messages d'état --- */
button.primary{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;margin-top:4px;border:0;border-radius:2px;background:var(--amber);color:#000;padding:9px 14px;font:600 13px var(--mono);letter-spacing:.06em;text-transform:uppercase;cursor:pointer}
button.primary::after{content:'GO';font-size:10px;border:1px solid #000;padding:0 5px;line-height:15px}
button.primary:hover{background:#ffb34f}
button.primary:focus-visible{outline:2px solid var(--yellow);outline-offset:2px}
button.primary:disabled{opacity:.55;cursor:wait}
.status{font:12px var(--mono);color:var(--green);margin:8px 0 0;min-height:18px}
.status.error{color:var(--red)}
```

- `button.primary` : le grand bouton ambre ; `::after` ajoute l'étiquette « GO » sans la mettre dans le HTML.
- `:hover`, `:focus-visible` : survol plus clair, contour jaune au clavier.
- `:disabled{cursor:wait}` : pendant un calcul, le bouton est grisé et le curseur indique l'attente.
- `.status` : le message sous le bouton, vert ; `min-height` réserve sa place pour que la page ne « saute » pas quand il apparaît. `.status.error` : rouge en cas d'erreur.

### 12. Résultats

```css
/* --- Résultats --- */
.results{display:flex;flex-direction:column;gap:12px;min-width:0}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);background:var(--panel);border:1px solid var(--line);border-bottom:0;border-radius:2px}
.metric{padding:10px 14px 12px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);min-width:0}
.metric:nth-child(3n){border-right:0}
.metric p{margin:0 0 2px;font:500 11px var(--mono);color:var(--amber);text-transform:uppercase;letter-spacing:.06em}
.metric strong{display:block;font:500 24px var(--mono);color:#fff;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.metric strong.pos{color:var(--green)}
.metric strong.neg{color:var(--red)}
```

- `.results` : la colonne de droite, une pile verticale de cartes.
- `.metrics` : la grille des indicateurs (3 colonnes) ; `.metric` : une case ; `:nth-child(3n)` retire la bordure droite de la dernière case de chaque ligne.
- `.metric p` : le libellé en petites majuscules ambre ; `.metric strong` : la valeur en grand, coupée avec « … » si elle est trop longue.
- `strong.pos` et `strong.neg` : valeur verte ou rouge (utilisé pour la marge émetteur, positive ou négative).

### 13. Graphiques et tableaux

```css
/* --- Graphiques et tableaux --- */
.chart-card{padding:14px}
svg{width:100%;height:auto;display:block}
svg text{font:11px var(--mono);fill:var(--muted)}
.greeks-table{width:100%;border-collapse:collapse;font:13px var(--mono);font-variant-numeric:tabular-nums}
.greeks-table th,.greeks-table td{text-align:left;padding:5px 8px;border-bottom:1px solid #161a20}
.greeks-table th{color:var(--muted);font-weight:500;font-size:11px;text-transform:uppercase;letter-spacing:.06em}
.greeks-table td:first-child{color:var(--amber)}
.greeks-table td:not(:first-child){text-align:right;color:var(--text)}
.greeks-table th:not(:first-child){text-align:right}
.greeks-table tbody tr:nth-child(even){background:#0b0e13}
.greeks-table tbody tr:hover{background:#121823}
.chart-card details{border-top:0;margin:12px 0 0;padding-top:0}
.chart-note{font-size:12px;color:var(--muted);margin:10px 0 0}
```

- `.chart-card` : carte qui contient un graphique ou un tableau.
- `svg{width:100%;height:auto}` : les graphiques SVG s'adaptent à la largeur de la carte en gardant leurs proportions (grâce à leur `viewBox`).
- `svg text` : police et couleur des textes des axes.
- `.greeks-table` : style commun à **tous** les tableaux (grecques, calendriers, flux) : chasse fixe, première colonne ambre, nombres alignés à droite, lignes alternées (`nth-child(even)`) et surlignage au survol.
- `.chart-card details` et `.chart-note` : bloc repliable et petite note sous un graphique.

### 14. Zone vide et suggestions

```css
/* --- Zone vide et suggestions de tickers --- */
.empty{border:1px dashed #2c323b;color:var(--muted);font:13px var(--mono);padding:48px 16px;text-align:center}
.empty::after{content:'';display:inline-block;width:8px;height:14px;background:var(--amber);margin-left:6px;vertical-align:-2px;animation:blink 1.1s steps(1) infinite}
.ticker-hit{padding:7px 10px;cursor:pointer;border-bottom:1px solid var(--line);font:13px var(--mono);background:#0d0f13}
.ticker-hit:hover{background:var(--bar)}
.ticker-hit strong{color:var(--amber)}
```

- `.empty` : le cadre pointillé « Lance un calcul… » avant le premier résultat, avec un curseur clignotant (`::after`).
- `.ticker-hit` : une ligne de la liste des tickers proposés ; le symbole en ambre (`strong`), surlignage bleu au survol.

### 15. Règles générales et petits écrans

```css
/* --- Règles générales et petits écrans --- */
[hidden]{display:none !important}
@media (prefers-reduced-motion:reduce){.cmd .caret,.empty::after{animation:none}}
@media(max-width:900px){
  .grid{grid-template-columns:1fr}
  .grid > .card{position:static;max-height:none}
  .metrics{grid-template-columns:1fr 1fr}
  .metric:nth-child(3n){border-right:1px solid var(--line)}
  .metric:nth-child(2n){border-right:0}
  .clock .date,.cmd .desc{display:none}
}
```

- `[hidden]{display:none !important}` : **règle importante**. L'attribut HTML `hidden` masque un élément, mais une règle CSS comme `.grid{display:grid}` peut l'emporter et le réafficher. `!important` garantit que `hidden` gagne toujours. Le JavaScript masque et affiche tout avec `element.hidden = true/false`.
- `prefers-reduced-motion` : si l'utilisateur a demandé moins d'animations dans son système, les curseurs ne clignotent plus (accessibilité).
- `@media(max-width:900px)` : sur un écran étroit, une seule colonne (formulaire puis résultats), le formulaire n'est plus collant, les indicateurs passent sur 2 colonnes, et la date et la description de la barre du haut sont masquées.

### 16. Indicateurs des produits structurés

```css
/* --- Indicateurs des produits structurés (4 colonnes) --- */
.structured-metrics{grid-template-columns:repeat(4,minmax(0,1fr))}
.structured-metrics .metric{border-right:1px solid var(--line)}
.structured-metrics .metric:nth-child(4n){border-right:0}
@media(max-width:1100px){.structured-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.structured-metrics .metric:nth-child(2n){border-right:0}}
@media(max-width:550px){.structured-metrics{grid-template-columns:1fr}.structured-metrics .metric{border-right:0}}
```

- Les produits structurés affichent 8 indicateurs : une grille de **4 colonnes** (deux lignes de 4) au lieu de 3.
- `:nth-child(4n)` : pas de bordure à droite de la dernière case de chaque ligne.
- Deux paliers responsives : 2 colonnes sous 1 100 px, 1 colonne sous 550 px.

## Partie 3 — le HTML (structure)

### 17. Barre du haut et menu des onglets

```html
<header class="topbar">
  <div class="brand">PRICER</div>
  <div class="cmd">
    <span class="prompt">&gt;</span>
    <span id="cmd-code">OPT</span>
    <span class="go">&lt;GO&gt;</span>
    <span class="caret" aria-hidden="true"></span>
    <span class="desc" id="cmd-desc">Options vanilles</span>
  </div>
  <div class="clock"><span class="live">PARIS</span><span class="date" id="clock-date"></span><span id="clock-time"></span></div>
</header>

<main>

  <div class="tabs" role="tablist">
    <button class="tab active" data-tab="options"><span class="key">1)</span>Options</button>
    <button class="tab" data-tab="forward"><span class="key">2)</span>Forward / Future</button>
    <button class="tab" data-tab="strategies"><span class="key">3)</span>Stratégies</button>
    <button class="tab" data-tab="structured"><span class="key">4)</span>Produits structurés</button>
    <button class="tab" data-tab="chantier"><span class="key">5)</span>Chantier</button>
  </div>
```

- `<header class="topbar">` : la barre de commande. `cmd-code` et `cmd-desc` ont un `id` car le JavaScript change leur texte à chaque onglet (« OPT · Options vanilles », « FWD · Contrats à terme »…).
- `aria-hidden="true"` sur le curseur clignotant : purement décoratif, les lecteurs d'écran l'ignorent.
- `clock-date` et `clock-time` : remplis chaque seconde par `majHorloge()`.
- `<main>` puis `<div class="tabs" role="tablist">` : le menu. Chaque bouton porte `data-tab="..."`, le nom de l'onglet : c'est ce qui relie le bouton au panneau `panel-<nom>` (le JavaScript lit `btn.dataset.tab`). Le numéro affiché (`<span class="key">`) correspond au raccourci clavier.

### 18. Onglet Options (HTML)

```html
  <!-- ===================== ONGLET OPTIONS ===================== -->
  <section id="panel-options" class="grid">
    <div class="card">
      <form id="form-options">
        <h2>Instrument</h2>
        <div class="fields">
          <div class="full"><label for="opt-instrument">Instrument</label>
            <select id="opt-instrument">
              <option value="vanilla">Option classique</option>
              <option value="cash">Digitale cash-or-nothing</option>
              <option value="asset">Digitale asset-or-nothing</option>
            </select>
          </div>
          <div id="digital-payout-wrap" hidden><label for="digital-payout">Paiement fixe de la digitale</label><input id="digital-payout" type="number" min="0" step="any" value="1"></div>
          <p id="digital-note" class="hint full" hidden>Digitale européenne : paiement fixe ou livraison du sous-jacent si la condition finale est satisfaite.</p>
        </div>
        <h2>Sous-jacent</h2>
        <div class="fields">
          <div class="full" style="position:relative">
            <label for="opt-ticker">Chercher un ticker</label>
            <input id="opt-ticker" type="text" placeholder="ex : AAPL, MC.PA..." autocomplete="off">
            <div id="opt-ticker-results" class="card" style="position:absolute;z-index:10;width:100%;margin-top:2px;max-height:180px;overflow-y:auto;" hidden></div>
            <p id="opt-ticker-status" class="hint"></p>
          </div>
        </div>
        <h2>Paramètres du contrat</h2>
        <div class="fields">
          <div><label for="opt-side">Position</label>
            <select id="opt-side"><option value="buy">Achat (long)</option><option value="sell">Vente (short)</option></select>
          </div>
          <div><label for="opt-type">Type</label>
            <select id="opt-type"><option value="call">Call</option><option value="put">Put</option></select>
          </div>
          <div><label for="opt-style">Exercice</label>
            <select id="opt-style"><option value="european">Européen</option><option value="american">Américain</option></select>
          </div>
          <div><label for="opt-method">Méthode</label>
            <select id="opt-method"></select>
          </div>
          <div><label for="opt-s0">Spot S₀</label><input id="opt-s0" type="number" value="100" min="0.01" step="any"></div>
          <div><label for="opt-k">Strike K</label><input id="opt-k" type="number" value="100" min="0.01" step="any"></div>
          <div>
            <label for="opt-sigma-source">Volatilité σ</label>
            <select id="opt-sigma-source">
              <option value="manual">Manuelle</option>
              <option value="hist">Historique (1 an)</option>
              <option value="vix">VIX (S&amp;P 500)</option>
            </select>
          </div>
          <div id="opt-sigma-manual-wrap"><label for="opt-sigma">σ manuelle (%)</label><input id="opt-sigma" type="number" value="20" min="0.01" step="any"></div>
          <div id="opt-sigma-mkt-wrap" hidden><label id="opt-sigma-mkt-label">σ marché</label><input id="opt-sigma-mkt-display" type="text" disabled></div>
          <div><label for="opt-t">Maturité T (années)</label><input id="opt-t" type="number" value="1" min="0.001" step="any"></div>
          <div><label for="opt-r">Taux r (%)</label><input id="opt-r" type="number" value="5" min="-20" step="any"></div>
          <div><label for="opt-q">Dividende q (%)</label><input id="opt-q" type="number" value="0" min="0" step="any"></div>
          <div class="full" id="opt-nsims-wrap" hidden>
            <label for="opt-nsims">Nombre de simulations</label>
            <input id="opt-nsims" type="number" value="30000" min="100" step="100">
          </div>
        </div>
        <p class="hint" id="opt-k-hint"></p>
        <button class="primary" type="submit">Calculer</button>
        <p id="opt-status" class="status" role="status" aria-live="polite"></p>
      </form>
    </div>

    <div class="results" id="opt-results">
      <div class="empty">Lance un calcul pour voir les résultats.</div>
    </div>
  </section>
```

La structure est la même pour tous les onglets : `<section id="panel-..." class="grid">` contient une **carte formulaire** à gauche et une **colonne de résultats** à droite (`<div class="results">`) qui affiche d'abord un message vide.

**Bloc Instrument**
- `opt-instrument` : option classique, digitale *cash-or-nothing* (paie un montant fixe) ou *asset-or-nothing* (livre le sous-jacent).
- `digital-payout-wrap` et `digital-note` ont l'attribut `hidden` : ils n'apparaissent que pour une digitale (géré en JavaScript).

**Bloc Sous-jacent : la recherche de ticker**
- `style="position:relative"` sur le conteneur et `position:absolute` sur la liste des résultats : la liste s'affiche **par-dessus** les champs suivants, juste sous la saisie, sans décaler la page.
- `autocomplete="off"` : le navigateur ne propose pas ses propres suggestions par-dessus les nôtres.
- `opt-ticker-status` : la ligne qui affiche « Recherche… », puis le spot et les volatilités du ticker choisi.

**Bloc Paramètres du contrat**
- Position, type, exercice, méthode : des `<select>`. La liste des méthodes (`opt-method`) est **vide** dans le HTML : le JavaScript la remplit selon le style d'exercice (une option américaine n'a qu'une méthode ici).
- Spot, strike, maturité, taux, dividende : des `<input type="number">` avec `min` (ex. `min="0.01"` : pas de spot nul) et `step="any"` (toute décimale acceptée ; sans cela, le navigateur refuse 100,5 avec un pas par défaut de 1).
- **Volatilité** : un choix de source (manuelle, historique 1 an, VIX), puis deux zones dont une seule est visible : la saisie manuelle, ou l'affichage en lecture seule (`disabled`) de la vol de marché.
- Taux et dividende sont saisis en **pourcentage** (5 pour 5 %) ; le serveur les convertit en décimal.
- `opt-nsims-wrap` : le nombre de simulations, caché tant que la méthode ne simule rien (Black-Scholes sur une option classique).

**Fin du formulaire**
- `opt-k-hint` : affiche les bornes acceptées pour le strike.
- `<button class="primary" type="submit">` : le clic (ou Entrée dans un champ) déclenche l'événement `submit` du formulaire, intercepté par `surSoumission`.
- `role="status" aria-live="polite"` sur le message : un lecteur d'écran annonce le message quand il change, sans interrompre l'utilisateur.

### 19. Onglet Forward / Future (HTML)

```html
  <!-- ===================== ONGLET FORWARD ===================== -->
  <section id="panel-forward" class="grid" hidden>
    <div class="card">
      <form id="form-forward">
        <h2>Paramètres du contrat à terme</h2>
        <div class="fields">
          <div class="full"><label for="fwd-side">Position</label>
            <select id="fwd-side"><option value="buy">Achat (long)</option><option value="sell">Vente (short)</option></select>
          </div>
          <div><label for="fwd-s0">Spot S₀</label><input id="fwd-s0" type="number" value="100" min="0.01" step="any"></div>
          <div><label for="fwd-k">Prix contractuel K</label><input id="fwd-k" type="number" value="100" min="0.01" step="any"></div>
          <div><label for="fwd-t">Maturité T (années)</label><input id="fwd-t" type="number" value="1" min="0.001" step="any"></div>
          <div><label for="fwd-r">Taux r (%)</label><input id="fwd-r" type="number" value="5" min="-20" step="any"></div>
          <div class="full"><label for="fwd-q">Dividende q (%)</label><input id="fwd-q" type="number" value="0" min="0" step="any"></div>
        </div>
        <button class="primary" type="submit">Calculer</button>
        <p id="fwd-status" class="status" role="status" aria-live="polite"></p>
      </form>
    </div>

    <div class="results" id="fwd-results">
      <div class="empty">Lance un calcul pour voir les résultats.</div>
    </div>
  </section>
```

- Même structure que l'onglet Options, plus simple : position, spot, prix contractuel K, maturité, taux, dividende.
- Pas de volatilité : le prix à terme `F = S0·e^{(r−q)T}` n'en dépend pas (le forward est linéaire en S, sans optionnalité).
- Pas de recherche de ticker : on raisonne volontairement sur un exemple simple.
- `hidden` sur la section : seul l'onglet Options est visible au chargement.

### 20. Onglet Stratégies (HTML)

```html
  <!-- ===================== ONGLET STRATÉGIES ===================== -->
  <section id="panel-strategies" class="grid" hidden>
    <div class="card">
      <form id="form-strategy">
        <h2>Sous-jacent</h2>
        <div class="fields">
          <div class="full" style="position:relative">
            <label for="strat-ticker">Chercher un ticker</label>
            <input id="strat-ticker" type="text" placeholder="ex : AAPL, MC.PA..." autocomplete="off">
            <div id="strat-ticker-results" class="card" style="position:absolute;z-index:10;width:100%;margin-top:2px;max-height:180px;overflow-y:auto;" hidden></div>
            <p id="strat-ticker-status" class="hint"></p>
          </div>
        </div>
        <h2>Construire une stratégie</h2>
        <div class="fields">
          <div class="full"><label for="strat-name">Stratégie</label>
            <select id="strat-name">
              <option value="covered_call">Covered call</option>
              <option value="protective_put">Protective put</option>
              <option value="straddle">Straddle</option>
              <option value="strangle">Strangle</option>
              <option value="call_spread">Call spread</option>
              <option value="put_spread">Put spread</option>
              <option value="collar">Collar</option>
            </select>
          </div>

          <div id="strat-side-wrap" class="full" hidden>
            <label for="strat-side">Sens (call+put ensemble)</label>
            <select id="strat-side"><option value="buy">Achat</option><option value="sell">Vente</option></select>
          </div>

          <div><label for="strat-s0">Spot S₀</label><input id="strat-s0" type="number" value="100" min="0.01" step="any"></div>
          <div id="strat-k-wrap"><label id="strat-k-label" for="strat-k">Strike K</label><input id="strat-k" type="number" value="100" min="0.01" step="any"></div>
          <div id="strat-k1-wrap" hidden><label id="strat-k1-label" for="strat-k1">Strike K1</label><input id="strat-k1" type="number" value="95" min="0.01" step="any"></div>
          <div id="strat-k2-wrap" hidden><label id="strat-k2-label" for="strat-k2">Strike K2</label><input id="strat-k2" type="number" value="110" min="0.01" step="any"></div>
          <div><label for="strat-t">Maturité T (années)</label><input id="strat-t" type="number" value="0.5" min="0.001" step="any"></div>
          <div>
            <label for="strat-sigma-source">Volatilité σ</label>
            <select id="strat-sigma-source">
              <option value="manual">Manuelle</option>
              <option value="hist">Historique (1 an)</option>
              <option value="vix">VIX (S&amp;P 500)</option>
            </select>
          </div>
          <div id="strat-sigma-manual-wrap"><label for="strat-sigma">σ manuelle (%)</label><input id="strat-sigma" type="number" value="20" min="0.01" step="any"></div>
          <div id="strat-sigma-mkt-wrap" hidden><label id="strat-sigma-mkt-label">σ marché</label><input id="strat-sigma-mkt-display" type="text" disabled></div>
          <div><label for="strat-r">Taux r (%)</label><input id="strat-r" type="number" value="5" min="-20" step="any"></div>
          <div><label for="strat-q">Dividende q (%)</label><input id="strat-q" type="number" value="0" min="0" step="any"></div>
          <div><label for="strat-qty">Quantité</label><input id="strat-qty" type="number" value="1" min="0.01" step="any"></div>
        </div>
        <p class="hint" id="strat-k-hint"></p>
        <button class="primary" type="submit">Calculer</button>
        <p id="strat-status" class="status" role="status" aria-live="polite"></p>
      </form>
    </div>

    <div class="results" id="strat-results">
      <div class="empty">Lance un calcul pour voir les résultats.</div>
    </div>
  </section>
```

- Recherche de ticker identique à l'onglet Options (préfixe `strat-`).
- `strat-name` : la liste des 7 stratégies (covered call, protective put, straddle, strangle, call spread, put spread, collar). Les `value` sont les noms attendus par le serveur.
- `strat-side-wrap` : le sens (achat ou vente) n'a de sens que pour les stratégies symétriques (straddle, strangle) ; caché sinon.
- **Trois champs de strike pour sept stratégies** : `strat-k` (un seul strike), `strat-k1` et `strat-k2` (deux strikes). Leurs libellés ont un `id` (`strat-k1-label`…) car le JavaScript les renomme : « Strike put » / « Strike call » pour un strangle, « Strike K1 (achat) » / « Strike K2 (vente) » pour un call spread. Moins de champs à maintenir qu'un formulaire par stratégie.
- Volatilité avec les trois mêmes sources que l'onglet Options.
- `strat-qty` : la quantité multiplie toute la stratégie.

### 21. Onglet Produits structurés (HTML)

```html
  <!-- ===================== ONGLET PRODUITS STRUCTURÉS ===================== -->
  <section id="panel-structured" class="grid" hidden>
    <div class="card">
      <div style="padding:0 14px 14px">
        <h2>Produit</h2>
        <label for="struct-product">Type de produit structuré</label>
        <select id="struct-product">
          <option value="" selected disabled>Choisir un produit</option>
          <option value="phoenix">Phoenix</option>
          <option value="autocall_plain">Athéna (Autocall Plain) — coupons accumulés</option>
        </select>
      </div>
<form id="form-phoenix" data-product="phoenix" hidden>
        <h2>Sous-jacent</h2>
        <div class="fields">
          <div class="full" style="position:relative">
            <label for="phx-ticker">Chercher un ticker (facultatif)</label>
            <input id="phx-ticker" type="text" placeholder="ex : AAPL, MC.PA..." autocomplete="off">
            <div id="phx-ticker-results" class="card" style="position:absolute;z-index:10;width:100%;margin-top:2px;max-height:180px;overflow-y:auto;" hidden></div>
            <p id="phx-ticker-status" class="hint">Sans ticker, le sous-jacent part de 100.</p>
          </div>
          <div>
            <label for="phx-sigma-source">Volatilité σ</label>
            <select id="phx-sigma-source">
              <option value="manual">Manuelle</option>
              <option value="hist">Historique (1 an)</option>
              <option value="vix">VIX (S&amp;P 500)</option>
            </select>
          </div>
          <div id="phx-sigma-manual-wrap"><label for="phx-sigma">σ (%)</label><input id="phx-sigma" type="number" value="25" min="0.01" max="200" step="any" required></div>
          <div id="phx-sigma-mkt-wrap" hidden><label id="phx-sigma-mkt-label">σ marché</label><input id="phx-sigma-mkt-display" type="text" disabled></div>
          <div><label for="phx-r">Taux r (%)</label><input id="phx-r" type="number" value="3" min="-50" max="50" step="any" required></div>
          <div><label for="phx-q">Dividende q (%)</label><input id="phx-q" type="number" value="2" min="0" max="50" step="any" required></div>
        </div>

        <h2>Durée</h2>
        <div class="fields">
          <div><label for="phx-nominal">Montant investi</label><input id="phx-nominal" type="number" value="1000" min="1" step="any" required></div>
          <div><label for="phx-freq">Observations</label>
            <select id="phx-freq">
              <option value="1">Annuelles</option>
              <option value="2" selected>Semestrielles</option>
              <option value="4">Trimestrielles</option>
              <option value="12">Mensuelles</option>
            </select>
          </div>
          <div class="full"><label for="phx-months">Maturité (mois)</label>
            <input id="phx-months" type="number" value="36" min="6" max="360" step="6" required>
            <p class="hint" id="phx-dates-hint"></p>
          </div>
        </div>

        <h2>Coupons</h2>
        <div class="fields">
          <div class="full"><label for="phx-coupon">Coupon par période (%)</label><input id="phx-coupon" type="number" value="4" min="0" max="100" step="any" required></div>
          <label class="check full"><input id="phx-stepup-on" type="checkbox"> Coupon step-up : il augmente à chaque période</label>
          <div class="full" id="phx-stepup-wrap" hidden><label for="phx-stepup">Hausse par période (%)</label><input id="phx-stepup" type="number" value="0.5" min="0.01" max="10" step="any"></div>
          <label class="check full"><input id="phx-memory" type="checkbox"> Effet mémoire : un coupon manqué est rattrapé plus tard</label>
        </div>

        <h2>Barrières</h2>
        <p class="hint" style="margin:0 0 10px">En % du niveau du sous-jacent au lancement.</p>
        <div class="fields">
          <label class="check full"><input id="phx-autocall" type="checkbox" checked> Remboursement anticipé possible (autocall)</label>
          <div class="full"><label for="phx-kauto">Remboursement anticipé (%)</label>
            <input id="phx-kauto" type="number" value="100" min="1" max="300" step="any" required>
            <p class="hint" id="phx-kauto-hint"></p></div>
          <div class="full"><label for="phx-bcoupon">Coupon versé (%)</label>
            <input id="phx-bcoupon" type="number" value="70" min="1" max="300" step="any" required>
            <p class="hint" id="phx-bcoupon-hint"></p></div>
          <div class="full"><label for="phx-bpdi">Capital protégé (%)</label>
            <input id="phx-bpdi" type="number" value="60" min="1" max="300" step="any" required>
            <p class="hint" id="phx-bpdi-hint"></p></div>
        </div>

        <details style="margin-top:14px">
          <summary>Bonus (facultatif)</summary>
          <div class="fields" style="margin-top:12px">
            <div><label for="phx-bonus-threshold">Seuil du bonus (%)</label><input id="phx-bonus-threshold" type="number" min="1" max="300" step="any" placeholder="aucun"></div>
            <div><label for="phx-bonus-amount">Bonus (% investi)</label><input id="phx-bonus-amount" type="number" value="0" min="0" max="100" step="any"></div>
          </div>
        </details>

        <div class="fields" style="margin-top:16px">
          <div class="full"><label for="phx-nsims">Nombre de simulations Monte Carlo</label><input id="phx-nsims" type="number" value="50000" min="1000" max="500000" step="1000" required>
            <p class="hint">Plus il y en a, plus le prix est précis, mais plus le calcul est long.</p></div>
        </div>

        <div class="fields">
          <div class="full"><label for="phx-step-down">Step-down du rappel par constat (points de % du niveau de référence)</label><input id="phx-step-down" type="number" value="0" min="0" step="0.1">
            <p class="hint">0 : désactivé. La barrière de rappel baisse de ce nombre de points à chaque constat, dès le deuxième. Ignoré sans rappel.</p></div>
        </div>
        <button class="primary" type="submit">Calculer</button>
        <p id="phx-status" class="status" role="status" aria-live="polite"></p>
      </form>
<form id="form-autocall_plain" data-product="autocall_plain" hidden>
      <h2>Sous-jacent</h2>
      <div class="fields">
        <div class="full" style="position:relative"><label for="ac-plain-ticker">Chercher un ticker (facultatif)</label>
          <input id="ac-plain-ticker" autocomplete="off" placeholder="ex : AAPL, MC.PA…">
          <div id="ac-plain-suggestions" class="card" style="position:absolute;z-index:10;width:100%;max-height:180px;overflow:auto" hidden></div>
          <p id="ac-plain-market-status" class="hint" role="status">Sans ticker, le sous-jacent part de 100.</p>
        </div>
        <input id="ac-plain-s0" type="hidden" value="100">
        <div><label for="ac-plain-sigma-source">Volatilité σ</label>
          <select id="ac-plain-sigma-source"><option value="manual">Manuelle</option><option value="hist">Historique (1 an)</option><option value="vix">VIX (S&amp;P 500)</option></select>
        </div>
        <div id="ac-plain-sigma-manual-wrap"><label for="ac-plain-sigma">σ (%)</label><input id="ac-plain-sigma" type="number" value="25" min="0.01" max="200" step="any" required></div>
        <div id="ac-plain-sigma-mkt-wrap" hidden><label id="ac-plain-sigma-mkt-label">σ marché</label><input id="ac-plain-sigma-mkt-display" type="text" disabled></div>
        <div><label for="ac-plain-r">Taux r (%)</label><input id="ac-plain-r" type="number" value="3" min="-50" max="50" step="any" required></div>
        <div><label for="ac-plain-q">Dividende q (%)</label><input id="ac-plain-q" type="number" value="2" min="0" max="50" step="any" required></div>
      </div>
      <h2>Durée et nominal</h2>
      <div class="fields">
        <div><label for="ac-plain-nominal">Montant investi</label><input id="ac-plain-nominal" type="number" value="1000" min="0.01" max="1000000000000.0" step="any" required></div>
        <div><label for="ac-plain-freq">Observations</label>
          <select id="ac-plain-freq">
            <option value="1">Annuelles</option>
            <option value="2" selected>Semestrielles</option>
            <option value="4">Trimestrielles</option>
            <option value="12">Mensuelles</option>
          </select>
        </div>
        <div class="full"><label for="ac-plain-months">Maturité (mois)</label><input id="ac-plain-months" type="number" value="36" min="1" max="360" step="1" required></div>
        <div class="full"><label for="ac-plain-first">Premier rappel autorisé à partir de (mois)</label><input id="ac-plain-first" type="number" value="6" min="0" max="360" step="1" required></div>
      </div>
      <label class="check"><input id="ac-plain-autocall" type="checkbox" checked> Remboursement anticipé possible (autocall)</label>
      <h2>Coupons et barrières</h2>
      <p id="ac-plain-rules" class="hint" style="margin-bottom:12px">Coupons accumulés payés au rappel ; à maturité, tous les coupons uniquement si le seuil final est atteint. Les barrières sont exprimées en % du spot initial.</p>
      <div class="fields">
        <div class="full"><label for="ac-plain-coupon">Coupon par observation (%)</label><input id="ac-plain-coupon" type="number" value="4" min="0" max="100" step="any" required></div>
        <div class="full"><label for="ac-plain-barrier">Rappel et coupon final (%)</label><input id="ac-plain-barrier" type="number" value="100" min="0.01" max="300" step="any" required></div>
        <label class="check full"><input id="ac-plain-protection" type="checkbox" checked> Protection conditionnelle à maturité</label>
        <div class="full"><label for="ac-plain-ki">Barrière de protection (%)</label><input id="ac-plain-ki" type="number" value="60" min="0.01" max="100" step="any" required></div>
      </div>
      <p class="hint">Sous la protection à maturité : remboursement du capital = nominal × niveau final / spot initial. Sans cette protection, le modèle rembourse le nominal.</p>
      <h2 style="margin-top:16px">Simulation</h2>
      <div class="fields">
        <div class="full"><label for="ac-plain-nsims">Nombre de simulations</label><input id="ac-plain-nsims" type="number" value="50000" min="1000" max="500000" step="1000" required></div>
      </div>
      <div class="fields">
        <div class="full"><label for="ac-plain-step-down">Step-down du rappel par constat (points de % du niveau de référence)</label><input id="ac-plain-step-down" type="number" value="0" min="0" step="0.1">
          <p class="hint">0 : désactivé. La barrière de rappel baisse de ce nombre de points à chaque constat, dès le deuxième. Ignoré sans rappel. Le seuil du coupon final ne change pas.</p></div>
      </div>
      <button class="primary" type="submit">Calculer</button>
      <p id="ac-plain-status" class="status" role="status" aria-live="polite"></p>
    </form>

    </div>

    <div class="results" id="phx-results">
      <div class="empty">Choisis un produit pour afficher ses réglages.</div>
    </div>
  </section>
```

**Principe : un sélecteur, un formulaire par produit.** En haut, `struct-product` liste les produits. La première option, `selected disabled`, oblige à faire un choix (« Choisir un produit »). Chaque produit a son **propre** `<form data-product="...">`, caché au départ ; le JavaScript affiche celui dont `data-product` correspond au choix. Ajouter un produit = une `<option>` + un formulaire. Tous les produits partagent la même colonne de résultats (`phx-results`).

**Formulaire Phoenix** (`form-phoenix`)
- **Sous-jacent** : la recherche de ticker est **facultative**. Sans ticker, le sous-jacent part de 100 et tout se lit en % ; avec un ticker, on part du vrai spot (le spot n'est donc pas un champ). Puis la volatilité (trois sources), le taux et le dividende ; `min`/`max` bornent les saisies (σ ≤ 200 %).
- **Durée** : le montant investi, la fréquence d'observation (`selected` sur semestrielle), la maturité **en mois** avec `step="6"`. `phx-dates-hint` affiche le nombre de dates. Les dates d'observation ne sont jamais saisies à la main : elles se déduisent de la maturité et de la fréquence.
- **Coupons** : le coupon par période ; la case *step-up* (coupon qui augmente à chaque période) affiche le champ de hausse ; la case *effet mémoire* (un coupon manqué est rattrapé à la date suivante où la barrière coupon est atteinte).
- **Barrières**, en % du niveau de départ : la case autocall (cochée par défaut), puis rappel, coupon et protection du capital. Sous chaque barrière, une phrase d'aide (`...-hint`) traduit le chiffre en langage clair.
- **Bonus** (dans un `<details>` replié : option rarement utilisée) : un seuil et un montant ; `placeholder="aucun"` indique qu'un seuil vide signifie pas de bonus.
- **Simulations** : de 1 000 à 500 000, par pas de 1 000, avec le rappel du compromis précision / temps.
- **Step-down** : la barrière de rappel baisse de ce nombre de points à chaque constat, à partir du deuxième ; `0` le désactive.

**Formulaire Athéna** (`form-autocall_plain`)
- Même logique de sous-jacent facultatif. Ici le spot est un champ **caché** (`type="hidden"`, valeur 100) que la recherche de ticker remplit.
- **Durée et nominal** : montant, fréquence, maturité en mois, et le **premier rappel autorisé** (souvent, un Athéna ne peut pas être rappelé la première année).
- La case autocall est hors de la grille : si elle est décochée, le JavaScript masque le premier rappel et renomme la barrière.
- **Coupons et barrières** : `ac-plain-rules` résume la règle de l'Athéna (coupons **accumulés**, payés au rappel ou à maturité si le seuil final est atteint) ; le JavaScript change ce texte selon que le rappel est actif ou non. Un seul champ pour la barrière de rappel et le seuil du coupon final (`ac-plain-barrier`) : c'est la définition d'un Athéna classique. La protection conditionnelle (case + barrière) : sous la barrière à maturité, le remboursement suit la baisse du sous-jacent.
- **Simulation** et **step-down** comme pour le Phoenix ; l'aide précise que le seuil du coupon final, lui, ne baisse pas.

**Colonne de résultats** : `phx-results` est partagée par tous les produits de l'onglet ; son message vide invite d'abord à choisir un produit.

### 22. Onglet Chantier (HTML)

```html
  <!-- ===================== ONGLET CHANTIER ===================== -->
<section id="panel-chantier" class="grid" hidden>
  <div class="card">
    <form id="vol-form" style="padding-top:14px">
      <h2>Laboratoire quantitatif</h2>
      <div class="fields">
        <div class="full">
          <label for="chantier-module">Sélectionner un module</label>
          <select id="chantier-module">
            <option value="volatility">Volatilité</option>
            <option value="rates" disabled>Modèles de taux — à venir</option>
          </select>
        </div>
        <div class="full" style="position:relative">
          <label for="vol-ticker">Chercher un ticker</label>
          <input id="vol-ticker" required autocomplete="off" placeholder="ex : AAPL, MSFT, MC.PA…" aria-controls="vol-suggestions">
          <div id="vol-suggestions" class="card" style="position:absolute;z-index:10;width:100%;max-height:180px;overflow-y:auto" hidden></div>
          <p id="vol-search-status" class="hint" role="status"></p>
        </div>
        <div class="full">
          <label for="vol-period">Période historique</label>
          <select id="vol-period">
            <option value="6mo">6 mois</option><option value="1y" selected>1 an</option>
            <option value="2y">2 ans</option><option value="5y">5 ans</option>
          </select>
        </div>
        <div class="full">
          <label for="vol-lambda">Mémoire EWMA · λ</label>
          <input id="vol-lambda" type="number" min="0.01" max="0.99" step="0.01" value="0.94" required>
          <p class="hint">Plus λ est élevé, plus la mémoire est longue.</p>
        </div>
      </div>
      <button id="vol-calculate" class="primary" type="submit">Calculer</button>
      <p id="vol-status" class="status" role="status" aria-live="polite"></p>
      <p class="hint">Volatilités historiques annualisées · fenêtres de 20 et 60 séances · EWMA · Parkinson.</p>
      <details style="margin-top:14px">
        <summary>Comprendre les mesures</summary>
        <p class="hint">Historique : dispersion des rendements entre clôtures. Les fenêtres 20 et 60 donnent deux horizons de lecture.</p>
        <p class="hint">EWMA : les chocs récents pèsent davantage. Avec λ = 0,94, chaque mise à jour conserve 94 % de la variance précédente et ajoute 6 % du rendement au carré.</p>
        <p class="hint">Parkinson : amplitude entre le plus haut et le plus bas de chaque séance. L'indicateur couvre la période choisie ; la courbe couvre les 20 dernières séances de chaque date. Les gaps de nuit sont mal capturés.</p>
        <p class="hint">Annualisation : 252 séances/an. EWMA suppose une moyenne nulle et démarre au carré du premier rendement. Changer la période peut donc modifier son initialisation.</p>
      </details>
    </form>
  </div>
  <div class="results" id="chantier-results" aria-busy="false">
    <div class="empty">Saisissez un ticker puis lancez le calcul.</div>
  </div>
</section>

</main>

<script>
```

- « Chantier » = **laboratoire** : des outils d'analyse qui ne sont pas des produits. Le sélecteur `chantier-module` prévoit d'autres modules ; l'option « Modèles de taux — à venir » est `disabled` : elle montre la direction prise sans être cliquable.
- **Recherche de ticker** : ici le ticker est **obligatoire** (`required`) ; `aria-controls` relie le champ à sa liste de suggestions pour les lecteurs d'écran.
- **Période historique** : 6 mois, 1 an (par défaut), 2 ans, 5 ans. Les `value` (`6mo`, `1y`…) sont celles qu'attend yfinance.
- **λ de l'EWMA** : entre 0,01 et 0,99 ; 0,94 est la valeur de RiskMetrics (J.P. Morgan, 1994).
- `<details>` « Comprendre les mesures » : une explication courte de chaque mesure (historique, EWMA, Parkinson) et de leurs conventions, directement dans la page.
- `aria-busy` sur la colonne de résultats : indique aux lecteurs d'écran qu'un calcul est en cours.
- `</main>` ferme la zone principale, puis `<script>` ouvre la partie JavaScript.

## Partie 4 — le JavaScript (comportement)

### 23. Le raccourci `$`

```js
const $ = id => document.getElementById(id);
```

- `const $ = id => document.getElementById(id);` : une **fonction fléchée** (`argument => résultat`). `$('opt-s0')` remplace `document.getElementById('opt-s0')`, écrit des centaines de fois dans le fichier. Ce n'est pas jQuery : juste un raccourci d'une ligne.

### 24. Formats de nombres

```js
// -------- Formats de nombres (un seul endroit) --------
const FORMAT_2 = new Intl.NumberFormat('fr-FR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const FORMAT_4 = new Intl.NumberFormat('fr-FR', {minimumFractionDigits: 2, maximumFractionDigits: 4});
const fmt = x => FORMAT_4.format(x);                                 // valeurs : 2 à 4 décimales
const fmt2 = x => x == null ? '—' : FORMAT_2.format(x);              // indicateurs : 2 décimales
const fmtPct = x => x == null ? '—' : FORMAT_2.format(x) + ' %';     // pourcentages
```

- `Intl.NumberFormat('fr-FR', ...)` : le formateur de nombres intégré au navigateur, à la française (virgule décimale, espace pour les milliers : « 1 234,56 »).
- Les deux formateurs sont créés **une seule fois** (créer un `Intl.NumberFormat` coûte cher ; l'appeler ne coûte rien).
- `fmt` : 2 à 4 décimales, pour les prix et les grecques (un delta de 0,5432 garde ses 4 décimales, un prix de 10,45 n'en affiche que 2).
- `fmt2` : exactement 2 décimales, pour les indicateurs des produits structurés.
- `fmtPct` : ajoute « % ». `x == null ? '—' : ...` : une valeur absente (`null` ou `undefined`, par exemple un VIX indisponible) s'affiche « — » au lieu de « NaN % ».
- **Pourquoi « un seul endroit » ?** Avant, chaque onglet formatait ses nombres à sa façon ; les mêmes valeurs apparaissaient avec un nombre de décimales différent selon l'onglet.

### 25. Navigation : la table des onglets

```js
// -------- Navigation entre onglets --------
// Chaque onglet a un code de fonction affiché dans la barre de commande.
const FONCTIONS = {
  options:    ['OPT',   'Options vanilles'],
  forward:    ['FWD',   'Contrats à terme'],
  strategies: ['STRAT', 'Stratégies optionnelles'],
  structured: ['STRC',  'Produits structurés'],
  chantier:   ['LAB',   'Laboratoire quantitatif'],
};
```

- `FONCTIONS` associe à chaque onglet un **code de fonction** et une description, affichés dans la barre du haut (comme les codes des terminaux de marché : on tape `OPT <GO>`).
- **L'ordre des clés compte** : c'est l'ordre du menu, et donc celui des raccourcis clavier (1 = premier onglet). Ajouter un onglet = une ligne ici, un bouton et un panneau dans le HTML.

### 26. `ouvrirOnglet()` et le clavier

```js
function ouvrirOnglet(nom) {
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === nom));
  Object.keys(FONCTIONS).forEach(n => { $('panel-' + n).hidden = (n !== nom); });
  $('cmd-code').textContent = FONCTIONS[nom][0];
  $('cmd-desc').textContent = FONCTIONS[nom][1];
}
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => ouvrirOnglet(btn.dataset.tab));
});
// Raccourcis clavier : un chiffre par onglet, dans l’ordre du menu, sauf pendant une saisie.
document.addEventListener('keydown', e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
  const nom = Object.keys(FONCTIONS)[Number(e.key) - 1];
  if (nom) ouvrirOnglet(nom);
});
```

- `document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === nom))` : chaque bouton reçoit la classe `active` si c'est le bon, la perd sinon (`toggle(classe, condition)`).
- `Object.keys(FONCTIONS).forEach(n => { $('panel-' + n).hidden = (n !== nom); })` : on masque tous les panneaux sauf celui demandé. Grâce à la convention `panel-<nom>`, aucune liste de panneaux à maintenir.
- Les deux lignes suivantes mettent à jour le code et la description dans la barre du haut.
- Un écouteur `click` par bouton appelle `ouvrirOnglet(btn.dataset.tab)`.
- **Raccourcis clavier** : un écouteur `keydown` sur toute la page.
  - Si Cmd, Ctrl ou Alt est enfoncée, on ne fait rien (on ne casse pas Ctrl+1 du navigateur).
  - Si le curseur est dans un champ, on ne fait rien : taper « 2 » dans le champ du spot ne doit pas changer d'onglet.
  - `Object.keys(FONCTIONS)[Number(e.key) - 1]` : la touche « 1 » donne l'indice 0, donc le premier onglet. Pour une autre touche, l'indice n'existe pas, `nom` vaut `undefined` et rien ne se passe.

### 27. L'horloge

```js
// Horloge de Paris dans la barre du haut.
function majHorloge() {
  const maintenant = new Date();
  $('clock-time').textContent = maintenant.toLocaleTimeString('fr-FR', {timeZone: 'Europe/Paris'});
  $('clock-date').textContent = maintenant.toLocaleDateString('fr-FR', {timeZone: 'Europe/Paris', day: '2-digit', month: '2-digit', year: 'numeric'});
}
majHorloge();
setInterval(majHorloge, 1000);
```

- `toLocaleTimeString('fr-FR', {timeZone: 'Europe/Paris'})` : l'heure **de Paris**, quel que soit le fuseau de l'ordinateur (utile si la page est ouverte depuis l'étranger).
- `majHorloge()` est appelée une première fois tout de suite (sinon l'horloge resterait vide pendant une seconde), puis `setInterval(majHorloge, 1000)` la rappelle chaque seconde.

### 28. `appelApi()` — le seul point d'entrée vers le serveur

```js
// -------- Appels au serveur (un seul point d'entrée) --------
// JSON en entrée et en sortie, message d'erreur du serveur, délai maximal.
// controleur : AbortController fourni par l'appelant pour annuler une requête devenue inutile.
async function appelApi(url, {payload, timeout = 300000, controleur = new AbortController()} = {}) {
  let delaiDepasse = false;
  const minuteur = setTimeout(() => { delaiDepasse = true; controleur.abort(); }, timeout);
  try {
    const options = {signal: controleur.signal};
    if (payload !== undefined) {
      Object.assign(options, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    }
    const res = await fetch(url, options);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Erreur inconnue.');
    return data;
  } catch (err) {
    if (delaiDepasse) throw new Error('Délai dépassé : réduisez le calcul (simulations, période) et réessayez.');
    throw err;
  } finally {
    clearTimeout(minuteur);
  }
}
```

**Pourquoi une seule fonction ?** Chaque onglet faisait ses propres `fetch`, avec des oublis différents : pas de délai maximal ici, pas de lecture du message d'erreur là. Tout est maintenant au même endroit.

- **Signature** : `appelApi(url, {payload, timeout = 300000, controleur = new AbortController()} = {})`. Les accolades sont une **déstructuration** : on passe un objet d'options nommées, chacune avec sa valeur par défaut. Le `= {}` final permet d'appeler `appelApi(url)` sans options.
- `async` : la fonction renvoie une promesse ; `await` attend la réponse sans bloquer la page.
- **Délai maximal** : `setTimeout(() => { delaiDepasse = true; controleur.abort(); }, timeout)`. Au bout de 5 minutes par défaut (300 000 ms), la requête est annulée. Le drapeau `delaiDepasse` permet ensuite de distinguer « annulée parce que trop longue » de « annulée par l'appelant ».
- **`AbortController`** : l'objet standard pour annuler un `fetch`. L'appelant peut fournir le sien (la recherche de ticker annule ainsi une recherche devenue inutile).
- `if (payload !== undefined)` : avec des données, c'est un **POST** JSON (`Content-Type: application/json`, `JSON.stringify`) ; sans données, un simple GET.
- `const data = await res.json(); if (!res.ok) throw new Error(data.error || 'Erreur inconnue.');` : le serveur renvoie toujours du JSON, même en erreur (`{"error": "..."}`) ; on transforme une réponse 400/500 en exception portant **le message du serveur**, que `surSoumission` affichera en rouge.
- `catch` : en cas de délai dépassé, un message qui dit quoi faire (« réduisez le calcul ») ; sinon, l'erreur d'origine est relancée.
- `finally { clearTimeout(minuteur); }` : on arrête le minuteur dans **tous** les cas (succès ou erreur) ; sinon il annulerait plus tard un contrôleur déjà inutile.

### 29. `surSoumission()` — le comportement commun des formulaires

```js
// -------- Comportement commun à tous les formulaires --------
// Bouton bloqué pendant le calcul, message d'attente, erreur en rouge.
// calcul() renvoie le message de succès (ou rien si le résultat est devenu inutile).
function surSoumission(form, status, calcul, {avant, attente = 'Calcul en cours...'} = {}) {
  const bouton = form.querySelector('button[type=submit]');
  form.addEventListener('submit', async e => {
    e.preventDefault();
    if (avant) avant();
    if (bouton.disabled || !form.reportValidity()) return;
    bouton.disabled = true;
    status.className = 'status';
    status.textContent = attente;
    try {
      status.textContent = await calcul() || '';
    } catch (err) {
      status.className = 'status error';
      status.textContent = err.message;
    } finally {
      bouton.disabled = false;
    }
  });
}
```

Tous les boutons « Calculer » se comportent pareil : bouton bloqué pendant le calcul, message d'attente, résultat ou erreur. Cette fonction l'écrit une fois.

- **Paramètres** : le formulaire, la zone de message, la fonction `calcul` (qui fait le travail et renvoie le message de succès) et des options (`attente` : le message pendant le calcul, `avant` : une vérification à lancer juste avant la validation).
- `form.addEventListener('submit', async e => { e.preventDefault(); ...` : par défaut, un formulaire HTML recharge la page en envoyant ses champs ; `preventDefault()` l'en empêche, on gère l'envoi nous-mêmes.
- `if (avant) avant();` : par exemple, revérifier l'ordre des barrières du Phoenix **juste avant** l'envoi, pour que la validation du navigateur voie l'état à jour.
- `if (bouton.disabled || !form.reportValidity()) return;` : 1) si un calcul est déjà en cours, on ignore le double clic ; 2) `reportValidity()` vérifie tous les champs (`required`, `min`, `max`, messages personnalisés) et affiche la bulle d'erreur native du navigateur sur le premier champ invalide.
- `bouton.disabled = true;` puis message d'attente en vert.
- `status.textContent = await calcul() || '';` : on attend le calcul et on affiche son message (`|| ''` : si `calcul` ne renvoie rien, par exemple parce que le résultat est devenu inutile, la zone se vide).
- `catch` : message d'erreur en rouge (classe `error`).
- `finally { bouton.disabled = false; }` : le bouton est **toujours** réactivé, même après une erreur. Oublier ce `finally` est un bug classique : un bouton bloqué pour toujours après la première erreur.

### 30. Compteur de graphes

```js
// -------- Petit moteur de tracé SVG générique (payoff/pnl vs ST) --------
let chartId = 0;   // identifiant unique par graphe (pour les zones de découpe SVG)
```

- `let chartId = 0;` : chaque graphe reçoit un numéro unique. Les zones de découpe SVG (`clipPath`) ont un `id`, et deux graphes affichés en même temps ne doivent pas avoir le même : sinon le second utiliserait la découpe du premier.

### 31. `renderChart()` — le graphique payoff / P&L

```js
function renderChart(ST_grid, series, breakevens, opts = {}) {
  const W=760, H=340, L=60, R=16, top=34, bottom=44;
  const id = ++chartId;
  const xmin = ST_grid[0], xmax = ST_grid[ST_grid.length-1];
  const allValues = series.flatMap(s => s.values);
  const pad = Math.max((Math.max(...allValues) - Math.min(...allValues)) * .12, 1);
  const ymin = Math.min(0, ...allValues) - pad, ymax = Math.max(0, ...allValues) + pad;

  const X = x => L + (x-xmin)/(xmax-xmin) * (W-L-R);
  const Y = y => top + (ymax-y)/(ymax-ymin) * (H-top-bottom);
  const nb = v => new Intl.NumberFormat('fr-FR', {maximumFractionDigits: 2}).format(v);

  const colors = {payoff:'#5cc8ff', pnl:'#ffa028'};
  const dash = {payoff:'6 5', pnl:'0'};
  const labels = Object.assign({payoff:'Payoff brut', pnl:'P&L net (après prime)'}, opts.labels || {});

  let content = `<rect x="0" y="0" width="${W}" height="${H}" fill="#000"/>`;
  for (let i=0;i<=4;i++){
    const y = ymin + (ymax-ymin)*i/4;
    content += `<line x1="${L}" x2="${W-R}" y1="${Y(y)}" y2="${Y(y)}" stroke="#1a1f27"/>`;
    content += `<text x="${L-8}" y="${Y(y)+4}" text-anchor="end">${nb(y)}</text>`;
  }
  for (let i=0;i<=5;i++){
    const x = xmin + (xmax-xmin)*i/5;
    content += `<line x1="${X(x)}" x2="${X(x)}" y1="${top}" y2="${H-bottom}" stroke="#12161c"/>`;
    content += `<text x="${X(x)}" y="${H-bottom+20}" text-anchor="middle">${nb(x)}</text>`;
  }
  content += `<text x="${(W+L-R)/2}" y="${H-6}" text-anchor="middle">${opts.xLabel || 'Prix du sous-jacent à maturité'}</text>`;

  // Zones de gain (vert) et de perte (rouge) sous la courbe de P&L
  const zero = Y(0);
  content += `<defs>
    <clipPath id="haut${id}"><rect x="${L}" y="${top}" width="${W-L-R}" height="${zero-top}"/></clipPath>
    <clipPath id="bas${id}"><rect x="${L}" y="${zero}" width="${W-L-R}" height="${H-bottom-zero}"/></clipPath>
  </defs>`;
  const pnlSerie = series.find(s => s.key === 'pnl');
  if (pnlSerie) {
    const pts = ST_grid.map((x,i) => `L${X(x).toFixed(2)},${Y(pnlSerie.values[i]).toFixed(2)}`).join(' ');
    const aire = `M${X(xmin)},${zero} ${pts} L${X(xmax)},${zero} Z`;
    content += `<path d="${aire}" fill="#3ddc84" fill-opacity=".14" clip-path="url(#haut${id})"/>`;
    content += `<path d="${aire}" fill="#ff5c5c" fill-opacity=".14" clip-path="url(#bas${id})"/>`;
  }
  content += `<line x1="${L}" x2="${W-R}" y1="${zero}" y2="${zero}" stroke="#5b616b"/>`;

  // Lignes verticales optionnelles (niveaux à repérer, comme des barrières)
  (opts.markers || []).forEach((m, i) => {
    if (m.x < xmin || m.x > xmax) return;
    content += `<line x1="${X(m.x)}" x2="${X(m.x)}" y1="${top}" y2="${H-bottom}" stroke="${m.color}" stroke-dasharray="2 4"/>`;
    content += `<text x="${X(m.x)+5}" y="${top + 14 + i*14}" text-anchor="start" style="fill:${m.color};paint-order:stroke;stroke:#000;stroke-width:4px">${m.label}</text>`;
  });

  series.forEach(s => {
    const path = ST_grid.map((x,i) => (i?'L':'M') + X(x).toFixed(2) + ',' + Y(s.values[i]).toFixed(2)).join(' ');
    content += `<path d="${path}" fill="none" stroke="${colors[s.key]||'#ffa028'}" stroke-width="${s.key==='pnl'?2.2:1.6}" stroke-dasharray="${dash[s.key]||'0'}" stroke-linejoin="round"/>`;
  });

  (breakevens||[]).forEach(be => {
    content += `<line x1="${X(be)}" x2="${X(be)}" y1="${top}" y2="${H-bottom}" stroke="#f5d547" stroke-dasharray="3 4"/>`;
    content += `<circle cx="${X(be)}" cy="${zero}" r="4" fill="#000" stroke="#f5d547" stroke-width="1.6"/>`;
    content += `<text x="${X(be)+6}" y="${zero-8}" text-anchor="start" style="fill:#f5d547;paint-order:stroke;stroke:#000;stroke-width:4px">${nb(be)}</text>`;
  });

  // Légende
  let legendX = L;
  const legendY = top - 14;
  series.forEach(s => {
    const label = labels[s.key] || s.key;
    content += `<line x1="${legendX}" x2="${legendX+18}" y1="${legendY}" y2="${legendY}" stroke="${colors[s.key]||'#ffa028'}" stroke-width="2" stroke-dasharray="${dash[s.key]||'0'}"/>`;
    content += `<text x="${legendX+24}" y="${legendY+4}" text-anchor="start" style="fill:#c9ccd1">${label}</text>`;
    legendX += 24 + label.length * 6.7 + 22;
  });
  if ((breakevens||[]).length) {
    content += `<circle cx="${legendX+5}" cy="${legendY}" r="4" fill="#000" stroke="#f5d547" stroke-width="1.6"/>`;
    content += `<text x="${legendX+15}" y="${legendY+4}" text-anchor="start" style="fill:#c9ccd1">Breakeven</text>`;
  }

  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Payoff et P&amp;L à maturité">${content}</svg>`;
}
```

**Ce qu'il fait :** dessine une ou plusieurs courbes en fonction du prix du sous-jacent à maturité et renvoie le SVG sous forme de **texte**, inséré ensuite dans la page.

**Pourquoi à la main ?** Une bibliothèque de graphiques (Chart.js, Plotly) pèse plusieurs centaines de Ko et cache ce qu'elle fait. Ici, 80 lignes suffisent : un repère, des courbes, des zones colorées, une légende.

**Paramètres** : `ST_grid` (les abscisses, calculées par le serveur), `series` (une liste `{key, values}` : `payoff` et/ou `pnl`), `breakevens` (points morts) et `opts` (libellés, titre de l'axe horizontal, lignes verticales de barrières).

**Le repère**
- `W, H` : taille logique du dessin (760 × 340) ; `L, R, top, bottom` : marges pour les graduations. Grâce au `viewBox` final, le dessin s'étire ensuite à la largeur réelle de la carte.
- `allValues = series.flatMap(s => s.values)` : toutes les ordonnées de toutes les courbes, pour fixer l'échelle verticale.
- `pad` : 12 % de marge au-dessus et au-dessous (au moins 1, pour une courbe plate).
- `Math.min(0, ...allValues)` et `Math.max(0, ...)` : **le zéro est toujours visible**, puisque c'est la ligne qui sépare gain et perte.
- `X = x => ...` et `Y = y => ...` : les deux fonctions de **changement d'échelle**, des unités financières vers les pixels. `Y` est inversée (`ymax - y`) car en SVG l'axe vertical descend.
- `colors`, `dash`, `labels` : le payoff en bleu pointillé, le P&L en ambre plein.
- `Object.assign({...}, opts.labels || {})` part des libellés par défaut et remplace ceux que l'appelant fournit (les produits structurés parlent de « Remboursement à maturité »).

**Le fond**
- 5 lignes horizontales et 6 verticales avec leurs graduations (formatées à la française par `nb`).
- Le titre de l'axe horizontal (`opts.xLabel` s'il est fourni, sinon « Prix du sous-jacent à maturité »).

**Zones de gain et de perte**
- Deux `clipPath` découpent le dessin en deux rectangles : au-dessus de zéro et au-dessous.
- On construit **une seule** aire (de la courbe de P&L jusqu'à l'axe zéro) et on la dessine **deux fois** : en vert découpée par le rectangle du haut, en rouge par celui du bas. Résultat : vert là où l'on gagne, rouge là où l'on perd, sans calculer les points où la courbe croise zéro.
- La ligne horizontale du zéro, en gris.

**Lignes verticales optionnelles** (`opts.markers`) : pour les produits structurés, une ligne pointillée par barrière (rappel, coupon, protection), avec son libellé. On ignore une barrière hors de l'écran ; les libellés sont décalés vers le bas (`i*14`) pour ne pas se chevaucher. `paint-order:stroke` dessine un contour noir **sous** le texte : il reste lisible même posé sur une courbe.

**Les courbes** : pour chaque série, un chemin SVG `M x,y L x,y L x,y…` (M = « aller à », L = « tracer jusqu'à ») ; `toFixed(2)` arrondit les coordonnées pour alléger le texte. Le P&L est tracé un peu plus épais.

**Les breakevens** : une ligne verticale jaune, un rond sur l'axe zéro et la valeur écrite à côté.

**La légende** : un trait et un libellé par série ; la position du suivant est estimée à partir du nombre de lettres (`label.length * 6.7`), une approximation suffisante en police à chasse fixe. Le symbole « Breakeven » n'apparaît que s'il y en a.

**Le retour** : `<svg viewBox="0 0 760 340" role="img" aria-label="...">` ; `role="img"` et `aria-label` décrivent le graphique aux lecteurs d'écran.

### 32. `greeksTable()` — tableau de grecques

```js
function greeksTable(dict, order) {
  const keys = order || Object.keys(dict);
  const rows = keys.filter(k => k in dict).map(k => `<tr><td>${k}</td><td>${fmt(dict[k])}</td></tr>`).join('');
  return `<table class="greeks-table"><thead><tr><th>Grecque</th><th>Valeur</th></tr></thead><tbody>${rows}</tbody></table>`;
}
```

- `order` : l'ordre d'affichage voulu (Delta, Gamma, Vega, Theta, Rho) ; sans ordre, celui de l'objet.
- `keys.filter(k => k in dict)` : on saute une grecque absente de la réponse au lieu d'afficher « undefined ».
- `.map(...)` construit une ligne `<tr>` par grecque, `.join('')` colle les lignes, et le tout est inséré dans un `<table class="greeks-table">`.
- Les valeurs viennent du serveur et sont des nombres formatés : aucun texte saisi par l'utilisateur n'est injecté ici.

### 33. `brancherRechercheTicker()` — l'autocomplétion des tickers

```js
// -------- Recherche de ticker commune à tous les formulaires --------
// Temporisation de 350 ms, annulation de la requête précédente, compteur de version
// (une réponse lente pour « AA » n'écrase pas celle de « AAPL ») et aucun HTML injecté.
// Renvoie une fonction qui ferme la liste et annule la recherche en cours.
function brancherRechercheTicker({inputId, resultsId, statusId, onSelect, saisieLibre = false}) {
  const input = $(inputId), boite = $(resultsId), status = $(statusId);
  let version = 0, minuteur, controleur;
  const fermer = () => { ++version; clearTimeout(minuteur); controleur?.abort(); boite.hidden = true; };

  input.addEventListener('input', () => {
    fermer();
    const maVersion = version, query = input.value.trim();
    boite.replaceChildren();
    if (!query) return;
    minuteur = setTimeout(async () => {
      controleur = new AbortController();
      status.textContent = 'Recherche…';
      try {
        const data = await appelApi('/api/search_ticker?q=' + encodeURIComponent(query), {controleur, timeout: 15000});
        if (maVersion !== version) return;
        const hits = (data.results || []).filter(hit => typeof hit.symbol === 'string');
        status.textContent = hits.length ? 'Sélectionnez un ticker.'
          : 'Aucun résultat.' + (saisieLibre ? ' Vous pouvez saisir un symbole directement.' : '');
        for (const hit of hits) {
          const ligne = document.createElement('button');
          ligne.type = 'button';
          ligne.className = 'ticker-hit';
          ligne.style.cssText = 'display:block;width:100%;text-align:left;color:var(--text);border:0;border-bottom:1px solid var(--line)';
          const symbole = document.createElement('strong');
          symbole.textContent = hit.symbol;
          const bourse = document.createElement('span');
          bourse.style.color = 'var(--muted)';
          bourse.textContent = hit.exchange || '';
          ligne.append(symbole, ` — ${hit.name || ''} `, bourse);
          ligne.addEventListener('click', () => {
            fermer();
            input.value = hit.symbol;
            status.textContent = hit.symbol;
            onSelect(hit.symbol, status);
          });
          boite.append(ligne);
        }
        boite.hidden = !boite.children.length;
      } catch (err) {
        if (maVersion === version && err.name !== 'AbortError') {
          status.textContent = 'Recherche indisponible.' + (saisieLibre ? ' Saisissez le symbole directement.' : '');
        }
      }
    }, 350);
  });
  input.addEventListener('keydown', e => { if (e.key === 'Escape') fermer(); });
  document.addEventListener('click', e => { if (e.target !== input && !boite.contains(e.target)) boite.hidden = true; });
  return fermer;
}
```

**Le besoin :** pendant la frappe, proposer les tickers correspondants (« AAP » → AAPL…) via `/api/search_ticker`, dans plusieurs onglets.

**Les problèmes rencontrés, et leurs solutions dans le code**
1. **Une requête par lettre tapée** : le serveur interroge Yahoo à chaque appel. → **Temporisation** (*debounce*) : on attend 350 ms sans nouvelle frappe avant d'envoyer (`setTimeout(..., 350)`, annulé à chaque nouvelle lettre par `clearTimeout`).
2. **Réponses dans le désordre** : la réponse lente pour « AA » arrivait après celle pour « AAPL » et l'écrasait. → **Compteur de version** : chaque frappe incrémente `version` ; une réponse dont `maVersion !== version` est ignorée. En plus, `controleur?.abort()` annule la requête précédente (`?.` : seulement s'il y en a une).
3. **Injection de HTML** : un nom de société contenant `<script>` ou `<img onerror=...>` aurait pu s'exécuter si on l'insérait avec `innerHTML`. → Les lignes sont construites avec `document.createElement` et `textContent`, qui insèrent du **texte**, jamais du HTML.

**Ligne par ligne**
- Les paramètres nommés : les `id` du champ, de la liste et du message, `onSelect` (que faire du symbole choisi) et `saisieLibre` (dans le Chantier, on peut taper un symbole directement si la recherche échoue).
- `fermer()` : invalide les réponses en cours (`++version`), annule la temporisation et la requête, cache la liste. Elle est aussi **renvoyée** à l'appelant.
- Sur `input` : on ferme tout, on mémorise `maVersion` et la saisie, on vide la liste (`replaceChildren()` sans argument). Saisie vide : on s'arrête.
- Dans la temporisation : nouvel `AbortController`, « Recherche… », appel avec un délai court (15 s : une recherche ne doit pas faire attendre).
- `filter(hit => typeof hit.symbol === 'string')` : on ne garde que des résultats valides (défense contre une réponse inattendue).
- Pour chaque résultat, un `<button type="button">` (`type="button"` : sinon un bouton dans un formulaire **soumet** le formulaire) qui contient le symbole en gras, le nom et la bourse.
- Au clic : on ferme la liste, on recopie le symbole dans le champ et on appelle `onSelect`.
- `boite.hidden = !boite.children.length` : la liste n'apparaît que si elle a du contenu.
- En cas d'erreur (sauf annulation volontaire, `AbortError`, et sauf réponse périmée) : « Recherche indisponible. »
- **Échap** ferme la liste ; un clic ailleurs dans la page la masque.

### 34. `chargerMarche()` — données de marché d'un ticker

```js
// -------- Données de marché d'un ticker (commun à tous les onglets) --------
// Compteur de version par champ de statut : seule la dernière sélection s'affiche.
async function chargerMarche(symbol, status, appliquer, bouton) {
  const version = status.dataset.version = String(Number(status.dataset.version || 0) + 1);
  if (bouton) bouton.disabled = true;
  status.textContent = 'Récupération des données de marché…';
  try {
    const data = await appelApi('/api/market/' + encodeURIComponent(symbol), {timeout: 30000});
    if (version !== status.dataset.version) return;
    if (!(Number.isFinite(data.S0) && data.S0 > 0)) throw new Error('Spot indisponible.');
    appliquer(data);
    status.textContent = `${symbol} (${data.devise || ''}) · spot ${data.S0} · vol. historique ${fmtPct(data.vol_hist)} · VIX ${fmtPct(data.vix)}`;
  } catch (err) {
    if (version === status.dataset.version) status.textContent = 'Erreur : ' + err.message;
  } finally {
    if (bouton && version === status.dataset.version) bouton.disabled = false;
  }
}
```

Après le choix d'un ticker, on récupère spot, devise, vol historique et VIX via `/api/market/<symbole>`.

- **Compteur de version par champ de statut** : `status.dataset.version` (un attribut `data-version` sur l'élément) est incrémenté à chaque appel. Si l'utilisateur choisit AAPL puis MSFT très vite, seule la réponse de MSFT s'affiche, même si celle d'AAPL arrive après.
- `if (bouton) bouton.disabled = true;` : on bloque le bouton Calculer de l'onglet pendant le chargement : impossible de calculer avec un spot à moitié mis à jour.
- `encodeURIComponent(symbol)` : un symbole comme `^GSPC` ou `BRK-B` est encodé correctement dans l'URL.
- `if (!(Number.isFinite(data.S0) && data.S0 > 0)) throw ...` : on refuse un spot absent, nul ou non numérique **avant** de toucher au formulaire.
- `appliquer(data)` : chaque onglet décide quoi faire des données (remplir le spot, recentrer les strikes…) ; cette fonction ne connaît pas les onglets.
- Le message de statut résume ce qui a été chargé.
- `finally` : réactive le bouton, mais seulement si cet appel est toujours le dernier.

### 35. Volatilité : les données partagées

```js
// -------- Volatilité : manuelle, historique 1 an ou VIX --------
// Les vols de marché sont gardées par onglet (préfixe des identifiants du formulaire) après la recherche d'un ticker.
const volMarche = {};
const LIBELLES_VOL = {hist: 'σ historique 1 an', vix: 'σ = VIX'};
```

- Chaque formulaire qui demande une volatilité a des champs nommés avec le **même suffixe** et un **préfixe** propre (`opt-sigma-source`…). Les fonctions suivantes prennent ce préfixe `p` : écrites une fois, elles servent à tous les onglets.
- `volMarche` : les vols de marché chargées, rangées par préfixe d'onglet (`volMarche.opt = {hist: 23.4, vix: 15.1}`).
- `LIBELLES_VOL` : le libellé affiché selon la source.

### 36. `afficherSigma()` — afficher la bonne zone

```js
function afficherSigma(p) {
  const source = $(p + '-sigma-source').value;
  const manuelle = source === 'manual';
  $(p + '-sigma-manual-wrap').hidden = !manuelle;
  $(p + '-sigma-mkt-wrap').hidden = manuelle;
  $(p + '-sigma').required = manuelle;
  if (!manuelle) {
    $(p + '-sigma-mkt-label').textContent = LIBELLES_VOL[source];
    const v = (volMarche[p] || {})[source];
    $(p + '-sigma-mkt-display').value = v == null ? 'cherche un ticker' : fmtPct(v);
  }
}
```

- Source manuelle : la saisie est visible et obligatoire (`required = manuelle`) ; sinon elle est cachée et **non** obligatoire (un champ caché obligatoire bloquerait l'envoi sans que l'utilisateur puisse le voir).
- Source de marché : on affiche la valeur chargée pour cet onglet, ou « cherche un ticker » s'il n'y en a pas encore.

### 37. `wireSigma()` — brancher le sélecteur

```js
function wireSigma(p) {
  $(p + '-sigma-source').addEventListener('change', () => afficherSigma(p));
  afficherSigma(p);
}
```

- Réafficher à chaque changement de source, et une fois tout de suite pour l'état initial.

### 38. `setVolMarche()` — après la recherche

```js
// Après la recherche : conserver historique et VIX pour cet onglet.
function setVolMarche(p, data) {
  volMarche[p] = {hist: data.vol_hist, vix: data.vix};
  $(p + '-sigma-source').value = data.vol_hist != null ? 'hist' : 'vix';
  afficherSigma(p);
}
```

- Mémorise vol historique et VIX pour l'onglet.
- Bascule automatiquement sur la vol historique si elle existe (sinon sur le VIX) : après avoir choisi un ticker, on veut en général utiliser **sa** volatilité.

### 39. `lireSigma()` — la valeur à envoyer

```js
function lireSigma(p) {
  const source = $(p + '-sigma-source').value;
  if (source === 'manual') return $(p + '-sigma').value;
  const v = (volMarche[p] || {})[source];
  if (v == null) {
    throw new Error(source === 'hist'
      ? "Cherche d'abord un ticker pour calculer sa volatilité historique."
      : "Cherche d'abord un ticker pour récupérer le VIX.");
  }
  return v;
}
```

- Source manuelle : la valeur du champ.
- Source de marché : la valeur mémorisée ; si elle n'existe pas, une **exception** avec un message clair. Comme `lireSigma` est appelée dans `calcul()`, `surSoumission` affiche ce message en rouge, sans requête inutile au serveur.

### 40. Strikes bornés : les données partagées

```js
// -------- Strikes bornés autour du spot --------
// Les bornes viennent du serveur (/api/config) : la règle n'est écrite que dans validation.py.
const moneyness = {min: null, max: null};
const arrondi = x => Math.round(x * 100) / 100;
```

- `moneyness` : les bornes du rapport K / S0 acceptées par le serveur (par exemple 0,2 à 5). Elles ne sont **pas** recopiées dans la page : elles viennent de `/api/config`. Ainsi, la règle n'est écrite qu'à un seul endroit (`validation.py`) et la page ne peut pas être en désaccord avec le serveur.
- `arrondi` : arrondi au centime.

### 41. `bindStrikeBounds()` — afficher les bornes du strike

```js
function bindStrikeBounds(spotId, strikeIds, hintId) {
  const update = () => {
    const S0 = Number($(spotId).value);
    if (!(S0 > 0) || moneyness.min == null) return;
    // ceil / floor pour que les bornes affichées restent dans l'intervalle accepté par le serveur
    const lo = Math.ceil(S0 * moneyness.min * 100) / 100;
    const hi = Math.floor(S0 * moneyness.max * 100) / 100;
    strikeIds.forEach(id => { $(id).min = lo; $(id).max = hi; });
    $(hintId).textContent = `Strike(s) entre ${fmt(lo)} et ${fmt(hi)}, soit ${Math.round(moneyness.min*100)} % à ${Math.round(moneyness.max*100)} % du spot.`;
  };
  $(spotId).addEventListener('input', update);
  return update;
}
const updateOptStrikes = bindStrikeBounds('opt-s0', ['opt-k'], 'opt-k-hint');
const updateStratStrikes = bindStrikeBounds('strat-s0', ['strat-k', 'strat-k1', 'strat-k2'], 'strat-k-hint');
appelApi('/api/config', {timeout: 10000}).then(config => {
  moneyness.min = config.moneyness_min;
  moneyness.max = config.moneyness_max;
  updateOptStrikes();
  updateStratStrikes();
}).catch(() => { /* le serveur revalide de toute façon les strikes */ });
```

- `update()` recalcule les bornes à partir du spot saisi et les pose en `min`/`max` sur les champs de strike : le navigateur refuse alors un strike hors bornes (champ rouge, bulle à l'envoi).
- `Math.ceil` pour la borne basse, `Math.floor` pour la haute : après arrondi au centime, les bornes affichées restent **à l'intérieur** de l'intervalle du serveur. Avec un arrondi classique, la page pourrait accepter un strike que le serveur refuserait ensuite.
- Le texte d'aide affiche les bornes en prix et en % du spot.
- `update` est rappelée à chaque saisie du spot, et renvoyée à l'appelant pour qu'il puisse la relancer (après le chargement d'un ticker, par exemple).
- `updateOptStrikes = bindStrikeBounds(...)` et `updateStratStrikes = ...` : le branchement pour l'onglet Options, puis pour l'onglet Stratégies (trois champs de strike).
- `appelApi('/api/config', ...).then(config => { ... })` : au chargement de la page, on lit les bornes puis on met à jour l'affichage.
- `.catch(() => {})` : si cet appel échoue, la page fonctionne quand même ; le serveur revalide les strikes de toute façon. Le commentaire dans le `catch` dit pourquoi l'erreur est volontairement ignorée.

### 42. Onglet Options : méthodes disponibles

```js
// -------- Onglet Options --------
// Méthodes possibles selon le style d'exercice :
// une option européenne a une formule fermée (Black-Scholes) ou se simule (Monte Carlo),
// une option américaine se price ici uniquement par Longstaff-Schwartz.
const METHODES = {
  european: [['black_scholes', 'Black-Scholes'], ['monte_carlo', 'Monte Carlo']],
  american: [['longstaff_schwartz', 'Longstaff-Schwartz']],
};
const NOMS_MODELES = {black_scholes: 'Black-Scholes', monte_carlo: 'Monte Carlo', longstaff_schwartz: 'Longstaff-Schwartz'};
```

- `METHODES` : pour chaque style d'exercice, la liste des méthodes `[valeur envoyée, libellé affiché]`. Une option européenne a une formule fermée (Black-Scholes) ou se simule (Monte Carlo) ; une option américaine peut être exercée à tout moment, il n'y a pas de formule fermée : ici, uniquement Longstaff-Schwartz.
- `NOMS_MODELES` : pour afficher en clair le modèle réellement utilisé, renvoyé par le serveur (`model_used`).

### 43. `updateOptMethod()` — remplir la liste des méthodes

```js
function updateOptMethod() {
  const style = $('opt-style').value;
  $('opt-method').innerHTML = METHODES[style].map(([v, label]) => `<option value="${v}">${label}</option>`).join('');
  $('opt-method').disabled = METHODES[style].length === 1;
  updateOptNsims();
}
```

- Reconstruit les `<option>` de `opt-method` selon le style choisi. Ici `innerHTML` est sans risque : le contenu vient de la constante `METHODES`, pas d'une saisie.
- Une seule méthode possible : le menu est désactivé (rien à choisir).
- Puis on met à jour l'affichage du nombre de simulations.

### 44. Nombre de simulations et digitales

```js
// Le nombre de simulations n'apparaît que si un calcul simule (Monte Carlo, Longstaff-Schwartz, digitale).
function updateOptNsims() {
  $('opt-nsims-wrap').hidden = $('opt-instrument').value === 'vanilla' && $('opt-method').value === 'black_scholes';
}
$('opt-style').addEventListener('change', updateOptMethod);
$('opt-method').addEventListener('change', updateOptNsims);
updateOptMethod();

// Une digitale est européenne : style forcé, Black-Scholes + Monte Carlo calculés tous les deux.
$('opt-instrument').addEventListener('change', () => {
  const digital = $('opt-instrument').value !== 'vanilla';
  $('digital-payout-wrap').hidden = $('opt-instrument').value !== 'cash';
  $('digital-note').hidden = !digital;
  if (digital) { $('opt-style').value = 'european'; updateOptMethod(); $('opt-method').value = 'black_scholes'; }
  $('opt-style').disabled = digital;
  $('opt-method').disabled = digital;
  updateOptNsims();
});
```

- `updateOptNsims()` : le champ du nombre de simulations n'est visible que si un calcul simule, c'est-à-dire tout sauf une option classique en Black-Scholes.
- Les écouteurs `change` sur le style et la méthode, puis `updateOptMethod()` une première fois pour l'état initial.
- **Changement d'instrument** :
  - le montant fixe n'apparaît que pour une digitale *cash* ; la note, pour toute digitale ;
  - une digitale est **européenne** (elle ne paie qu'à maturité) : on force le style européen et Black-Scholes, puis on **désactive** les deux menus. Le serveur calcule pour une digitale les deux prix, Black-Scholes et Monte Carlo, ce qui permet de les comparer.

### 45. Onglet Options : recherche de ticker

```js
brancherRechercheTicker({
  inputId: 'opt-ticker', resultsId: 'opt-ticker-results', statusId: 'opt-ticker-status',
  onSelect: (symbol, status) => chargerMarche(symbol, status, data => {
    $('opt-s0').value = data.S0;
    $('opt-k').value = arrondi(data.S0);   // on repart à la monnaie
    updateOptStrikes();
    setVolMarche('opt', data);
  }, $('form-options').querySelector('button[type=submit]')),
});
wireSigma('opt');
```

- `brancherRechercheTicker({...})` avec les identifiants de l'onglet.
- `onSelect` : charge les données de marché puis, dans `appliquer` : recopie le spot, **remet le strike à la monnaie** (K = S0 arrondi ; un strike de 100 n'a pas de sens pour une action à 3 000), recalcule les bornes et mémorise les vols.
- Le dernier argument est le bouton Calculer de l'onglet, bloqué pendant le chargement.
- `wireSigma('opt')` : branche le choix de la volatilité de l'onglet.

### 46. Onglet Options : le calcul

```js
surSoumission($('form-options'), $('opt-status'), async () => {
  const instrument = $('opt-instrument').value;
  const payload = {
    side: $('opt-side').value, option_type: $('opt-type').value, style: $('opt-style').value,
    method: $('opt-method').value, S0: $('opt-s0').value, K: $('opt-k').value, T: $('opt-t').value,
    sigma: lireSigma('opt'), r: $('opt-r').value, q: $('opt-q').value,
    n_simulations: $('opt-nsims').value,
  };
  if (instrument !== 'vanilla') { payload.digital_type = instrument; payload.payout = $('digital-payout').value; }
  const data = await appelApi(instrument === 'vanilla' ? '/api/option' : '/api/digital', {payload});

  $('opt-results').innerHTML = `
    <div class="metrics">
      <div class="metric"><p>Prix</p><strong>${fmt(data.price)}</strong></div>
      <div class="metric"><p>Breakeven(s)</p><strong>${data.breakevens.length ? data.breakevens.map(fmt).join(' / ') : '—'}</strong></div>
      <div class="metric"><p>Delta</p><strong>${fmt(data.primaires.Delta)}</strong></div>
    </div>
    <div class="card chart-card">${renderChart(data.ST_grid, [{key:'payoff', values:data.payoff}, {key:'pnl', values:data.pnl}], data.breakevens)}</div>
    <div class="card chart-card">
      <h2>Grecques primaires</h2>
      ${greeksTable(data.primaires, ['Delta','Gamma','Vega','Theta','Rho'])}
      <details><summary>Grecques secondaires</summary>${greeksTable(data.secondaires, ['Vanna','Vomma','Charm','Color','Speed','Zomma','Ultima','Lambda'])}</details>
    </div>`;
  if (data.monte_carlo) {
    $('opt-results').insertAdjacentHTML('beforeend', `<div class="card chart-card">Monte Carlo : ${fmt(data.monte_carlo.price)} · IC95 : ${data.monte_carlo.ic95.map(fmt).join(' à ')}</div>`);
  }
  appendExtras('opt-results', data);
  return 'Résultats à jour (' + (NOMS_MODELES[data.model_used] || data.model_used) + ').';
});
```

- `payload` : les paramètres envoyés. Les valeurs sont envoyées **telles que saisies** (chaînes, pourcentages) : la conversion et la validation sont faites par le serveur, à un seul endroit.
- `n_simulations` est toujours envoyé ; le serveur l'ignore si la méthode ne simule pas.
- Pour une digitale, on ajoute son type et son montant, et on appelle `/api/digital` au lieu de `/api/option`.
- **Affichage** :
  - trois indicateurs : prix, breakeven(s) (`'—'` s'il n'y en a pas), delta ;
  - le graphique payoff + P&L avec les breakevens ;
  - les grecques primaires, puis les secondaires dans un bloc repliable (plus avancées, rarement lues en premier) ;
  - si le serveur a renvoyé un résultat Monte Carlo (cas des digitales), une carte avec son prix et son intervalle de confiance à 95 %, à comparer au prix Black-Scholes ;
  - `appendExtras` ajoute le bouton d'export PDF.
- Le message de succès indique le modèle réellement utilisé.

### 47. Onglet Forward : le calcul

```js
// -------- Onglet Forward --------
surSoumission($('form-forward'), $('fwd-status'), async () => {
  const payload = {
    side: $('fwd-side').value, S0: $('fwd-s0').value, K: $('fwd-k').value,
    T: $('fwd-t').value, r: $('fwd-r').value, q: $('fwd-q').value,
  };
  const data = await appelApi('/api/forward', {payload});
  $('fwd-results').innerHTML = `
    <div class="metrics">
      <div class="metric"><p>Prix à terme théorique F</p><strong>${fmt(data.forward_price)}</strong></div>
      <div class="metric"><p>Valeur actuelle du contrat</p><strong>${fmt(data.valeur_actuelle)}</strong></div>
      <div class="metric"><p>Breakeven</p><strong>${data.breakevens.length ? data.breakevens.map(fmt).join(' / ') : '—'}</strong></div>
    </div>
    <div class="card chart-card">${renderChart(data.ST_grid, [{key:'payoff', values:data.payoff}, {key:'pnl', values:data.pnl}], data.breakevens)}</div>`;
  appendExtras('fwd-results', data);
  return 'Résultats à jour.';
});
```

- `payload` : position, spot, prix contractuel, maturité, taux, dividende ; appel à `/api/forward`.
- Trois indicateurs : le **prix à terme théorique** F (celui qui donne une valeur nulle au contrat aujourd'hui), la **valeur actuelle** du contrat au prix K saisi, et le breakeven.
- Le graphique du payoff et du P&L, qui sont des droites : pas d'optionnalité.
- Puis l'export PDF.

### 48. Onglet Stratégies : quels champs pour quelle stratégie

```js
// -------- Onglet Stratégies : champs dynamiques --------
const STRAT_FIELDS = {
  covered_call:   {k:true,  k1:false, k2:false, side:false},
  protective_put: {k:true,  k1:false, k2:false, side:false},
  straddle:       {k:true,  k1:false, k2:false, side:true},
  strangle:       {k:false, k1:false, k2:false, side:true, kput:true, kcall:true},
  call_spread:    {k:false, k1:true,  k2:true,  side:false},
  put_spread:     {k:false, k1:true,  k2:true,  side:false},
  collar:         {k:false, k1:false, k2:false, side:false, kput:true, kcall:true},
};
```

- `STRAT_FIELDS` : pour chaque stratégie, les champs utiles. `k` : un seul strike ; `k1`/`k2` : deux strikes d'un spread ; `kput`/`kcall` : un strike de put et un de call (strangle, collar) ; `side` : achat ou vente au choix.
- Une **table de configuration** plutôt que des `if` dispersés : pour ajouter une stratégie, on ajoute une ligne.

### 49. Onglet Stratégies : libellés des strikes

```js
const STRAT_LABELS = {
  k1_call_spread: 'Strike K1 (achat)', k2_call_spread: 'Strike K2 (vente)',
  k1_put_spread: 'Strike K1 (achat, haut)', k2_put_spread: 'Strike K2 (vente, bas)',
  kput: 'Strike put', kcall: 'Strike call',
};
```

- Les libellés des deux champs de strike selon la stratégie. Pour un put spread, K1 est le strike **haut** (put acheté) et K2 le strike **bas** (put vendu) : on le précise pour éviter l'erreur classique d'inversion.

### 50. `updateStrategyFields()` — adapter le formulaire

```js
function updateStrategyFields() {
  const strat = $('strat-name').value;
  const cfg = STRAT_FIELDS[strat];

  $('strat-side-wrap').hidden = !cfg.side;
  $('strat-k-wrap').hidden = !cfg.k;
  $('strat-k1-wrap').hidden = !(cfg.k1 || cfg.kput);
  $('strat-k2-wrap').hidden = !(cfg.k2 || cfg.kcall);
  // les champs masqués sont aussi désactivés pour ne pas bloquer la validation du formulaire
  $('strat-k').disabled = !cfg.k;
  $('strat-k1').disabled = !(cfg.k1 || cfg.kput);
  $('strat-k2').disabled = !(cfg.k2 || cfg.kcall);

  if (cfg.kput) { $('strat-k1-label').textContent = STRAT_LABELS.kput; }
  else if (strat === 'call_spread') { $('strat-k1-label').textContent = STRAT_LABELS.k1_call_spread; }
  else if (strat === 'put_spread') { $('strat-k1-label').textContent = STRAT_LABELS.k1_put_spread; }

  if (cfg.kcall) { $('strat-k2-label').textContent = STRAT_LABELS.kcall; }
  else if (strat === 'call_spread') { $('strat-k2-label').textContent = STRAT_LABELS.k2_call_spread; }
  else if (strat === 'put_spread') { $('strat-k2-label').textContent = STRAT_LABELS.k2_put_spread; }
}
$('strat-name').addEventListener('change', updateStrategyFields);
updateStrategyFields();
```

- Affiche ou cache le sens et chaque champ de strike selon `STRAT_FIELDS`. Les champs `k1` et `k2` servent aussi à `kput` et `kcall`.
- **Les champs cachés sont aussi désactivés** (`disabled`) : un champ caché mais actif, avec une valeur hors bornes, bloquerait `reportValidity()` avec une erreur sur un champ invisible. Un champ désactivé est ignoré par la validation.
- Puis on change les libellés selon la stratégie.
- Rappelée à chaque changement de stratégie, et une fois au chargement.

### 51. `recentrerStrategie()` — strikes autour du nouveau spot

```js
// Quand on change de sous-jacent, on recentre les strikes autour du nouveau spot.
function recentrerStrategie(S0) {
  const strat = $('strat-name').value;
  $('strat-k').value = arrondi(S0);
  const bas = arrondi(S0 * 0.95), haut = arrondi(S0 * 1.05);
  if (strat === 'put_spread') { $('strat-k1').value = haut; $('strat-k2').value = bas; }
  else { $('strat-k1').value = bas; $('strat-k2').value = haut; }
}
```

- Après le choix d'un ticker : K = spot (à la monnaie), et deux strikes à ±5 % du spot.
- Pour un put spread, K1 doit être le strike haut : on inverse l'ordre.

### 52. Onglet Stratégies : recherche de ticker

```js
brancherRechercheTicker({
  inputId: 'strat-ticker', resultsId: 'strat-ticker-results', statusId: 'strat-ticker-status',
  onSelect: (symbol, status) => chargerMarche(symbol, status, data => {
    $('strat-s0').value = data.S0;
    recentrerStrategie(data.S0);
    updateStratStrikes();
    setVolMarche('strat', data);
  }, $('form-strategy').querySelector('button[type=submit]')),
});
wireSigma('strat');
```

- Même principe que l'onglet Options : on recopie le spot, on recentre les strikes, on recalcule les bornes et on mémorise les vols ; puis `wireSigma('strat')`.

### 53. Onglet Stratégies : le calcul

```js
surSoumission($('form-strategy'), $('strat-status'), async () => {
  const strat = $('strat-name').value;
  const cfg = STRAT_FIELDS[strat];
  const payload = {
    strategy: strat, S0: $('strat-s0').value, T: $('strat-t').value,
    sigma: lireSigma('strat'), r: $('strat-r').value, q: $('strat-q').value,
    qty: $('strat-qty').value, side: cfg.side ? $('strat-side').value : 'buy',
  };
  if (cfg.k) payload.K = $('strat-k').value;
  if (cfg.k1) payload.K1 = $('strat-k1').value;
  if (cfg.k2) payload.K2 = $('strat-k2').value;
  if (cfg.kput) payload.K_put = $('strat-k1').value;
  if (cfg.kcall) payload.K_call = $('strat-k2').value;

  const data = await appelApi('/api/strategy', {payload});
  $('strat-results').innerHTML = `
    <div class="metrics">
      <div class="metric"><p>Breakeven(s)</p><strong>${data.breakevens.length ? data.breakevens.map(fmt).join(' / ') : '—'}</strong></div>
      <div class="metric"><p>Delta net</p><strong>${fmt(data.greeks.Delta)}</strong></div>
      <div class="metric"><p>Theta net</p><strong>${fmt(data.greeks.Theta)}</strong></div>
    </div>
    <div class="card chart-card">${renderChart(data.ST_grid, [{key:'pnl', values:data.pnl}], data.breakevens)}</div>
    <div class="card chart-card"><h2>Grecques agrégées de la stratégie</h2>${greeksTable(data.greeks, ['Delta','Gamma','Vega','Theta','Rho'])}</div>`;
  appendExtras('strat-results', data);
  return 'Résultats à jour · ' + data.n_legs + ' leg(s).';
});
```

- `side: cfg.side ? ... : 'buy'` : le sens n'est envoyé que pour les stratégies où il a un sens ; les autres sont définies côté « achat » (un covered call est par définition action achetée + call vendu).
- On n'ajoute **que** les strikes utiles à la stratégie, sous les noms attendus par le serveur (`K`, `K1`, `K2`, `K_put`, `K_call`).
- Affichage : breakevens, delta net et theta net (le theta dit si la stratégie gagne ou perd au passage du temps), le graphique du P&L **seul** (le payoff brut d'une combinaison est moins parlant), puis les grecques **agrégées** : la somme signée des grecques de chaque jambe.
- Le message indique le nombre de jambes (*legs*) de la stratégie.

### 54. Produits structurés : le compteur de version

```js
// -------- Onglet Produits structurés : choix du produit --------
// Chaque produit a son propre <form data-product="...">. Pour en ajouter un,
// il suffit d'ajouter une <option> et un formulaire avec le bon data-product.
// versionStructure change quand le produit ou ses règles changent : une réponse
// arrivée entre-temps est ignorée au lieu de s'afficher sur le mauvais écran.
let versionStructure = 0;
```

- `versionStructure` : un compteur incrémenté dès que le produit ou ses règles changent. Un calcul Monte Carlo peut durer plusieurs secondes : si l'utilisateur change de produit entre-temps, la réponse arrivée trop tard est **ignorée** au lieu de s'afficher sur l'écran d'un autre produit. Chaque calcul mémorise la version au départ et la compare à l'arrivée.

### 55. Produits structurés : changer de produit

```js
const CODES_PRODUITS = {
  phoenix: ['PHNX', 'Phoenix autocallable'],
  autocall_plain: ['ATHN', 'Athéna (Autocall Plain)'],
};
$('struct-product').addEventListener('change', () => {
  ++versionStructure;
  const produit = $('struct-product').value;
  document.querySelectorAll('#panel-structured form[data-product]').forEach(f => {
    f.hidden = f.dataset.product !== produit;
  });
  $('phx-results').innerHTML = '<div class="empty">Lance un calcul pour voir les résultats.</div>';
  $('cmd-code').textContent = 'STRC ' + CODES_PRODUITS[produit][0];
  $('cmd-desc').textContent = CODES_PRODUITS[produit][1];
});
```

- `CODES_PRODUITS` : le code de fonction et la description de chaque produit, pour la barre du haut (« STRC PHNX »).
- Au changement de produit : on invalide les calculs en cours (`++versionStructure`), on affiche le formulaire dont `data-product` correspond et on cache les autres, on vide les résultats et on met à jour la barre du haut.

### 56. `verifierMaturite()` — maturité cohérente avec la fréquence

```js
// Maturité en mois : un nombre entier de périodes d'observation (même règle que le serveur).
function verifierMaturite(moisId, freqId, aideId) {
  const champ = $(moisId), pasMois = 12 / Number($(freqId).value);
  champ.step = pasMois;
  champ.min = pasMois;
  const n = Number(champ.value) / pasMois;
  const ok = Number.isInteger(n) && n > 0;
  const message = `La maturité doit être un multiple de ${pasMois} mois.`;
  champ.setCustomValidity(ok ? '' : message);
  if (aideId) $(aideId).textContent = ok ? `${n} date(s) d'observation, tous les ${pasMois} mois.` : message;
  return ok;
}
```

- La maturité doit être un **nombre entier de périodes** : 36 mois en semestriel = 6 dates, mais 40 mois ne tombe pas juste. C'est la même règle que côté serveur.
- `pasMois = 12 / fréquence` (6 mois en semestriel) ; on règle `step` et `min` du champ pour que les flèches du champ avancent du bon pas.
- `Number.isInteger(n) && n > 0` : le nombre de dates doit être un entier positif.
- `setCustomValidity(message)` : rend le champ **invalide** pour le navigateur avec notre message (bulle native, champ rouge, envoi bloqué) ; `setCustomValidity('')` le rend valide.
- Si une zone d'aide est fournie, elle affiche le nombre de dates ou le message d'erreur. La fonction renvoie aussi le résultat.

### 57. `renderStructuredMetrics()` — les 8 indicateurs communs

```js
// Indicateurs communs au Phoenix et au Plain.
function renderStructuredMetrics(data) {
  const margin = data.marge_emetteur_pct;
  const metrics = [
    ['Prix théorique', fmtPct(data.prix_pct), ''],
    ['Valeur pour le montant investi', fmt2(data.prix), ''],
    ['Marge émetteur', fmtPct(margin), margin >= 0 ? 'pos' : 'neg'],
    ['Probabilité de perte en capital', fmtPct(data.proba_perte_capital_pct), ''],
    ['Durée de vie moyenne', fmt2(data.duree_de_vie_moyenne) + ' ans', ''],
    ['Arrive à maturité', fmtPct(data.proba_maturite_pct), ''],
    ['Remboursement moyen si perte', fmtPct(data.remboursement_moyen_si_perte_pct), ''],
    ['Coupons moyens actualisés', fmtPct(data.coupons_moyens_actualises_pct), ''],
  ];
  return '<div class="metrics structured-metrics">' + metrics.map(([label, value, style]) =>
    `<div class="metric"><p>${label}</p><strong class="${style}">${value}</strong></div>`
  ).join('') + '</div>';
}
```

- Les indicateurs communs au Phoenix et à l'Athéna, dans une liste `[libellé, valeur, style]` : prix théorique (% du nominal), valeur pour le montant investi, **marge émetteur** (verte si positive, rouge sinon), probabilité de perte en capital, durée de vie moyenne, probabilité d'aller à maturité, remboursement moyen en cas de perte, coupons moyens actualisés.
- **Marge émetteur** = 100 % − prix théorique : ce que la banque gagne à vendre le produit au pair (hors frais, financement et risque de défaut).
- Une liste de données + un seul `map` : pour ajouter un indicateur, on ajoute une ligne.

### 58. Phoenix : step-up, dates et spot

```js
// -------- Onglet Produits structurés : Phoenix --------
$('phx-stepup-on').addEventListener('change', () => {
  const on = $('phx-stepup-on').checked;
  $('phx-stepup-wrap').hidden = !on;
  $('phx-stepup').required = on;
});

// Les dates ne sont jamais saisies à la main : elles sont construites à partir
// de la maturité et de la fréquence, donc forcément croissantes.
const updatePhoenixDates = () => verifierMaturite('phx-months', 'phx-freq', 'phx-dates-hint');
$('phx-freq').addEventListener('change', updatePhoenixDates);
$('phx-months').addEventListener('input', updatePhoenixDates);

// Le spot ne se saisit pas : un Phoenix se lit en % du niveau de départ.
// Sans ticker on part de 100 (barrière 70 % = 70), avec un ticker on part du vrai spot.
let phxSpot = 100, phxDevise = '';
```

- La case *step-up* affiche le champ de hausse et le rend obligatoire seulement quand elle est cochée.
- `updatePhoenixDates` : appelle `verifierMaturite` avec les champs du Phoenix ; rappelée quand la fréquence ou la maturité change. Les dates d'observation sont déduites, donc forcément croissantes et régulières : toute une famille d'erreurs de saisie disparaît.
- `phxSpot` et `phxDevise` : le niveau de départ (100 sans ticker, le vrai spot avec un ticker) et la devise, utilisés pour traduire les barrières en prix.

### 59. `phxNiveau()` — une barrière en mots

```js
function phxNiveau(pct) {
  const niveau = phxSpot * pct / 100;
  const p = new Intl.NumberFormat('fr-FR', {maximumFractionDigits:2}).format(pct) + ' %';
  return phxDevise ? `${p} du départ (${fmt(niveau)} ${phxDevise})` : `${p} du départ`;
}
```

- Transforme un pourcentage en texte : « 70 % du départ », ou, avec un ticker, « 70 % du départ (152,30 USD) ». L'investisseur voit le niveau réel à surveiller.

### 60. `updatePhoenixHints()` — les phrases d'aide des barrières

```js
function updatePhoenixHints() {
  const kauto = Number($('phx-kauto').value), bcoupon = Number($('phx-bcoupon').value), bpdi = Number($('phx-bpdi').value);
  $('phx-kauto-hint').textContent = $('phx-autocall').checked
    ? `À chaque date, si le sous-jacent est au-dessus de ${phxNiveau(kauto)}, tu récupères ton capital + le coupon et le produit s'arrête.`
    : 'Désactivé : le produit va toujours jusqu\'à maturité.';
  $('phx-bcoupon-hint').textContent = `À chaque date, s'il est au-dessus de ${phxNiveau(bcoupon)}, tu touches le coupon.`;
  $('phx-bpdi-hint').textContent = `À maturité, s'il est sous ${phxNiveau(bpdi)}, tu perds autant que la baisse du sous-jacent.`;
}
```

- Pour chaque barrière, une phrase qui dit **ce qui se passe** si le sous-jacent la franchit : rappel avec capital + coupon, coupon versé, perte en capital à maturité. Un étudiant comprend le produit en lisant le formulaire.
- Sans autocall, l'aide du rappel indique que le produit va toujours jusqu'à maturité.

### 61. Ordre des barrières du Phoenix

```js
// Ordre des barrières : protection ≤ coupon ≤ rappel.
// setCustomValidity bloque l'envoi du formulaire avec un message natif du navigateur.
function checkPhoenixBarriers() {
  const kauto = Number($('phx-kauto').value), bcoupon = Number($('phx-bcoupon').value), bpdi = Number($('phx-bpdi').value);
  $('phx-bpdi').setCustomValidity(bpdi > bcoupon ? 'La protection doit être ≤ à la barrière coupon.' : '');
  $('phx-bcoupon').setCustomValidity($('phx-autocall').checked && bcoupon > kauto ? 'La barrière coupon doit être ≤ à la barrière de rappel.' : '');
}
['phx-kauto', 'phx-bcoupon', 'phx-bpdi'].forEach(id => $(id).addEventListener('input', () => {
  updatePhoenixHints();
  checkPhoenixBarriers();
}));
$('phx-autocall').addEventListener('change', () => {
  $('phx-kauto').disabled = !$('phx-autocall').checked;
  updatePhoenixHints();
  checkPhoenixBarriers();
});
updatePhoenixDates();
updatePhoenixHints();
```

- `checkPhoenixBarriers()` : impose protection ≤ coupon ≤ rappel (la seconde contrainte seulement si le rappel est actif) avec `setCustomValidity` : le navigateur bloque l'envoi et affiche le message sur le bon champ. Le serveur fait la même vérification.
- À chaque saisie d'une barrière : mise à jour des aides et de la vérification.
- La case autocall active ou désactive le champ de rappel, puis met à jour aides et vérification.
- `updatePhoenixDates(); updatePhoenixHints();` : l'état initial au chargement.

### 62. Phoenix : recherche de ticker

```js
brancherRechercheTicker({
  inputId: 'phx-ticker', resultsId: 'phx-ticker-results', statusId: 'phx-ticker-status',
  onSelect: (symbol, status) => chargerMarche(symbol, status, data => {
    phxSpot = data.S0; phxDevise = data.devise;
    updatePhoenixHints();
    setVolMarche('phx', data);
  }, $('form-phoenix').querySelector('button[type=submit]')),
});
wireSigma('phx');
```

- Le ticker sert ici à fixer le niveau de départ (`phxSpot`), la devise et les vols ; les aides des barrières se mettent à jour avec les prix réels. Puis `wireSigma('phx')`.

### 63. Phoenix : le calcul

```js
surSoumission($('form-phoenix'), $('phx-status'), async () => {
  const version = versionStructure;
  const freq = Number($('phx-freq').value);
  const nDates = Number($('phx-months').value) / (12 / freq);
  const coupon0 = Number($('phx-coupon').value);
  const hausse = $('phx-stepup-on').checked ? Number($('phx-stepup').value) : 0;
  // Coupon fixe si pas de hausse, sinon liste step-up : c, c + h, c + 2h...
  const coupon = hausse > 0 ? Array.from({length: nDates}, (_, i) => coupon0 + i * hausse) : coupon0;

  const payload = {
    S0: phxSpot, sigma: lireSigma('phx'), r: $('phx-r').value, q: $('phx-q').value,
    nominal: $('phx-nominal').value,
    T: Number($('phx-months').value) / 12, frequence: freq,
    coupon: coupon,
    K_auto: $('phx-kauto').value, B_phoenix: $('phx-bcoupon').value, B_pdi: $('phx-bpdi').value,
    memory: $('phx-memory').checked, has_autocall: $('phx-autocall').checked,
    bonus_threshold: $('phx-bonus-threshold').value,
    bonus_amount: $('phx-bonus-amount').value || 0,
    n_simulations: $('phx-nsims').value,
    step_down: $('phx-step-down').value,
  };
  const data = await appelApi('/api/phoenix', {payload});
  if (version !== versionStructure) return;

  const niv = data.niveaux;
  const markers = [
    niv.autocall !== null ? {x: niv.autocall, label: 'Rappel', color: '#5cc8ff'} : null,
    {x: niv.coupon, label: 'Coupon', color: '#3ddc84'},
    {x: niv.protection, label: 'Protection', color: '#ff5c5c'},
  ].filter(Boolean);

  const n = data.obs_dates.length;
  const lignes = data.obs_dates.map((t, i) => `<tr>
      <td>${fmt(t)} an(s)</td>
      <td>${fmtPct(data.coupon_schedule_pct[i])}</td>
      <td>${i === n - 1 ? 'Maturité' : !payload.has_autocall ? 'Désactivé' : fmtPct(data.proba_rappel_par_date_pct[i])}</td>
    </tr>`).join('');

  $('phx-results').innerHTML = `
    ${renderStructuredMetrics(data)}
    <div class="card chart-card">
      ${renderChart(data.ST_grid, [{key:'payoff', values:data.payoff}, {key:'pnl', values:data.pnl}], [], {
        labels: {payoff: 'Remboursement à maturité', pnl: 'Gain ou perte vs montant investi'},
        xLabel: phxDevise ? `Prix du sous-jacent à maturité (${phxDevise})` : 'Niveau du sous-jacent à maturité (100 = départ)',
        markers: markers,
      })}
      <p class="chart-note">Cas où le produit n'a pas été rappelé avant maturité. Seul le coupon de la dernière date est compté : les coupons déjà versés et l'effet mémoire dépendent du chemin suivi. Intervalle de confiance du prix : ${fmtPct(data.ic95_pct[0])} à ${fmtPct(data.ic95_pct[1])}.</p>
    </div>
    <div class="card chart-card">
      <h2>Calendrier d'observation</h2>
      <table class="greeks-table">
        <thead><tr><th>Date</th><th>Coupon de la période</th><th>Probabilité de rappel</th></tr></thead>
        <tbody>${lignes}</tbody>
      </table>
    </div>`;
  appendExtras('phx-results', data);
  return `Résultats à jour (${fmt(data.prix)} pour ${fmt(Number(payload.nominal))} investis).`;
}, {avant: checkPhoenixBarriers, attente: 'Simulation en cours...'});
```

**Préparation**
- `const version = versionStructure;` : on mémorise la version au départ.
- `nDates` : nombre de dates = maturité en mois / pas en mois.
- **Coupon step-up** : sans hausse, un nombre ; avec hausse, une **liste** d'un coupon par date (`c, c+h, c+2h…`). `Array.from({length: nDates}, (_, i) => ...)` crée un tableau de `nDates` éléments calculés à partir de leur indice. Le serveur accepte les deux formes.
- `payload` : le spot (`phxSpot`), la vol, la maturité en **années** (`mois / 12`), les barrières, les options (mémoire, autocall, bonus, step-down) et le nombre de simulations.
- Après l'appel : `if (version !== versionStructure) return;` : réponse périmée, on n'affiche rien.

**Affichage**
- `markers` : une ligne verticale par barrière (rappel seulement s'il est actif ; `.filter(Boolean)` retire le `null`). Les niveaux viennent du serveur (`data.niveaux`), déjà convertis en prix.
- Le calendrier d'observation : une ligne par date avec le coupon de la période et la probabilité de rappel (« Maturité » pour la dernière date, « Désactivé » sans autocall).
- Les 8 indicateurs, le graphique (libellés et axe adaptés au produit), une note qui explique **ce que montre** le graphique (le cas sans rappel, avec seulement le dernier coupon : les coupons déjà versés dépendent du chemin suivi, ils ne peuvent pas figurer sur un graphique en fonction du seul prix final) et l'intervalle de confiance du prix.
- Puis le tableau des flux et l'export PDF (`appendExtras`).
- Options de `surSoumission` : `avant: checkPhoenixBarriers` (revérifier juste avant l'envoi) et un message d'attente adapté.

### 64. Athéna : raccourcis

```js
// -------- Onglet Produits structurés : Athéna (Autocall Plain) --------
const ac = id => $('ac-plain-' + id);
const formAutocall = $('form-autocall_plain');
```

- `ac = id => $('ac-plain-' + id)` : tous les champs de l'Athéna ont le préfixe `ac-plain-` ; `ac('coupon')` est plus court et plus lisible.
- `formAutocall` : le formulaire, utilisé plusieurs fois.

### 65. `afficherAutocall()` — résultats de l'Athéna

```js
function afficherAutocall(data) {
  const hasAutocall = data.has_autocall !== false;
  const result = document.createElement('div');
  result.innerHTML = renderStructuredMetrics(data);
  const card = document.createElement('div'); card.className = 'card chart-card';
  const title = document.createElement('h2');
  title.textContent = hasAutocall ? 'Athéna · résultats' : 'Athéna sans rappel · résultats';
  const note = document.createElement('p'); note.className = 'chart-note';
  note.textContent = `Intervalle de confiance Monte Carlo à 95 % : ${fmtPct(data.ic95_pct[0])} à ${fmtPct(data.ic95_pct[1])}. ${data.n_simulations.toLocaleString('fr-FR')} simulations. Écart souscription − valeur : ${fmtPct(data.marge_emetteur_pct)} (hors coûts et risque de défaut).`;
  const rules = document.createElement('p'); rules.className = 'chart-note';
  rules.textContent = (hasAutocall
    ? 'Les coupons s’accumulent : paiement au rappel, ou à maturité si le seuil final est atteint.'
    : 'Aucun rappel anticipé. À maturité, tous les coupons accumulés sont payés si le seuil final est atteint, sinon aucun.')
    + ' La probabilité de perte concerne le principal, avant prise en compte des coupons.';
  const loss = document.createElement('p'); loss.className = 'chart-note';
  loss.textContent = data.remboursement_moyen_si_perte_pct === null
    ? 'Aucune perte de capital dans les simulations.'
    : 'Capital moyen remboursé en cas de perte : ' + fmtPct(data.remboursement_moyen_si_perte_pct) + '.';
  card.append(title, note, rules, loss);

  const calendar = document.createElement('div'); calendar.className = 'card chart-card';
  const h = document.createElement('h2'); h.textContent = 'Calendrier des observations';
  const table = document.createElement('table'); table.className = 'greeks-table';
  table.innerHTML = '<thead><tr><th>Date</th><th>Coupon accumulé</th><th>Rappel à cette date</th></tr></thead>';
  const body = document.createElement('tbody');
  data.obs_dates.forEach((t, i) => {
    const row = document.createElement('tr');
    const rappel = i === data.obs_dates.length - 1 ? 'Maturité'
      : !hasAutocall ? 'Désactivé'
      : t < data.first_call_date ? 'Non autorisé'
      : fmtPct(data.proba_rappel_par_date_pct[i]);
    for (const text of [fmt2(t) + ' ans', fmtPct(data.coupon_pct * (i + 1)), rappel]) {
      const td = document.createElement('td'); td.textContent = text; row.append(td);
    }
    body.append(row);
  });
  table.append(body);
  const foot = document.createElement('p'); foot.className = 'chart-note';
  foot.textContent = 'Les coupons indiqués sont accumulés, pas versés à chaque date. À maturité, leur paiement dépend du seuil final.';
  calendar.append(h, table, foot);

  const chart = document.createElement('div'); chart.className = 'card chart-card';
  const markers = [{x: data.niveaux.coupon, label: hasAutocall ? 'Rappel / coupon final' : 'Coupon final', color: '#5cc8ff'}];
  if (data.niveaux.protection !== null) markers.push({x: data.niveaux.protection, label: 'Protection', color: '#ff5c5c'});
  chart.innerHTML = renderChart(data.ST_grid, [{key:'payoff', values:data.payoff}, {key:'pnl', values:data.pnl}], [], {
    labels: {payoff: 'Remboursement à maturité', pnl: 'Gain ou perte vs montant investi'},
    xLabel: 'Prix du sous-jacent à maturité (même unité que le spot)', markers,
  });
  const chartNote = document.createElement('p'); chartNote.className = 'chart-note';
  chartNote.textContent = 'Cas sans rappel avant maturité. Tous les coupons accumulés sont payés si le seuil final est atteint, sinon aucun. Montants non actualisés ; gain ou perte par rapport au nominal investi.';
  chart.append(chartNote);
  $('phx-results').replaceChildren(result.firstElementChild, chart, card, calendar);
}
```

Contrairement au Phoenix, cet affichage est construit élément par élément (`createElement`, `textContent`). Les deux façons fonctionnent ; celle-ci est plus longue mais n'insère jamais de texte comme du HTML.

- `hasAutocall` : `data.has_autocall !== false` ; l'affichage s'adapte selon que le rappel est actif ou non.
- **Carte de synthèse** : titre, intervalle de confiance, nombre de simulations, écart entre prix de souscription et valeur ; la règle des coupons **accumulés** (payés au rappel, ou tous à maturité si le seuil final est atteint, sinon aucun) ; le remboursement moyen en cas de perte, ou « Aucune perte de capital dans les simulations ».
- **Calendrier** : pour chaque date, le coupon **accumulé** (`coupon × (i + 1)` : à la 3ᵉ date, trois coupons sont en jeu) et la probabilité de rappel, ou « Maturité », « Désactivé », « Non autorisé » (avant le premier rappel autorisé). La note rappelle que ces coupons ne sont pas versés à chaque date.
- **Graphique** : une ligne pour le seuil de rappel / coupon final et une pour la protection si elle existe ; la note explique que les montants ne sont pas actualisés.
- `$('phx-results').replaceChildren(...)` : remplace d'un coup tout le contenu de la colonne de résultats par les quatre blocs, dans l'ordre voulu.

### 66. Athéna : recherche de ticker et protection

```js
brancherRechercheTicker({
  inputId: 'ac-plain-ticker', resultsId: 'ac-plain-suggestions', statusId: 'ac-plain-market-status',
  onSelect: (symbol, status) => chargerMarche(symbol, status, data => {
    ac('s0').value = data.S0;
    setVolMarche('ac-plain', data);
  }, formAutocall.querySelector('button[type=submit]')),
});
wireSigma('ac-plain');
ac('protection').addEventListener('change', () => { ac('ki').disabled = !ac('protection').checked; });
```

- Le ticker remplit le spot caché et les vols ; puis `wireSigma('ac-plain')`.
- Décocher la protection désactive le champ de la barrière de protection.

### 67. Athéna : cohérence des dates

```js
function verifierDatesAutocall() {
  verifierMaturite('ac-plain-months', 'ac-plain-freq');
  ac('first').setCustomValidity(!ac('autocall').checked || Number(ac('first').value) <= Number(ac('months').value)
    ? '' : 'Le premier rappel ne peut pas être après la maturité.');
}
for (const champ of ['freq', 'months', 'first']) ac(champ).addEventListener('input', verifierDatesAutocall);
```

- Maturité multiple de la période (même fonction `verifierMaturite` que le Phoenix, sans zone d'aide).
- Le premier rappel ne peut pas être après la maturité (vérifié seulement si le rappel est actif).
- Rappelée à chaque saisie de la fréquence, de la maturité ou du premier rappel.

### 68. `updateAutocall()` — rappel actif ou non

```js
function updateAutocall() {
  const enabled = ac('autocall').checked;
  ac('first').disabled = !enabled;
  ac('first').parentElement.hidden = !enabled;
  document.querySelector('label[for="ac-plain-barrier"]').textContent = enabled ? 'Rappel et coupon final (%)' : 'Seuil du coupon final (%)';
  ac('rules').textContent = enabled
    ? 'Coupons accumulés payés au rappel ; à maturité, tous les coupons uniquement si le seuil final est atteint. Les barrières sont exprimées en % du spot initial.'
    : 'Sans rappel : paiement à maturité. Tous les coupons accumulés si le seuil final est atteint, sinon aucun. La protection du capital reste indépendante.';
  ++versionStructure;
  $('phx-results').innerHTML = '<div class="empty">Paramètres modifiés. Lance un calcul pour voir les résultats.</div>';
  ac('status').textContent = '';
  verifierDatesAutocall();
}
ac('autocall').addEventListener('change', updateAutocall);
updateAutocall();
```

- Sans rappel : le champ du premier rappel est désactivé **et** caché, et la barrière est renommée « Seuil du coupon final » (sans rappel, elle ne sert plus qu'à ça).
- Le texte des règles change selon le cas.
- `++versionStructure` et résultats vidés : les règles ont changé, un résultat affiché ou en cours de calcul ne correspond plus au formulaire.
- Puis revérification des dates ; appelée au changement de la case et une fois au chargement.

### 69. Athéna : le calcul

```js
surSoumission(formAutocall, ac('status'), async () => {
  const version = versionStructure;
  const payload = {
    produit: 'autocall_plain', S0: ac('s0').value, r: ac('r').value, q: ac('q').value, sigma: lireSigma('ac-plain'),
    nominal: ac('nominal').value, T: Number(ac('months').value) / 12, frequence: ac('freq').value,
    coupon: ac('coupon').value, K_auto: ac('barrier').value, protection: ac('protection').checked,
    B_pdi: ac('ki').value, n_simulations: ac('nsims').value, step_down: ac('step-down').value,
    has_autocall: ac('autocall').checked,
  };
  payload.first_call_months = payload.has_autocall ? ac('first').value : 0;
  $('phx-results').innerHTML = '<div class="empty">Calcul en cours…</div>';
  try {
    const data = await appelApi('/api/autocall', {payload});
    if (version !== versionStructure) return;
    afficherAutocall(data);
    appendExtras('phx-results', data);
    return 'Calcul terminé.';
  } catch (err) {
    if (version === versionStructure) $('phx-results').innerHTML = '<div class="empty">Vérifiez les paramètres et relancez le calcul.</div>';
    throw err;
  }
}, {avant: verifierDatesAutocall, attente: 'Calcul Monte Carlo en cours…'});
```

- `produit: 'autocall_plain'` : le serveur vérifie qu'il s'agit bien de ce produit.
- `K_auto: ac('barrier').value` : le même champ sert de barrière de rappel et de seuil du coupon final.
- `first_call_months` : le premier rappel en mois, ou 0 si le rappel est désactivé.
- Pendant le calcul, la colonne affiche « Calcul en cours… ».
- Réponse arrivée trop tard : ignorée. Sinon : affichage, puis flux et export PDF.
- En cas d'erreur : si elle concerne toujours le calcul affiché, on remplace les résultats par une invitation à vérifier les paramètres, puis on **relance** l'erreur (`throw err`) pour que `surSoumission` affiche son message en rouge.
- `avant: verifierDatesAutocall` : revérifier les dates juste avant l'envoi.

### 70. Chantier : les courbes et les dates

```js
// -------- Chantier : volatilité historique et séries chronologiques --------
const volCurves = [
  {key:'series_20', label:'20 séances', color:'var(--cyan)'},
  {key:'series_60', label:'60 séances', color:'var(--amber)'},
  {key:'series_ewma', label:'EWMA', color:'var(--green)'},
  {key:'series_parkinson_20', label:'Parkinson · 20 séances', color:'var(--yellow)'},
];
const volDate = x => new Date(x + 'T00:00:00Z').toLocaleDateString('fr-FR', {timeZone:'UTC'});
```

- `volCurves` : les quatre courbes à tracer (clé de la réponse serveur, libellé, couleur). Le graphique, la légende et la validation lisent tous cette liste : ajouter une mesure = une ligne.
- `volDate` : affiche une date ISO (« 2024-03-15 ») à la française. `'T00:00:00Z'` et `timeZone:'UTC'` : on lit et on affiche la date en UTC ; sans cela, à Paris, minuit UTC peut devenir la veille à 23 h selon le fuseau et l'heure d'été.

### 71. `validateVolatility()` — vérifier la réponse avant de tracer

```js
function validateVolatility(data) {
  const n = data.dates?.length;
  const metrics = [data.vol_historique, data.vol_20, data.vol_60, data.vol_ewma, data.vol_parkinson];
  if (!n || !Array.isArray(data.dates) ||
      !volCurves.every(curve => Array.isArray(data[curve.key]) && data[curve.key].length === n) ||
      ![...metrics, ...volCurves.flatMap(curve => data[curve.key] || [])].every(v => typeof v === 'number' && Number.isFinite(v) && v >= 0) ||
      !data.dates.every((d, i) => typeof d === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(d) && Number.isFinite(Date.parse(d)) && (!i || d > data.dates[i-1]))) {
    throw new Error('Données de volatilité absentes ou incohérentes. Essayez une période plus longue.');
  }
  return data;
}
```

**Problème rencontré :** avec une période courte ou un ticker peu liquide, Yahoo renvoyait parfois des séries vides, de longueurs différentes ou avec des trous ; le graphique plantait ou affichait n'importe quoi.

Le code vérifie, avant tout tracé :
- qu'il y a des dates (`data.dates?.length` : `?.` évite une erreur si `dates` est absent) ;
- que chaque courbe est une liste de **même longueur** que les dates ;
- que tous les indicateurs et tous les points sont des nombres finis et positifs ;
- que chaque date a le format `AAAA-MM-JJ`, est une vraie date, et que les dates sont **strictement croissantes** (comparer deux dates ISO comme du texte suffit : l'ordre alphabétique est l'ordre chronologique).

Sinon : un message qui dit quoi faire (« Essayez une période plus longue »).

### 72. `renderVolatilityChart()` — le graphique interactif

```js
function renderVolatilityChart(data) {
  const W=760, H=340, L=64, R=20, T=30, B=48;
  const times = data.dates.map(d => Date.parse(d));
  const span = times.at(-1) - times[0];
  const max = Math.max(...volCurves.flatMap(curve => data[curve.key]), 1) * 1.12;
  const x = i => span ? L + (times[i]-times[0])/span*(W-L-R) : (L+W-R)/2;
  const y = v => H - B - v/max*(H-T-B);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('tabindex', '0');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Volatilités annualisées : 20 séances, 60 séances, EWMA et Parkinson sur 20 séances. Flèches gauche et droite pour parcourir les dates.');
  let markup = '<title>Volatilité glissante annualisée</title>';
  for (let i=0; i<=4; i++) {
    const v = max*i/4, py = y(v);
    markup += `<line x1="${L}" x2="${W-R}" y1="${py}" y2="${py}" stroke="var(--line)"/><text x="${L-8}" y="${py+4}" text-anchor="end">${v.toFixed(1)} %</text>`;
  }
  for (const i of [...new Set([0, Math.floor((times.length-1)/2), times.length-1])]) {
    markup += `<text x="${x(i)}" y="${H-22}" text-anchor="${i===0?'start':i===times.length-1?'end':'middle'}">${volDate(data.dates[i])}</text>`;
  }
  for (const curve of volCurves) {
    const values = data[curve.key], color = curve.color;
    const path = values.map((v,i) => `${i?'L':'M'}${x(i).toFixed(2)},${y(v).toFixed(2)}`).join(' ');
    markup += `<path d="${path}" fill="none" stroke="${color}" stroke-width="2"/>`;
    if (values.length === 1) markup += `<circle cx="${x(0)}" cy="${y(values[0])}" r="3" fill="${color}"/>`;
  }
  markup += `<line id="vol-cursor" y1="${T}" y2="${H-B}" stroke="var(--muted)" stroke-dasharray="4 4" hidden/>
    ${volCurves.map((curve,i) => `<circle id="vol-dot${i}" r="4" fill="${curve.color}" hidden/>`).join('')}`;
  svg.innerHTML = markup;
  const note = document.createElement('p'); note.className = 'chart-note'; note.setAttribute('aria-live', 'polite');
  let index = times.length - 1;
  function show(i) {
    index = i;
    const cursor = svg.querySelector('#vol-cursor'); cursor.removeAttribute('hidden');
    cursor.setAttribute('x1', x(i)); cursor.setAttribute('x2', x(i));
    for (const [j, curve] of volCurves.entries()) {
      const dot = svg.querySelector('#vol-dot' + j); dot.removeAttribute('hidden');
      dot.setAttribute('cx', x(i)); dot.setAttribute('cy', y(data[curve.key][i]));
    }
    note.textContent = volDate(data.dates[i]) + ' · ' + volCurves.map(curve => curve.label + ' : ' + fmtPct(data[curve.key][i])).join(' · ');
  }
  svg.addEventListener('pointermove', e => {
    const point = svg.createSVGPoint(); point.x = e.clientX; point.y = e.clientY;
    const px = point.matrixTransform(svg.getScreenCTM().inverse()).x;
    let nearest = 0;
    for (let i=1; i<times.length; i++) if (Math.abs(x(i)-px) < Math.abs(x(nearest)-px)) nearest = i;
    show(nearest);
  });
  svg.addEventListener('keydown', e => {
    if (!['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) return;
    e.preventDefault();
    show(e.key==='Home' ? 0 : e.key==='End' ? times.length-1 : Math.max(0, Math.min(times.length-1, index + (e.key==='ArrowRight' ? 1 : -1))));
  });
  show(index);
  return {svg, note};
}
```

Contrairement à `renderChart`, l'axe horizontal est le **temps**, et le graphique est interactif (curseur à la souris et au clavier). Il est donc construit comme un **élément** SVG, pas comme du texte.

**Le repère**
- `times` : les dates en millisecondes. L'abscisse est **proportionnelle au temps**, pas à l'indice : un week-end ou un jour férié laisse un écart réel.
- `max` : la plus haute vol (au moins 1), plus 12 % de marge.
- `x(i)` et `y(v)` : changements d'échelle ; si toutes les dates sont identiques (`span` nul), on centre le point.
- `document.createElementNS('http://www.w3.org/2000/svg', 'svg')` : un élément SVG doit être créé dans **l'espace de noms SVG** (`createElement('svg')` créerait un élément HTML inconnu, qui ne dessine rien).
- `tabindex="0"` : le graphique peut recevoir le focus clavier ; `aria-label` le décrit et explique les touches.

**Le dessin**
- 5 graduations horizontales en %.
- 3 dates en abscisse : la première, celle du milieu et la dernière (`new Set` supprime les doublons quand il y a peu de dates).
- Une courbe par mesure ; s'il n'y a qu'un point, un petit cercle (un chemin d'un seul point est invisible).
- Le curseur vertical et un point par courbe, cachés au départ.

**L'interaction**
- `show(i)` : place le curseur et les points sur la date `i` et écrit les valeurs dans la note (`aria-live` : lue par les lecteurs d'écran).
- `pointermove` : convertit la position de la souris en coordonnées du SVG (`getScreenCTM().inverse()` défait l'agrandissement du `viewBox`) puis cherche la date la plus proche.
- `keydown` : flèches gauche/droite (date précédente/suivante, sans sortir des bornes), Début/Fin (première/dernière date) ; `preventDefault()` empêche la page de défiler.
- `show(index)` au départ : on affiche la dernière date.
- La fonction renvoie le SVG et sa note, que l'appelant place dans la carte.

### 73. Chantier : recherche de ticker

```js
const fermerRechercheVol = brancherRechercheTicker({
  inputId: 'vol-ticker', resultsId: 'vol-suggestions', statusId: 'vol-search-status',
  onSelect: () => $('vol-ticker').focus(), saisieLibre: true,
});
```

- `saisieLibre: true` : si la recherche ne trouve rien, on peut taper le symbole directement.
- `onSelect` remet simplement le focus dans le champ.
- On garde la fonction `fermer` renvoyée, pour fermer la liste au lancement du calcul.

### 74. Chantier : le calcul

```js
surSoumission($('vol-form'), $('vol-status'), async () => {
  const results = $('chantier-results');
  const ticker = $('vol-ticker').value.trim().toUpperCase(), periode = $('vol-period').value, lambda = $('vol-lambda').value;
  fermerRechercheVol();
  results.setAttribute('aria-busy', 'true');
  results.innerHTML = '<div class="empty">Calcul des volatilités…</div>';
  try {
    const data = validateVolatility(await appelApi('/api/volatility?' + new URLSearchParams({ticker, periode, lambda}), {timeout: 45000}));
    results.replaceChildren();
    const metrics = document.createElement('div'); metrics.className = 'metrics';
    for (const [label, value] of [['Historique · ' + periode, data.vol_historique], ['Glissante · 20 séances', data.vol_20], ['Glissante · 60 séances', data.vol_60], ['EWMA · λ = ' + lambda, data.vol_ewma], ['Parkinson · ' + periode, data.vol_parkinson]]) {
      const metric = document.createElement('div'); metric.className = 'metric';
      const p = document.createElement('p'); p.textContent = label;
      const strong = document.createElement('strong'); strong.textContent = fmtPct(value);
      metric.append(p, strong); metrics.append(metric);
    }
    const card = document.createElement('div'); card.className = 'card chart-card';
    const title = document.createElement('h2'); title.textContent = ticker + ' · Volatilités annualisées';
    const legend = document.createElement('p'); legend.className = 'chart-note';
    legend.innerHTML = volCurves.map(curve => `<span style="color:${curve.color}">━ ${curve.label}</span>`).join(' · ') + ' · Survolez le graphique ou utilisez les flèches.';
    const {svg, note} = renderVolatilityChart(data); card.append(title, svg, legend, note);
    const convention = document.createElement('p'); convention.className = 'chart-note';
    convention.textContent = `Parkinson indicateur : toute la période ; courbe : 20 séances. EWMA : demi-vie ${data.ewma_half_life} séances. Les courbes démarrent après 60 rendements.`;
    card.append(convention); results.append(metrics, card);
    return `${ticker} · ${data.dates.length} observations · ${volDate(data.dates[0])} au ${volDate(data.dates.at(-1))}`;
  } catch (err) {
    results.innerHTML = '<div class="empty">Calcul indisponible. Vérifiez le ticker ou la période et réessayez.</div>';
    throw err;
  } finally {
    results.setAttribute('aria-busy', 'false');
  }
}, {attente: 'Récupération des données de marché…'});
```

- Le ticker est mis en majuscules ; la liste de suggestions est fermée ; `aria-busy` passe à vrai et un message d'attente s'affiche.
- `new URLSearchParams({ticker, periode, lambda})` : construit `ticker=AAPL&periode=1y&lambda=0.94` en encodant correctement chaque valeur. C'est un GET : rien n'est modifié côté serveur.
- Délai de 45 s : la récupération de 5 ans d'historique peut être lente.
- `validateVolatility(await appelApi(...))` : on vérifie **avant** d'afficher.
- Cinq indicateurs (historique sur la période, glissantes 20 et 60 séances, EWMA, Parkinson), construits avec `textContent`.
- La carte du graphique : titre, SVG, légende colorée, note interactive et rappel des conventions (fenêtre de Parkinson, demi-vie de l'EWMA renvoyée par le serveur, démarrage des courbes).
- En cas d'erreur : un message dans la colonne de résultats, et l'erreur est relancée pour `surSoumission`.
- `finally` : `aria-busy` repasse à faux dans tous les cas.
- Le message de succès donne le nombre d'observations et la période couverte.

### 75. `appendExtras()` — flux par date et export PDF

```js
// -------- Tableau des flux par date et export PDF --------
// Export d'un instantané serveur : les changements de formulaire ne modifient pas ce PDF.
function appendExtras(target, data) {
  const panel = $(target);
  if (data.flux_attendus_par_date) {
    const rows = data.obs_dates.map((t, i) => `<tr><td>${fmt(t)}</td><td>${data.barrieres_rappel_pct && i < data.obs_dates.length-1 ? fmtPct(data.barrieres_rappel_pct[i]) : '—'}</td><td>${fmt(data.flux_attendus_par_date[i])}</td><td>${fmt(data.flux_attendus_actualises_par_date[i])}</td></tr>`).join('');
    panel.insertAdjacentHTML('beforeend', `<div class="card chart-card"><h2>Flux attendus par date</h2><table class="greeks-table"><thead><tr><th>Années</th><th>Seuil rappel (%)</th><th>Flux moyen</th><th>Flux actualisé</th></tr></thead><tbody>${rows}</tbody></table><p class="hint">Moyennes sur toutes les trajectoires, y compris celles sans paiement. La somme des flux actualisés retrouve la valeur théorique.</p></div>`);
  }
  if (!data.calculation_id) return;
  const button = document.createElement('button'); button.type = 'button'; button.className = 'primary'; button.textContent = 'Exporter ce calcul en PDF';
  button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      // réponse binaire (PDF) : appel direct à fetch, pas de JSON en cas de succès
      const response = await fetch('/api/export_pdf', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({calculation_id: data.calculation_id})});
      if (!response.ok) { const error = await response.json(); throw new Error(error.error); }
      const url = URL.createObjectURL(await response.blob());
      const a = document.createElement('a'); a.href = url; a.download = 'dernier_calcul.pdf'; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      button.textContent = e.message;
    } finally {
      button.disabled = false;
    }
  });
  panel.append(button);
}
```

Appelée après **chaque** calcul, quel que soit l'onglet.

**Tableau des flux attendus** (si la réponse en contient) : une ligne par date avec le seuil de rappel (« — » pour la dernière date, ou s'il n'y en a pas), le flux moyen et le flux actualisé. La note rappelle la propriété qui sert de **contrôle** : la somme des flux actualisés retrouve la valeur théorique. Si ce n'est pas le cas, il y a un bug.

**Export PDF**
- `if (!data.calculation_id) return;` : pas d'identifiant, pas de bouton.
- **Principe de l'instantané :** le serveur garde en mémoire le calcul (paramètres et résultats) sous un identifiant. Le bouton envoie **cet identifiant**, pas le contenu du formulaire : si l'utilisateur modifie ensuite un champ, le PDF reste celui du calcul affiché. Avant, le PDF relisait le formulaire, et pouvait mélanger des résultats anciens avec des paramètres nouveaux.
- Ici on appelle `fetch` directement, pas `appelApi` : en cas de succès, la réponse est un **fichier binaire**, pas du JSON. En cas d'erreur, le serveur renvoie du JSON, lu pour obtenir le message.
- `URL.createObjectURL(await response.blob())` : transforme le PDF reçu en une adresse locale temporaire ; un lien `<a download="dernier_calcul.pdf">` créé à la volée et « cliqué » par le code déclenche le téléchargement.
- `setTimeout(() => URL.revokeObjectURL(url), 1000)` : libère la mémoire du fichier une seconde plus tard (le temps que le téléchargement démarre).
- En cas d'erreur, le texte du bouton affiche le message ; `finally` réactive le bouton.

## Partie 5 — fin de la page

### 76. Fin de la page

```html
</script>
</body>
</html>
```

- `</script></body></html>` : fin du JavaScript et du document.
- **Pourquoi le script est-il à la fin ?** Le navigateur lit la page de haut en bas. Placé à la fin, le script s'exécute quand tous les éléments HTML existent déjà : `$('opt-s0')` les trouve. En haut de page, il faudrait attendre l'événement `DOMContentLoaded`.

---

## Exercices

1. Ajoutez une stratégie « butterfly » côté page : quelles lignes faut-il toucher ? (Indice : `STRAT_FIELDS`, `STRAT_LABELS`, la liste HTML ; le serveur doit aussi la connaître.)
2. Dans `brancherRechercheTicker`, supprimez le test `maVersion !== version`, tapez vite « A », « AA », « AAPL » avec un réseau lent (outils de développement → Network → Slow 3G) : que voit-on ?
3. Supprimez la règle CSS `[hidden]{display:none !important}` : quels éléments réapparaissent alors qu'ils devraient être cachés ? Pourquoi ?
4. Pourquoi `bindStrikeBounds` utilise-t-il `Math.ceil` pour la borne basse et `Math.floor` pour la borne haute ?
