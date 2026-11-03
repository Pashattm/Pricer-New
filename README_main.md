# `main.py` — le serveur Flask

`main.py` est la porte d'entrée du pricer. Pour chaque requête, il :

1. reçoit les paramètres envoyés par `index.html` (JSON) ;
2. les confie à `validation.py`, qui les lit, les convertit et les vérifie ;
3. appelle le bon moteur ;
4. **met en forme** la réponse (arrondis, montants × nominal, grille du graphe) ;
5. mémorise le calcul pour l'export PDF.

Lancement : `python main.py`, puis <http://127.0.0.1:5000>.

**Pourquoi Flask ?** C'est le micro-framework web Python le plus simple : une route = une fonction décorée par `@app.post("/api/...")`. Django serait surdimensionné (base de données, administration…) ; FastAPI est excellent mais ajoute des notions (typage Pydantic, asynchrone) qui ne servent pas ici.

**Comment lire une route ?** Chaque route tient en quelques lignes : **lire les paramètres → calculer → répondre**. Les contrôles sont dans `validation.py`, les erreurs sont gérées une seule fois pour tout le serveur.

**Deux notions Python utilisées partout :**
- un **décorateur** (`@app.get("/")`, `@app.post(...)`, `@app.errorhandler(...)`) est une ligne placée au-dessus d'une fonction pour l'enregistrer auprès de Flask : « quand le navigateur demande cette adresse, appelle cette fonction » ;
- `**dictionnaire` à l'intérieur d'un autre dictionnaire recopie toutes ses clés : `{**a, "x": 1}` = toutes les clés de `a`, plus `x`.

---

# Le code, ligne par ligne
### 1. En-tête du fichier

```python
"""Serveur Flask du pricer.

Rôle de chaque fichier :
- main.py (ici) : reçoit les requêtes du site, appelle validation.py,
  appelle le moteur et met en forme la réponse JSON ;
- validation.py : lit, convertit (% -> décimal) et vérifie les paramètres ;
- *_engine.py : les calculs, sur des paramètres déjà propres.

Lancement : python main.py puis http://127.0.0.1:5000
"""
```

- Elle décrit le **rôle de chaque fichier** : `main.py` reçoit et répond, `validation.py` vérifie, les fichiers `*_engine.py` calculent. C'est la carte du projet.
- Dernière ligne : comment lancer le serveur.

### 2. Imports

```python
import json
from collections import OrderedDict
from datetime import datetime, timezone
from io import BytesIO
from threading import RLock
from time import monotonic
from uuid import uuid4

import numpy as np
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.exceptions import HTTPException

from pricer_engine import (
    black_scholes, monte_carlo, longstaff_schwartz,
    grecs_primaires_bs, grecs_secondaires_bs,
    forward_price, forward_value, forward_payoff,
    payoff_strategie, greeks_strategie,
    make_covered_call, make_protective_put, make_straddle, make_strangle,
    make_call_spread, make_put_spread, make_collar,
    digital_bs, asset_or_nothing_bs, grecs_digital_bs, digital_monte_carlo,
)
from strutu_engine import (
    analyse_phoenix, analyse_autocall_plain,
    calculer_remboursement_phoenix_maturite, calculer_remboursement_autocall_maturite,
)
from market_data_engine import search_tickers, get_cotation, get_vix, get_vol_historique, get_volatility_snapshot
import validation as v
```

**Bibliothèque standard** (installée avec Python) :
- `json` : vérifier qu'une réponse est un JSON valide (aucun `NaN`).
- `OrderedDict` : un dictionnaire qui garde l'ordre d'insertion ; sert au cache des calculs pour le PDF.
- `datetime, timezone` : horodater un calcul en UTC.
- `BytesIO` : un « fichier » en mémoire, pour envoyer le PDF sans l'écrire sur le disque.
- `RLock` : un verrou, pour que deux requêtes simultanées ne modifient pas le cache en même temps.
- `monotonic` : une horloge qui ne recule jamais (pour mesurer l'âge d'un calcul).
- `uuid4` : un identifiant aléatoire impossible à deviner.

**Bibliothèques installées :**
- `numpy as np` : calculs sur les grilles du graphe.
- `from flask import ...` : `Flask` (l'application), `render_template` (servir la page HTML), `request` (la requête reçue), `jsonify` (fabriquer une réponse JSON), `send_file` (envoyer un fichier).
- `HTTPException` : le type des erreurs HTTP de Flask (404, 405, 413…).

**Fichiers du projet :**
- `from pricer_engine import (...)` : les fonctions de pricing utilisées par les routes, dont les constructeurs de stratégies (`make_covered_call`…). Les parenthèses permettent d'écrire la liste sur plusieurs lignes.
- `from strutu_engine import (...)` : les analyses Phoenix et Athéna, et les deux fonctions de remboursement à maturité utilisées pour les graphes.
- `from market_data_engine import ...` : recherche de ticker, cotation, VIX, volatilités.
- `import validation as v` : les routes écrivent `v.parametres_option(...)`, court et explicite.

Tous les imports sont **en tête de fichier** : on voit d'un coup d'œil de quoi dépend le serveur.

### 3. Création de l'application

```python
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2_000_000   # un formulaire fait quelques kilo-octets
```

- `app = Flask(__name__)` : crée l'application. `__name__` (le nom du module) permet à Flask de trouver le dossier `templates/` à côté du fichier.
- `app.config['MAX_CONTENT_LENGTH'] = 2_000_000` : requêtes limitées à 2 Mo. Un formulaire de pricer fait quelques kilo-octets ; cette limite protège contre un envoi énorme qui saturerait la mémoire. Au-delà, Flask lève une erreur 413, traduite plus bas en message lisible.

### 4. `_err()` — format unique des erreurs

```python
def _err(message, code=400):
    """Renvoie une erreur au site (affichée en rouge sous le bouton)."""
    return jsonify({"error": message}), code
```

- La bannière `# === Fonctions utiles partout ===` ouvre la section des utilitaires.
- `return jsonify({"error": message}), code` : une route Flask peut renvoyer un couple (contenu, code HTTP). Code 400 par défaut (erreur de l'utilisateur).
- **Un seul format pour tout le serveur** : le navigateur sait toujours où lire le message (`data.error`) et l'affiche en rouge sous le bouton.

### 5. `_grid()` — grille de prix finaux pour les graphes

```python
def _grid(centres, n_points=121, low=0.4, high=1.6, sauts=()):
    """Grille de prix finaux S_T pour les graphes.

    Je vais de min(centres) x low à max(centres) x high, avec n_points points.
    sauts : niveaux où le payoff fait une marche (strike d'une digitale,
    barrières d'un structuré).
    J'ajoute le niveau et ses deux voisins
    flottants immédiats pour que le graphe montre une vraie marche verticale.
    """
    points = list(np.linspace(max(0.01, min(centres) * low), max(centres) * high, n_points))
    for x in sauts:
        points.extend([np.nextafter(x, -np.inf), x, np.nextafter(x, np.inf)])
    return np.unique(points)
```

- **Paramètres** : `centres` (les niveaux intéressants : spot, strikes, barrières), `n_points` (121 par défaut : assez pour une courbe lisse, assez peu pour un JSON léger), `low` et `high` (de 40 % du plus bas à 160 % du plus haut par défaut), `sauts`.
- `points = list(np.linspace(max(0.01, min(centres) * low), max(centres) * high, n_points))` : `np.linspace(a, b, n)` donne n points régulièrement espacés de a à b. `max(0.01, ...)` : un prix ne peut pas être nul ou négatif. `list(...)` permet d'ajouter des points ensuite.
- `for x in sauts: points.extend([np.nextafter(x, -np.inf), x, np.nextafter(x, np.inf)])` : le payoff d'une digitale ou d'un structuré fait une **marche** au strike ou aux barrières. Une grille régulière tombe rarement pile dessus, et le graphe dessinerait une pente. On ajoute donc le niveau et ses deux voisins flottants immédiats : `np.nextafter(x, -np.inf)` est le plus grand nombre représentable juste en dessous de x. Le graphe dessine alors une vraie marche verticale.
- `return np.unique(points)` : `np.unique` trie et retire les doublons.

### 6. `_find_breakevens()` — points morts

```python
def _find_breakevens(ST_grid, pnl):
    """Trouve les breakevens : les points où le P&L change de signe.

    Il peut y en avoir plusieurs (straddle, strangle...). J'interpole à la main
    parce que np.interp veut des valeurs croissantes, et le P&L peut très bien
    descendre : ça me donnait un résultat faux sans message d'erreur.
    """
    breakevens = []
    signs = np.sign(pnl)
    for i in range(len(signs) - 1):
        if signs[i] != signs[i + 1] and signs[i] != 0 and signs[i + 1] != 0:
            be = ST_grid[i] + (0 - pnl[i]) * (ST_grid[i + 1] - ST_grid[i]) / (pnl[i + 1] - pnl[i])
            breakevens.append(round(float(be), 2))
    return breakevens
```

- `breakevens = []` : la liste résultat ; il peut y avoir plusieurs points morts (un straddle en a deux).
- `signs = np.sign(pnl)` : −1, 0 ou +1 selon le signe du P&L en chaque point.
- `for i in range(len(signs) - 1):` : on compare chaque point au suivant.
- `if signs[i] != signs[i + 1] and signs[i] != 0 and signs[i + 1] != 0:` : le P&L **change de signe** entre deux points. On exclut les zéros exacts pour ne pas compter deux fois le même point mort.
- `be = ST_grid[i] + (0 - pnl[i]) * (ST_grid[i + 1] - ST_grid[i]) / (pnl[i + 1] - pnl[i])` : **interpolation linéaire** entre les deux points pour trouver le zéro exact (règle de trois sur le segment).
- `breakevens.append(round(float(be), 2))` : arrondi à 2 décimales.
- **Problème rencontré :** la première version utilisait `np.interp(0, pnl, ST_grid)`. Or `np.interp` exige des abscisses **croissantes**. Pour un put ou un short call, le P&L décroît : le résultat était faux **sans aucun message d'erreur**. D'où l'interpolation écrite à la main.

### 7. `_arrondi()` — alléger le JSON

```python
def _arrondi(valeurs, chiffres=4):
    """Arrondit une liste (ou un tableau numpy) pour alléger le JSON."""
    return [round(float(x), chiffres) for x in valeurs]
```

- `return [round(float(x), chiffres) for x in valeurs]` : transforme une liste ou un tableau NumPy en liste de nombres Python arrondis à 4 décimales. `float(x)` est nécessaire car `jsonify` ne sait pas toujours convertir les nombres NumPy.

### 8. `_pct()` — fraction → pourcentage

```python
def _pct(x):
    """Fraction du nominal -> pourcentage arrondi (0.9712 -> 97.12)."""
    return None if x is None else round(100 * float(x), 4)
```

- `return None if x is None else round(100 * float(x), 4)` : `0.9712` devient `97.12`. `None` reste `None` (par exemple, le remboursement moyen si perte quand aucune perte n'a été simulée).
- **Convention de nommage tenue dans tout le fichier :** un champ qui finit par `_pct` est en %, un champ sans suffixe est en devise du nominal.

### 9. `_reponse_graphe()` — partie « graphe » des réponses

```python
def _reponse_graphe(ST_grid, payoff, pnl, breakevens=True):
    """Partie commune des réponses avec un graphe payoff / P&L."""
    reponse = {"ST_grid": _arrondi(ST_grid), "payoff": _arrondi(payoff), "pnl": _arrondi(pnl)}
    if breakevens:
        reponse["breakevens"] = _find_breakevens(ST_grid, pnl)
    return reponse
```

- `reponse = {...}` : les trois listes du graphe, arrondies.
- `if breakevens:` : les points morts sont calculés par défaut. Le Phoenix passe `breakevens=False` : son « P&L » à maturité n'a pas de sens sans les coupons déjà versés.
- Utilisée par les options, le forward, les stratégies et le Phoenix.

### 10. `_reponse_structure()` — indicateurs communs aux produits structurés

```python
def _reponse_structure(res, nominal):
    """Indicateurs communs au Phoenix et à l'Autocall : montants en devise, _pct en %."""
    return {
        "prix": round(res["prix"] * nominal, 4),
        "prix_pct": _pct(res["prix"]),
        "erreur_type": round(res["erreur_type"] * nominal, 6),
        "ic95_pct": [_pct(x) for x in res["ic95"]],
        "marge_emetteur_pct": _pct(res["marge_emetteur"]),
        "duree_de_vie_moyenne": round(res["duree_de_vie_moyenne"], 4),
        "coupons_moyens_actualises_pct": _pct(res["coupons_moyens_actualises"]),
        "obs_dates": res["obs_dates"],
        "proba_rappel_par_date_pct": [_pct(p) for p in res["proba_rappel_par_date"]],
        "proba_maturite_pct": _pct(res["proba_maturite"]),
        "proba_perte_capital_pct": _pct(res["proba_perte_capital"]),
        "remboursement_moyen_si_perte_pct": _pct(res["remboursement_moyen_si_perte"]),
        "flux_attendus_par_date": [x * nominal for x in res["flux_attendus_par_date"]],
        "flux_attendus_actualises_par_date": [x * nominal for x in res["flux_attendus_actualises_par_date"]],
    }
```

- `res` : le résultat d'`analyse_phoenix` ou d'`analyse_autocall_plain`, en **fraction du nominal**.
- `"prix": round(res["prix"] * nominal, 4)` : la valeur théorique en devise ; `"prix_pct"` : la même en %.
- `"erreur_type"` en devise, `"ic95_pct"` en % : la précision Monte Carlo.
- `"marge_emetteur_pct"` : 100 % − valeur théorique.
- `"duree_de_vie_moyenne"` (années), `"coupons_moyens_actualises_pct"`, `"obs_dates"`.
- `"proba_rappel_par_date_pct"`, `"proba_maturite_pct"`, `"proba_perte_capital_pct"`, `"remboursement_moyen_si_perte_pct"` : les probabilités, converties une à une avec `_pct` (compréhension de liste pour les listes).
- `"flux_attendus_par_date"` et `"..._actualises_par_date"` : les paiements moyens à chaque date, multipliés par le nominal.
- **Pourquoi une fonction commune ?** Ces quinze champs étaient construits deux fois, avec des différences (un produit renvoyait `erreur_type`, l'autre non ; la marge existait sous deux noms). Une seule fonction = mêmes clés, mêmes arrondis.

### 11. `erreur_parametre()` — erreurs de paramètres

```python
@app.errorhandler(ValueError)
def erreur_parametre(erreur):
    """Toute ValueError (validation.py ou moteur) devient une erreur 400 lisible."""
    return _err(str(erreur))
```

- La bannière `# === Erreurs : un seul endroit pour toutes les routes ===` ouvre la section.
- `@app.errorhandler(ValueError)` : Flask appelle cette fonction **chaque fois qu'une `ValueError` remonte d'une route**, qu'elle vienne de `validation.py` ou d'un moteur.
- `return _err(str(erreur))` : le message de l'erreur devient une réponse 400. C'est pour cela que les routes n'ont aucun `try / except` : avant, chaque route avait son propre bloc, avec des messages légèrement différents.

### 12. `erreur_inattendue()` — toutes les autres erreurs

```python
@app.errorhandler(Exception)
def erreur_inattendue(erreur):
    """Erreur imprévue : message générique, sans détail Python interne (500).

    Les erreurs HTTP de Flask (404, 405, 413...) gardent leur code.
    """
    if isinstance(erreur, HTTPException):
        if erreur.code == 413:
            return _err("Requête limitée à 2 Mo.", 413)
        if erreur.code == 404:
            return _err("Route inconnue.", 404)
        return _err(erreur.description, erreur.code)
    return _err("Le calcul a échoué. Vérifiez les paramètres et réessayez.", 500)
```

- `@app.errorhandler(Exception)` : attrape toute autre erreur.
- `if isinstance(erreur, HTTPException):` : les erreurs HTTP de Flask gardent leur code. 413 (requête trop grosse) et 404 (adresse inconnue : « Route inconnue. ») reçoivent un message en français ; les autres (405, mauvaise méthode…) gardent la description de Flask.
- `return _err("Le calcul a échoué. ...", 500)` : pour une erreur imprévue (un bug), on renvoie un **message générique** sans le détail Python interne, qui pourrait révéler des informations sur le serveur. Code 500 = erreur du serveur.

### 13. `index()` — la page du site

```python
@app.get("/")
def index():
    """Route GET / : affiche la page du site."""
    return render_template("index.html")
```

- La bannière ouvre la section « Page du site et configuration partagée ».
- `@app.get("/")` : l'adresse racine du site.
- `return render_template("index.html")` : renvoie `templates/index.html`. Toute l'interface est dans ce fichier ; ensuite, le serveur ne fait plus que de l'API JSON.

### 14. `api_config()` — bornes partagées avec le site

```python
@app.get("/api/config")
def api_config():
    """Bornes lues par le site : la règle des strikes n'est écrite qu'une fois."""
    return jsonify({"moneyness_min": v.MONEYNESS_MIN, "moneyness_max": v.MONEYNESS_MAX})
```

- `@app.get("/api/config")` : une route de lecture.
- `return jsonify({"moneyness_min": v.MONEYNESS_MIN, "moneyness_max": v.MONEYNESS_MAX})` : le site lit ici les bornes de strike au chargement. La règle 50 %–150 % était autrefois écrite dans `main.py` **et** dans `index.html`, avec un commentaire « penser à changer les deux ». Elle n'existe plus qu'une fois, dans `validation.py`.

### 15. `api_search_ticker()` — suggestions de tickers

```python
@app.get("/api/search_ticker")
def api_search_ticker():
    """Route GET /api/search_ticker?q=... : suggestions de tickers (liste vide si Yahoo ne répond pas)."""
    query = request.args.get("q", "").strip()
    return jsonify({"results": search_tickers(query) if query else []})
```

- La bannière ouvre la section des données de marché.
- `query = request.args.get("q", "").strip()` : `request.args` contient les paramètres de l'URL (`?q=MC`).
- `search_tickers(query) if query else []` : requête vide → liste vide, sans appel inutile à Yahoo. `search_tickers` renvoie déjà une liste vide si Yahoo ne répond pas : pas besoin de `try`.

### 16. `api_market()` — spot, devise, VIX et vol historique

```python
@app.get("/api/market/<ticker>")
def api_market(ticker):
    """Route GET /api/market/<ticker> : spot, devise, VIX et vol historique.

    Si la vol historique n'est pas dispo (ticker récent), je renvoie None et
    le site se rabat sur le VIX.
    """
    try:
        cotation = get_cotation(ticker)
        vix = get_vix()
    except Exception as e:
        return _err(f"Impossible de récupérer les données pour '{ticker}' : {e}")
    try:
        vol_hist = round(get_vol_historique(ticker), 4)
    except Exception:
        vol_hist = None
    return jsonify({"S0": round(cotation["S0"], 4), "devise": cotation["devise"],
                    "vix": round(vix, 4), "vol_hist": vol_hist})
```

- `@app.get("/api/market/<ticker>")` : `<ticker>` est une partie variable de l'adresse ; Flask la passe en argument à la fonction.
- Premier `try` : `get_cotation(ticker)` (spot et devise en une seule requête Yahoo) et `get_vix()`. En cas d'échec, un message qui cite le ticker, plus utile que le message générique.
- Second `try` : `get_vol_historique(ticker)`. **Dégradation gracieuse** : si l'historique est insuffisant (introduction en Bourse récente), la vol historique vaut `None` au lieu de faire échouer toute la requête. L'interface sélectionne alors automatiquement le VIX.
- `return jsonify({...})` : spot arrondi, devise, VIX, vol historique.

### 17. `api_volatility()` — onglet Chantier

```python
@app.get("/api/volatility")
def api_volatility():
    """Volatilités historique, glissantes, EWMA et Parkinson d'un sous-jacent.

    Exemple : /api/volatility?ticker=AAPL&periode=1y&lambda=0.94
    """
    ticker, periode, lambda_ = v.parametres_volatilite(request.args)
    return jsonify(get_volatility_snapshot(ticker, periode, lambda_))
```

- `ticker, periode, lambda_ = v.parametres_volatilite(request.args)` : validation (liste blanche des périodes, 0 < λ < 1).
- `return jsonify(get_volatility_snapshot(ticker, periode, lambda_))` : toutes les mesures de volatilité en un seul calcul.

### 18. `api_option()` — option européenne ou américaine

```python
@app.post("/api/option")
def api_option():
    """Prix, grecques et graphe d'une option.

    Européenne : Black-Scholes ou Monte Carlo (avec IC95). Américaine : Longstaff-Schwartz.
    """
    p = v.parametres_option(request.get_json())
    marche = (p["S0"], p["K"], p["T"], p["r"], p["q"], p["sigma"], p["option_type"])

    reponse = {}
    if p["style"] == "american":
        price, used = longstaff_schwartz(*marche, p["n_simulations"], seed=p["seed"]), "longstaff_schwartz"
    elif p["method"] == "monte_carlo":
        reponse["monte_carlo"] = monte_carlo(*marche, p["n_simulations"], seed=p["seed"])
        price, used = reponse["monte_carlo"]["price"], "monte_carlo"
    else:
        price, used = black_scholes(*marche), "black_scholes"

    sign = 1 if p["side"] == "buy" else -1
    ST_grid = _grid([p["S0"], p["K"]])
    payoff = sign * (np.maximum(ST_grid - p["K"], 0) if p["option_type"] == "call"
                     else np.maximum(p["K"] - ST_grid, 0))
    pnl = payoff - sign * price  # j'enlève la prime payée (ou je l'ajoute si vendeur)

    return jsonify({
        **reponse,
        "price": round(float(price), 4),
        "model_used": used,
        # grecques Black-Scholes (approximation pour l'américaine)
        "primaires": {k: round(float(x), 6) for k, x in grecs_primaires_bs(*marche).items()},
        "secondaires": {k: round(float(x), 6) for k, x in grecs_secondaires_bs(*marche).items()},
        **_reponse_graphe(ST_grid, payoff, pnl),
    })
```

- La bannière ouvre la section ; `@app.post("/api/option")` : le navigateur envoie les paramètres en POST.
- `p = v.parametres_option(request.get_json())` : `request.get_json()` lit le corps JSON ; la validation renvoie un dictionnaire propre.
- `marche = (p["S0"], p["K"], ...)` : un tuple avec les sept paramètres communs ; `*marche` les « déplie » dans chaque appel. On évite de recopier sept arguments à chaque fonction.
- `reponse = {}` : champs supplémentaires éventuels.
- **Choix du modèle :**
  - américaine → `longstaff_schwartz(*marche, p["n_simulations"], seed=p["seed"])` : pas de formule fermée pour un put américain ;
  - européenne en Monte Carlo → `monte_carlo(...)`, dont le résultat complet (prix et IC95) est gardé dans `reponse["monte_carlo"]` pour être affiché ;
  - sinon Black-Scholes.
  - `used` mémorise le modèle réellement utilisé, affiché par l'interface.
- `sign = 1 if p["side"] == "buy" else -1` : la logique de signe des positions (un vendeur encaisse la prime et a un payoff négatif).
- `ST_grid = _grid([p["S0"], p["K"]])` : la grille centrée sur le spot et le strike.
- `payoff = sign * (np.maximum(...) if call else np.maximum(...))` : le payoff à maturité sur toute la grille.
- `pnl = payoff - sign * price` : on retire la prime payée (ou on ajoute la prime encaissée si vendeur).
- `return jsonify({**reponse, "price": ..., "model_used": ..., "primaires": ..., "secondaires": ..., **_reponse_graphe(...)})` : le prix arrondi, les grecques **Black-Scholes européennes** (même pour une américaine : approximation assumée, exacte pour un call américain sans dividende) arrondies à 6 décimales, et le graphe.

### 19. `api_digital()` — digitale européenne

```python
@app.post("/api/digital")
def api_digital():
    """Prix Black-Scholes et Monte Carlo d'une digitale européenne."""
    p = v.parametres_digitale(request.get_json())
    marche = (p["S0"], p["K"], p["T"], p["r"], p["q"], p["sigma"], p["option_type"])
    prix = digital_bs(*marche, p["payout"]) if p["digital_type"] == "cash" else asset_or_nothing_bs(*marche)
    mc = digital_monte_carlo(*marche, p["n_simulations"], payout=p["payout"],
                             seed=p["seed"], digital_type=p["digital_type"])
    grecs = grecs_digital_bs(*marche, p["payout"], p["digital_type"])
    signe = 1 if p["side"] == "buy" else -1
    grille = _grid([p["S0"], p["K"]], sauts=[p["K"]])
    condition = grille > p["K"] if p["option_type"] == "call" else grille < p["K"]
    payoff = signe*condition*(p["payout"] if p["digital_type"] == "cash" else grille)
    return jsonify({"price": float(prix), "monte_carlo": mc, "model_used": "black_scholes",
                    "primaires": {cle: float(signe*x) for cle, x in grecs.items()},
                    "secondaires": {}, "breakevens": [], "ST_grid": grille.tolist(),
                    "payoff": payoff.tolist(), "pnl": (payoff-signe*prix).tolist(),
                    "strikes": [p["K"]], "digital_type": p["digital_type"]})
```

- `p = v.parametres_digitale(...)` et `marche = (...)` : comme pour une option.
- `prix = digital_bs(*marche, p["payout"]) if cash else asset_or_nothing_bs(*marche)` : le prix Black-Scholes selon le type.
- `mc = digital_monte_carlo(...)` : le prix Monte Carlo avec son IC95, pour vérifier que la formule fermée tombe dans l'intervalle.
- `grecs = grecs_digital_bs(...)` : les grecques fermées.
- `signe` : achat ou vente.
- `grille = _grid([p["S0"], p["K"]], sauts=[p["K"]])` : la marche au strike est dessinée verticalement.
- `condition = grille > p["K"]` (call) ou `< p["K"]` (put) : inégalité stricte, cohérente avec le moteur.
- `payoff = signe*condition*(payout if cash else grille)` : le paiement fixe ou la valeur de l'action, là où la condition est vraie.
- La réponse a **les mêmes clés qu'une option** (`price`, `primaires`, `secondaires`, `breakevens`, `ST_grid`…) : l'interface affiche les deux avec le même code. `"secondaires": {}` et `"breakevens": []` sont vides par construction ; les grecques sont multipliées par le signe (vendeur = grecques opposées).

### 20. `api_forward()` — forward / future

```python
@app.post("/api/forward")
def api_forward():
    """Prix à terme, valeur du contrat et graphe."""
    p = v.parametres_forward(request.get_json())
    valeur = forward_value(p["S0"], p["K"], p["T"], p["r"], p["q"], p["side"])
    ST_grid = _grid([p["S0"], p["K"]])
    payoff = forward_payoff(ST_grid, p["K"], p["side"])
    # pas de prime pour un forward, le P&L c'est payoff - valeur actuelle du contrat
    return jsonify({
        "forward_price": round(float(forward_price(p["S0"], p["T"], p["r"], p["q"])), 4),
        "valeur_actuelle": round(float(valeur), 4),
        **_reponse_graphe(ST_grid, payoff, payoff - valeur),
    })
```

- La bannière ouvre la section ; `p = v.parametres_forward(...)`.
- `valeur = forward_value(...)` : la valeur actuelle du contrat.
- `ST_grid = _grid([p["S0"], p["K"]])` et `payoff = forward_payoff(ST_grid, p["K"], p["side"])` : le payoff linéaire sur toute la grille, sans boucle.
- Le P&L est `payoff - valeur` : il n'y a pas de prime pour un forward, mais un contrat signé hors marché (K ≠ F) a déjà une valeur.
- La réponse contient le prix à terme F, la valeur du contrat et le graphe.

### 21. `STRATEGY_BUILDERS` — table des stratégies

```python
# pour chaque stratégie, la fonction qui me construit ses jambes
# (les strikes à lire sont dans validation.STRIKES_STRATEGIE)
STRATEGY_BUILDERS = {
    "covered_call":   lambda s, p: make_covered_call(s["K"], p["T"], qty=p["qty"]),
    "protective_put": lambda s, p: make_protective_put(s["K"], p["T"], qty=p["qty"]),
    "straddle":       lambda s, p: make_straddle(s["K"], p["T"], side=p["side"], qty=p["qty"]),
    "strangle":       lambda s, p: make_strangle(s["K_put"], s["K_call"], p["T"], side=p["side"], qty=p["qty"]),
    "call_spread":    lambda s, p: make_call_spread(s["K1"], s["K2"], p["T"], qty=p["qty"]),
    "put_spread":     lambda s, p: make_put_spread(s["K1"], s["K2"], p["T"], qty=p["qty"]),
    "collar":         lambda s, p: make_collar(s["K_put"], s["K_call"], p["T"], qty=p["qty"]),
}
```

- La bannière ouvre la section des stratégies ; les deux commentaires expliquent le rôle de la table.
- Un dictionnaire « nom → fonction ». Chaque valeur est une **lambda** (petite fonction anonyme d'une ligne) qui reçoit `s` (les strikes lus par la validation) et `p` (les autres paramètres), et appelle le bon constructeur de `pricer_engine`.
- **Pourquoi une table plutôt qu'une chaîne de `if / elif` ?** Ajouter une stratégie = ajouter une ligne ici et une dans `validation.STRIKES_STRATEGIE`, sans toucher à la route.

### 22. `api_strategy()` — payoff, P&L et grecques d'une stratégie

```python
@app.post("/api/strategy")
def api_strategy():
    """Payoff, P&L et grecques d'une stratégie."""
    p = v.parametres_strategie(request.get_json())
    legs = STRATEGY_BUILDERS[p["strategie"]](p["strikes"], p)
    ST_grid = _grid([p["S0"], *p["strikes"].values()])
    resultat = payoff_strategie(legs, p["S0"], p["r"], p["q"], p["sigma"], ST_grid)
    grecques = greeks_strategie(legs, p["S0"], p["r"], p["q"], p["sigma"])
    return jsonify({
        "greeks": {k: round(float(x), 6) for k, x in grecques.items()},
        **_reponse_graphe(ST_grid, resultat["payoff"], resultat["pnl"]),
        "n_legs": len(legs),
    })
```

- `p = v.parametres_strategie(...)` : le nom de la stratégie a déjà été vérifié.
- `legs = STRATEGY_BUILDERS[p["strategie"]](p["strikes"], p)` : on récupère la fonction dans la table et on l'appelle : elle renvoie la liste des jambes.
- `ST_grid = _grid([p["S0"], *p["strikes"].values()])` : la grille centrée sur le spot et tous les strikes (`*` déplie la liste des strikes).
- `resultat = payoff_strategie(...)` et `grecques = greeks_strategie(...)` : la somme signée des jambes.
- La réponse contient les grecques agrégées, le graphe et le nombre de jambes (`n_legs`, affiché sous le résultat).

### 23. `api_phoenix()` — Phoenix

```python
@app.post("/api/phoenix")
def api_phoenix():
    """Prix, stats des scénarios et graphe du Phoenix.

    Montants en devise du nominal, et en % du nominal pour les champs en _pct.
    """
    p = v.parametres_phoenix(request.get_json())
    nominal = p.pop("nominal")
    res = analyse_phoenix(**p)

    # je passe les barrières en prix pour les tracer sur le graphe
    strike_reference = p["strike_pct"] * p["S0"]
    niveaux = {
        "strike": strike_reference,
        "autocall": p["K_auto"] * strike_reference if p["has_autocall"] else None,
        "coupon": p["B_phoenix"] * strike_reference,
        "protection": p["B_pdi"] * strike_reference,
    }
    seuils = [x for x in niveaux.values() if x is not None]
    ST_grid = _grid([p["S0"], *seuils], n_points=241, low=0.6, high=1.3, sauts=seuils)

    # payoff à maturité si pas rappelé
    payoff = calculer_remboursement_phoenix_maturite(
        ST_grid, p["S0"], p["B_phoenix"], p["B_pdi"], res["coupon_schedule"][-1],
        p["strike_pct"], p["bonus_threshold"], p["bonus_amount"])["total"] * nominal
    # P&L du client : il a payé le nominal (100 %), pas le prix théorique
    return jsonify({
        **_reponse_structure(res, nominal),
        "barrieres_rappel_pct": [x*100 for x in res["barrieres_rappel"]] if p["has_autocall"] else None,
        "coupon_schedule_pct": [_pct(c) for c in res["coupon_schedule"]],
        "niveaux": {k: (None if x is None else round(float(x), 4)) for k, x in niveaux.items()},
        **_reponse_graphe(ST_grid, payoff, payoff - nominal, breakevens=False),
    })
```

- La bannière ouvre la section ; la docstring rappelle la convention : montants en devise, champs `_pct` en %.
- `p = v.parametres_phoenix(...)` : renvoie exactement les arguments du moteur, plus le nominal.
- `nominal = p.pop("nominal")` : `pop` retire le nominal du dictionnaire et le renvoie ; le moteur travaille en fraction du nominal.
- `res = analyse_phoenix(**p)` : `**p` passe chaque clé du dictionnaire comme argument nommé.
- **Niveaux pour le graphe :** `strike_reference = p["strike_pct"] * p["S0"]`, puis le dictionnaire `niveaux` convertit chaque barrière en prix (le rappel vaut `None` s'il est désactivé).
- `seuils = [x for x in niveaux.values() if x is not None]` : les niveaux à afficher.
- `ST_grid = _grid([p["S0"], *seuils], n_points=241, low=0.6, high=1.3, sauts=seuils)` : 241 points entre 60 % et 130 %, zone où se trouvent les barrières, avec une marche à chaque barrière.
- `payoff = calculer_remboursement_phoenix_maturite(...)["total"] * nominal` : remboursement à maturité **dans le cas non rappelé**, avec le dernier coupon du calendrier (`res["coupon_schedule"][-1]`), en devise.
- Le P&L du client est `payoff - nominal` : il a payé 100 % du nominal, pas le prix théorique ; c'est son vrai gain ou sa vraie perte.
- La réponse ajoute aux indicateurs communs : les barrières de rappel effectives (après step-down) en %, le calendrier de coupons en %, les niveaux arrondis, et le graphe sans breakevens.

### 24. `api_autocall()` — Athéna (Autocall Plain)

```python
@app.post("/api/autocall")
def api_autocall():
    """Entrées du formulaire en %, calculs en décimal, montants en devise du nominal."""
    p = v.parametres_autocall(request.get_json())
    nominal = p.pop("nominal")
    res = analyse_autocall_plain(**p)

    # Graphe du remboursement final, dans le cas sans rappel antérieur.
    S0, K_auto, B_pdi = p["S0"], p["K_auto"], p["B_pdi"]
    niveaux = {"autocall": K_auto * S0 if p["has_autocall"] else None,
               "coupon": K_auto * S0,
               "protection": None if B_pdi is None else B_pdi * S0}
    seuils = [x for x in niveaux.values() if x is not None]
    grille = _grid([S0, *seuils], n_points=241, low=0.6, high=1.3, sauts=seuils)
    remboursement_final = calculer_remboursement_autocall_maturite(
        grille, S0, K_auto, B_pdi, p["coupon"] * len(p["obs_dates"]))["total"] * nominal
    return jsonify({
        **_reponse_structure(res, nominal),
        "ST_grid": grille.tolist(),
        "payoff": remboursement_final.tolist(),
        "pnl": (remboursement_final - nominal).tolist(),
        "niveaux": niveaux,
        "produit": "autocall_plain",
        "has_autocall": p["has_autocall"],
        "barrieres_rappel_pct": [x*100 for x in res["barrieres_rappel"]] if p["has_autocall"] else None,
        "nombre_moyen_coupons": round(res["nombre_moyen_coupons"], 4),
        "nominal": nominal, "S0": S0,
        "coupon_pct": p["coupon"] * 100, "K_auto_pct": K_auto * 100,
        "B_pdi_pct": None if B_pdi is None else B_pdi * 100,
        "first_call_date": p["first_call_date"], "n_simulations": p["n_simulations"], "seed": p["seed"],
    })
```

- Même structure que le Phoenix : validation, `nominal = p.pop("nominal")`, `res = analyse_autocall_plain(**p)`.
- `S0, K_auto, B_pdi = ...` : raccourcis pour les lignes suivantes.
- `niveaux` : rappel (s'il est actif), seuil du coupon final (le même niveau `K_auto`), protection (si elle existe).
- `grille = _grid(..., sauts=seuils)` : marches aux seuils.
- `remboursement_final = calculer_remboursement_autocall_maturite(grille, S0, K_auto, B_pdi, p["coupon"] * len(p["obs_dates"]))["total"] * nominal` : à maturité, **tous** les coupons accumulés (coupon × nombre de dates) si le seuil final est atteint, sinon aucun ; capital protégé ou non. La même fonction que celle du moteur : le graphe et le prix suivent la même règle.
- La réponse ajoute aux indicateurs communs : la grille et les courbes (en listes complètes, sans arrondi), les niveaux, le nombre moyen de coupons, et un rappel des paramètres (coupon, barrières en %, première date de rappel, simulations, graine) que l'interface affiche dans ses notes.

### 25. Le cache des calculs pour l'export PDF

```python
_calculs = OrderedDict()
_verrou = RLock()
_DUREE_DE_VIE = 1800   # secondes
_NB_MAX_CALCULS = 20
_pricing_paths = {'/api/option', '/api/digital', '/api/forward',
                  '/api/strategy',
                  '/api/phoenix', '/api/autocall',
                  }
```

- La bannière ouvre la dernière section.
- **Problème à éviter :** un export PDF qui recalculerait à partir du formulaire ne correspondrait plus à l'écran dès que l'utilisateur modifie un champ après le calcul. **Solution :** le serveur **mémorise un instantané** (paramètres + résultats) de chaque calcul, identifié par un `calculation_id`. Le PDF relit cet instantané, sans recalcul.
- `_calculs = OrderedDict()` : le cache ; l'ordre d'insertion permet de supprimer facilement les plus anciens.
- `_verrou = RLock()` : verrou partagé par les fonctions qui lisent ou modifient le cache.
- `_DUREE_DE_VIE = 1800` (30 minutes) et `_NB_MAX_CALCULS = 20` : la mémoire ne grossit pas indéfiniment. Les deux valeurs sont nommées une fois et réutilisées.
- `_pricing_paths = {...}` : l'ensemble (`set`) des routes de calcul dont on mémorise le résultat. Les routes de données de marché n'y sont pas.
- **Limite :** ce cache vit dans la mémoire du processus. Un redémarrage l'efface (d'où l'erreur 410 « Calcul expiré ») et il ne serait pas partagé entre plusieurs processus en production.

### 26. `verifier_json_api()` — contrôle d'entrée

```python
@app.before_request
def verifier_json_api():
    """Toute requête POST vers l'API doit contenir un objet JSON.

    Le contenu (nombres, bornes, types) est vérifié par validation.py.
    """
    if request.method != 'POST' or not request.path.startswith('/api/'):
        return
    if not request.is_json:
        return _err('Un objet JSON est requis.', 415)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _err('Un objet JSON valide est requis.')
    if data.get('vol_source') not in (None, 'manual', 'hist', 'vix'):
        return _err('Source de volatilité inconnue : utilisez une saisie, un historique ou le VIX.')
    if 'leg_vols' in data:
        return _err('La stratégie utilise une volatilité constante commune à ses jambes.')
```

- `@app.before_request` : Flask appelle cette fonction **avant chaque requête**. Si elle renvoie une réponse, la route n'est pas appelée.
- `if request.method != 'POST' or not request.path.startswith('/api/'): return` : seules les requêtes POST vers l'API sont contrôlées ; `return` sans valeur laisse la requête continuer.
- `if not request.is_json:` : le corps doit être déclaré comme JSON (code 415, « type de média non supporté »).
- `data = request.get_json(silent=True)` : `silent=True` renvoie `None` au lieu de lever une erreur si le JSON est mal formé.
- `if not isinstance(data, dict):` : on attend un **objet** JSON (`{...}`), pas une liste ni un nombre. Les routes peuvent donc écrire `request.get_json()` sans se méfier.
- `if data.get('vol_source') not in (None, 'manual', 'hist', 'vix'):` : si le champ de source de volatilité est envoyé, il doit être une des trois sources connues.
- `if 'leg_vols' in data:` : refuse explicitement une volatilité par jambe : une stratégie utilise une seule volatilité commune (le modèle n'a pas de smile).

### 27. `memoriser_calcul()` — contrôle de sortie et mémorisation

```python
@app.after_request
def memoriser_calcul(response):
    """Contrôle de sortie (aucun NaN/inf) et mémorisation du calcul pour le PDF."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    if response.is_json and response.status_code < 400:
        data = response.get_json()
        try:
            json.dumps(data, allow_nan=False)
        except (ValueError, TypeError):
            response.set_data(app.json.dumps({'error': 'Résultat numérique non fini : vérifiez les paramètres.'}))
            response.status_code = 500
            return response
        if request.path in _pricing_paths:
            ident = uuid4().hex
            with _verrou:
                now = monotonic()
                for key in list(_calculs):
                    if now - _calculs[key]['clock'] > _DUREE_DE_VIE:
                        del _calculs[key]
                _calculs[ident] = {'clock': now, 'date': datetime.now(timezone.utc).isoformat(),
                                   'route': request.path, 'parametres': request.get_json(), 'resultats': data}
                while len(_calculs) > _NB_MAX_CALCULS:
                    _calculs.popitem(last=False)
            data['calculation_id'] = ident
            response.set_data(app.json.dumps(data))
    return response
```

- `@app.after_request` : Flask appelle cette fonction **après chaque requête**, avec la réponse prête à partir ; elle doit la renvoyer.
- `response.headers['X-Content-Type-Options'] = 'nosniff'` : le navigateur n'essaie pas de deviner le type du contenu (bonne pratique de sécurité).
- `response.headers['Cache-Control'] = 'no-store'` : un prix ne doit jamais être servi depuis un cache.
- `if response.is_json and response.status_code < 400:` : seulement pour les réponses JSON réussies.
- `json.dumps(data, allow_nan=False)` dans un `try` : **dernier filet**. Si un `NaN` ou un `inf` s'est glissé dans un résultat, le JSON standard serait invalide (`NaN` n'existe pas en JSON). On le détecte ici et on remplace la réponse par une erreur 500 propre plutôt qu'un chiffre absurde. C'est le **seul** contrôle de finitude des résultats : les moteurs n'en refont pas.
- `if request.path in _pricing_paths:` : pour les routes de calcul :
  - `ident = uuid4().hex` : identifiant aléatoire de 32 caractères, impossible à deviner (on ne peut pas récupérer le calcul d'un autre en incrémentant un numéro) ;
  - `with _verrou:` : tout le bloc est protégé contre les accès simultanés ;
  - la boucle `for key in list(_calculs)` supprime les calculs de plus de 30 minutes (`list(...)` fait une copie des clés, car on ne peut pas modifier un dictionnaire pendant qu'on le parcourt) ;
  - `_calculs[ident] = {...}` : l'instantané : horloge, date UTC lisible, route, paramètres reçus (tels que saisis, donc en %), résultats ;
  - `while len(_calculs) > _NB_MAX_CALCULS: _calculs.popitem(last=False)` : on supprime les plus anciens au-delà de 20 ;
  - `data['calculation_id'] = ident` puis `response.set_data(app.json.dumps(data))` : l'identifiant est ajouté à la réponse ; le navigateur le renverra pour demander le PDF.
- `monotonic()` plutôt que l'heure système : une horloge monotone ne recule jamais (changement d'heure, synchronisation réseau).

### 28. `api_export_pdf()` — export PDF

```python
@app.post('/api/export_pdf')
def api_export_pdf():
    """PDF du calcul mémorisé : aucun recalcul, donc identique à l'écran."""
    ident = request.get_json().get('calculation_id', '')
    with _verrou:
        snapshot = _calculs.get(ident) if isinstance(ident, str) else None
        if snapshot is None or monotonic() - snapshot['clock'] > _DUREE_DE_VIE:
            return _err('Calcul expiré ou serveur redémarré : relancez le calcul.', 410)
    from pdf_engine import generer_pdf_calcul
    try:
        contenu = generer_pdf_calcul(snapshot)
    except ImportError:   # reportlab est importé à la demande dans pdf_engine
        return _err('Installez les dépendances : pip install -r requirements.txt', 503)
    return send_file(BytesIO(contenu), mimetype='application/pdf', as_attachment=True,
                     download_name='dernier_calcul.pdf')
```

- `ident = request.get_json().get('calculation_id', '')` : l'identifiant envoyé par le navigateur.
- `with _verrou:` : lecture protégée du cache.
- `snapshot = _calculs.get(ident) if isinstance(ident, str) else None` : l'instantané, s'il existe.
- Absent ou expiré : code **410 Gone** (« la ressource a existé mais n'existe plus »), plus précis qu'un 404 ; le message demande de relancer le calcul.
- `from pdf_engine import generer_pdf_calcul` : import placé ici, au moment de l'export.
- `try: contenu = generer_pdf_calcul(snapshot)` / `except ImportError:` : `reportlab` est importé à la demande dans `pdf_engine` ; s'il n'est pas installé, le pricer fonctionne quand même et seul l'export renvoie un message (503, « service indisponible ») qui dit quoi installer.
- `send_file(BytesIO(contenu), mimetype='application/pdf', as_attachment=True, download_name='dernier_calcul.pdf')` : le PDF est construit en mémoire, jamais écrit sur le disque, et proposé au téléchargement.

### 29. Lancement du serveur

```python
if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=False, use_reloader=False)
```

- `if __name__ == "__main__":` : vrai seulement quand on lance `python main.py` (pas quand le fichier est importé).
- `app.run(host="127.0.0.1", debug=False, use_reloader=False)` :
  - `127.0.0.1` : le serveur n'est accessible que depuis votre ordinateur, pas depuis le réseau ;
  - `debug=False` : le mode debug de Flask expose une console Python dans le navigateur en cas d'erreur, dangereux si la page est accessible à d'autres ;
  - `use_reloader=False` : le rechargement automatique lance **deux** processus, ce qui dédoublerait le cache des calculs (un PDF demandé au mauvais processus ne trouverait pas son calcul). Contrepartie : après une modification du code, il faut relancer `python main.py` à la main.

---

## Pour aller plus loin

- Lancez le serveur et appelez une route à la main : `curl -X POST http://127.0.0.1:5000/api/forward -H "Content-Type: application/json" -d '{"S0":100,"K":100,"T":1,"r":5,"q":0}'`.
- Envoyez `"S0": true` ou `"sigma": "nan"` : quel message reçoit-on, et quelle fonction de `validation.py` l'a produit ?
