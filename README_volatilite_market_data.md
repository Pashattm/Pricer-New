# `volatility_engine.py` et `market_data_engine.py` — volatilité et données de marché

Ces deux fichiers alimentent l'onglet **Chantier** (laboratoire de volatilité) et le choix « σ historique » des onglets de pricing.

**Répartition des rôles :**
- `volatility_engine.py` : **maths pures**. Reçoit des prix propres, renvoie des volatilités en **décimal annualisé** (`0.25` = 25 %). Aucun accès réseau, aucune route Flask, aucun contrôle.
- `market_data_engine.py` : **entrées / sorties**. Va chercher les données sur Yahoo Finance, **nettoie les cours** (seul endroit où ils sont contrôlés), appelle le moteur, convertit en **pourcentages** pour l'API.
- Le paramètre λ de l'EWMA et la période sont vérifiés par `validation.parametres_volatilite`.

Pourquoi séparer ? Si Yahoo change d'API (fréquent), seul `market_data_engine.py` est touché. Et les formules restent vérifiables hors connexion, avec des prix inventés.

---

# Le code, ligne par ligne

## Partie A — `volatility_engine.py`

### 1. En-tête du fichier

```python
"""Mesures de volatilité à partir des cours historiques.

Fonctions disponibles : log-rendements, volatilité historique et glissante,
estimateur de Parkinson, série EWMA et demi-vie de ses poids.
Yang-Zhang et GARCH restent des emplacements à compléter (pass).

Les calculs renvoient des décimaux annualisés ; market_data_engine les
convertit en pourcentages pour l'API. Ce moteur ne contient aucune route Flask.
Les cours sont nettoyés par market_data_engine et λ est vérifié par
validation.py : les fonctions ci-dessous supposent des données propres.
"""
```

- Elle liste les fonctions disponibles et signale que Yang-Zhang et GARCH sont des **emplacements réservés** (`pass`).
- Elle rappelle les unités : décimaux annualisés ici, pourcentages dans l'API.
- Elle précise la répartition des contrôles : cours nettoyés par `market_data_engine`, λ vérifié par `validation.py`. Les fonctions supposent donc des données propres.

### 2. Imports

```python
import numpy as np
```

- `import numpy as np` : la seule dépendance du moteur de volatilité.

### 3. `ANNUALISATION` — séances par an

```python
ANNUALISATION = 252  # séances par an
```

- `ANNUALISATION = 252` : le nombre usuel de séances de Bourse par an. Une constante nommée plutôt que `252` écrit en dur dans chaque fonction ; `market_data_engine` la renvoie aussi dans la réponse de l'API.

### 4. `log_returns()` — log-rendements

```python
def log_returns(prices):
    """
    Calcule les log-rendements d'une série de prix.

    Formule :
        r_t = ln(S_t / S_{t-1})

    Les log-rendements servent ensuite de base au calcul de la
    volatilité historique, EWMA, GARCH, etc.
    """
    prices = np.asarray(prices, dtype=float)
    return np.log(prices[1:] / prices[:-1])
```

- La bannière `# === 1. RENDEMENTS ===` ouvre la section.
- **Docstring** : la formule r_t = ln(S_t / S_{t−1}) ; ces rendements servent de base à toutes les mesures de volatilité.
- `prices = np.asarray(prices, dtype=float)` : accepte une liste, une série pandas ou un tableau, et le convertit en tableau NumPy de nombres décimaux.
- `return np.log(prices[1:] / prices[:-1])` : `prices[1:]` = tous les prix sauf le premier, `prices[:-1]` = tous sauf le dernier ; leur division donne S_t / S_{t−1} pour toutes les dates d'un coup (division décalée vectorisée).
- **Pourquoi des log-rendements ?** Ils s'additionnent dans le temps (le rendement sur 2 jours = somme des deux), et Black-Scholes suppose précisément que ln(S) suit une loi normale.

### 5. `historical_volatility()` — volatilité close-to-close

```python
def historical_volatility(prices, annualization=ANNUALISATION):
    """
    Calcule la volatilité historique close-to-close.

    Étapes :
    1. calculer les log-rendements ;
    2. calculer leur écart-type ;
    3. annualiser la volatilité.

    Pour des données journalières, on utilise généralement :
        sigma_annuelle = sigma_journalière * sqrt(252)

    Renvoie :
        volatilité historique annualisée en décimal
        Exemple : 0.25 = 25 %
    """
    daily_volatility = np.std(log_returns(prices), ddof=1)
    return float(daily_volatility * np.sqrt(annualization))
```

- La bannière `# === 2. VOLATILITÉ HISTORIQUE ===` ouvre la section.
- **Docstring** : les trois étapes (rendements, écart-type, annualisation) et l'unité du résultat.
- `daily_volatility = np.std(log_returns(prices), ddof=1)` : écart-type des rendements quotidiens ; `ddof=1` divise par n − 1 (estimateur non biaisé de la variance).
- `return float(daily_volatility * np.sqrt(annualization))` : **annualisation par √252**. Si les rendements quotidiens sont indépendants, les variances s'additionnent, donc la volatilité croît comme la racine du temps.

### 6. `rolling_volatility()` — volatilité glissante

```python
def rolling_volatility(prices, window=20, annualization=ANNUALISATION):
    """
    Calcule une volatilité historique sur une fenêtre glissante.

    Exemple avec window=20 :
    à chaque date, on utilise uniquement les 20 derniers rendements.

    Cela permet de voir comment la volatilité évolue dans le temps
    au lieu d'obtenir une seule volatilité sur toute la période.

    Renvoie :
        série de len(rendements) - window + 1 volatilités annualisées
    """
    returns = log_returns(prices)
    rolling_vol = []

    for i in range(window, len(returns) + 1):
        # Sélection des derniers rendements
        window_returns = returns[i - window:i]
        # Écart-type sur la fenêtre, puis annualisation
        rolling_vol.append(np.std(window_returns, ddof=1) * np.sqrt(annualization))

    return np.array(rolling_vol)
```

- **Docstring** : à chaque date, on n'utilise que les `window` derniers rendements ; on voit ainsi la vol **évoluer** (pics en période de crise) au lieu d'un seul chiffre.
- `returns = log_returns(prices)` et `rolling_vol = []`.
- `for i in range(window, len(returns) + 1):` : chaque position de la fenêtre.
- `window_returns = returns[i - window:i]` : les `window` rendements qui se terminent juste avant i.
- `rolling_vol.append(np.std(window_returns, ddof=1) * np.sqrt(annualization))` : la vol annualisée de la fenêtre.
- `return np.array(rolling_vol)` : `len(rendements) − window + 1` valeurs.
- Boucle Python assumée : quelques centaines d'itérations, rapide. Une version vectorisée existe (`pandas.Series.rolling(window).std()`), mais la boucle montre explicitement la fenêtre.

### 7. `parkinson_volatility()` — estimateur de Parkinson

```python
def parkinson_volatility(high, low, annualization=ANNUALISATION):
    """
    Estimateur de volatilité de Parkinson.

    Contrairement au close-to-close, il utilise les plus hauts et
    plus bas observés pendant chaque séance.

    L'objectif est d'utiliser davantage d'information contenue dans
    les mouvements intraday.

    Limite importante :
    l'estimateur ne capture pas correctement les gaps overnight.
    """
    # L'amplitude logarithmique mesure les mouvements pendant la séance.
    ranges = np.log(np.asarray(high, dtype=float)) - np.log(np.asarray(low, dtype=float))
    daily_variance = np.mean(ranges ** 2) / (4 * np.log(2))
    return float(np.sqrt(daily_variance * annualization))
```

- **Docstring** : on utilise l'**amplitude de la séance** (plus haut / plus bas) au lieu des seules clôtures. À nombre de jours égal, l'estimateur est plus précis car il voit davantage du mouvement de la journée.
- `ranges = np.log(...high) - np.log(...low)` : l'amplitude logarithmique de chaque séance.
- `daily_variance = np.mean(ranges ** 2) / (4 * np.log(2))` : la variance quotidienne ; le facteur 1/(4 ln 2) vient de la loi de l'amplitude d'un mouvement brownien.
- `return float(np.sqrt(daily_variance * annualization))` : volatilité annualisée.
- **Limite documentée :** les **gaps d'ouverture** (mouvements de nuit) sont invisibles dans l'amplitude d'une séance : Parkinson sous-estime la vol des titres qui « gappent » (résultats publiés hors séance).

### 8. `yang_zhang_volatility()` — emplacement réservé

```python
def yang_zhang_volatility(open_, high, low, close, annualization=ANNUALISATION):
    """
    Estimateur de volatilité de Yang-Zhang.

    Il combine plusieurs informations :
    - mouvement overnight ;
    - mouvement open-to-close ;
    - information high / low.

    Il est donc plus complet que le simple close-to-close
    et que Parkinson lorsque le sous-jacent présente des gaps.
    """
    pass
```

- La fonction ne contient que sa docstring et `pass` (une instruction qui ne fait rien) : c'est un **emplacement réservé**.
- La docstring décrit déjà le but : combiner le mouvement de nuit, le mouvement d'ouverture à clôture et l'amplitude de la séance, pour corriger la limite de Parkinson. C'est une bonne pratique de laisser l'interface prête et documentée pour la suite.

### 9. `ewma_half_life()` — demi-vie de l'EWMA

```python
def ewma_half_life(lambda_):
    """
    Calcule la demi-vie associée au paramètre lambda d'un EWMA.

    La demi-vie correspond au nombre de périodes nécessaires
    pour que le poids d'une observation soit divisé par deux.

    Exemple :
        lambda = 0.94
        -> demi-vie d'environ 11 jours.
    """
    return float(np.log(0.5) / np.log(lambda_))
```

- La bannière `# === 3. EWMA / GARCH ===` ouvre la section.
- `return float(np.log(0.5) / np.log(lambda_))` : nombre de jours pour que le poids d'une observation soit divisé par deux : λ^h = 0,5 ⇒ h = ln 0,5 / ln λ. Pour λ = 0,94, h ≈ 11,2 jours.
- Ça rend λ **interprétable** : « la mémoire de l'EWMA est d'environ deux semaines ».

### 10. `ewma_volatility_series()` — volatilité EWMA

```python
def ewma_volatility_series(returns, lambda_=0.94, annualization=ANNUALISATION):
    """Volatilité EWMA après chaque rendement, en décimal annualisé.

    Les observations récentes pèsent davantage :
        variance_t = lambda * variance_{t-1} + (1 - lambda) * r_t²
    Plus lambda est proche de 1, plus la mémoire est longue et la vol stable.

    Moyenne des rendements supposée nulle. Initialisation au carré du
    premier rendement : aucune observation future n'entre dans le calcul.
    La valeur datée t inclut le rendement t (mise à jour après clôture).
    """
    returns = np.asarray(returns, dtype=float)
    variance = returns[0] ** 2
    values = [np.sqrt(variance * annualization)]
    for daily_return in returns[1:]:
        # On conserve une partie du passé et on ajoute le choc de la séance.
        variance = lambda_ * variance + (1 - lambda_) * daily_return ** 2
        values.append(np.sqrt(variance * annualization))
    return np.asarray(values)
```

- **Docstring** : la formule σ²_t = λ·σ²_{t−1} + (1−λ)·r_t². Les chocs récents pèsent plus ; les anciens s'effacent géométriquement. C'est le modèle RiskMetrics (J.P. Morgan, 1994), avec λ = 0,94 pour des données quotidiennes. Plus λ est proche de 1, plus la mémoire est longue et la vol stable.
- `returns = np.asarray(returns, dtype=float)` : conversion en tableau.
- `variance = returns[0] ** 2` : **piège évité**. L'initialisation « naturelle » consiste à prendre la variance de **tout** l'échantillon comme point de départ. Cela injecte de l'information future dans les premières valeurs (biais d'anticipation). On initialise donc au carré du **premier** rendement seulement. Conséquence assumée : les toutes premières valeurs sont bruitées, et changer la période historique change l'initialisation.
- `values = [np.sqrt(variance * annualization)]` : la première vol annualisée.
- `for daily_return in returns[1:]:` puis la mise à jour `variance = lambda_ * variance + (1 - lambda_) * daily_return ** 2` : on garde λ du passé et on ajoute (1 − λ) du choc du jour. **Moyenne supposée nulle** : sur des rendements quotidiens, elle est négligeable devant l'écart-type.
- `values.append(...)` puis `return np.asarray(values)` : une vol par rendement. La valeur datée t **inclut** le rendement du jour t (mise à jour après la clôture).

### 11. `garch_volatility()` — emplacement réservé

```python
def garch_volatility(returns):
    """
    Estime une volatilité dynamique avec un modèle GARCH.

    Idée générale :
    la volatilité d'aujourd'hui dépend notamment :
    - de la volatilité passée ;
    - des chocs observés récemment.

    Cette fonction sera implémentée plus tard.
    """
    pass
```

- Comme Yang-Zhang : docstring et `pass`. GARCH modélise une volatilité qui dépend de la volatilité passée **et** des chocs récents, avec un retour vers une moyenne de long terme ; il permettrait une prévision de volatilité.

## Partie B — `market_data_engine.py`

### 12. En-tête du fichier

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MARKET DATA ENGINE

Récupération des données financières nécessaires
aux différents moteurs de pricing (Yahoo Finance).

C'est ici, et seulement ici, que les cours sont contrôlés
(dates triées, pas de doublon, cours positifs et finis) :
volatility_engine reçoit des données propres.

Created on Wed Oct 14 10:59:13 2026
@author: theojondeau
"""
```

- `#!/usr/bin/env python3` : la ligne « shebang », qui permet de lancer le fichier directement sous Mac / Linux ; `# -*- coding: utf-8 -*-` : déclaration d'encodage (inutile en Python 3, mais inoffensive). Ces deux lignes ont été ajoutées par l'éditeur (Spyder) à la création du fichier.
- La docstring dit que c'est **ici, et seulement ici**, que les cours sont contrôlés : `volatility_engine` reçoit des données propres. Elle garde aussi la date de création et l'auteur.

### 13. Imports

```python
import numpy as np
import yfinance as yf

from volatility_engine import (
    historical_volatility, rolling_volatility, log_returns,
    parkinson_volatility, ewma_volatility_series, ewma_half_life, ANNUALISATION,
)
```

- `import numpy as np` : contrôles et conversions des cours.
- `import yfinance as yf` : client **non officiel** de Yahoo Finance, gratuit. En C#, il n'existe pas d'équivalent simple : c'est un des arguments en faveur de Python.
- `from volatility_engine import (...)` : les mesures de volatilité et la constante `ANNUALISATION`.

### 14. `search_tickers()` — recherche de tickers

```python
def search_tickers(query, max_results=8):
    """Cherche des tickers sur Yahoo Finance (barre de recherche du site).

    Renvoie : une liste de dicts {symbol, name, exchange}, ou une liste vide
    si Yahoo ne répond pas.
    """
    try:
        resultats = yf.Search(query, max_results=max_results).quotes
    except Exception:
        return []  # si yahoo répond pas je renvoie juste rien

    return [
        {
            "symbol": r.get("symbol"),
            "name": r.get("shortname") or r.get("longname") or r.get("symbol"),
            "exchange": r.get("exchange"),
        }
        for r in resultats
        if r.get("symbol")
    ]
```

- La bannière `# === 1. RECHERCHE DES SOUS-JACENTS ===` ouvre la section.
- `try: resultats = yf.Search(query, max_results=max_results).quotes` : utilise la barre de recherche de Yahoo.
- `except Exception: return []` : **choix volontaire**. En cas d'échec, on renvoie une liste vide plutôt qu'une erreur : la recherche est un confort (autocomplétion) ; elle ne doit pas bloquer l'utilisateur, qui peut toujours taper le symbole.
- La liste en compréhension garde, pour chaque résultat ayant un symbole : le symbole, le nom (`shortname`, sinon `longname`, sinon le symbole : Yahoo ne remplit pas toujours tous les champs ; `or` renvoie la première valeur non vide) et la place de cotation.

### 15. `get_cotation()` — spot et devise

```python
def get_cotation(ticker):
    """Spot et devise en une seule requête Yahoo."""
    infos = yf.Ticker(ticker).fast_info
    return {"S0": float(infos["last_price"]), "devise": infos["currency"]}
```

- La bannière `# === 2. COTATION : SPOT, DEVISE, VIX ===` ouvre la section.
- `infos = yf.Ticker(ticker).fast_info` : accès rapide (une requête légère) plutôt que de télécharger tout l'historique pour un seul prix.
- `return {"S0": float(infos["last_price"]), "devise": infos["currency"]}` : spot et devise en **une seule** requête. Il y avait auparavant deux fonctions, qui interrogeaient Yahoo deux fois pour le même ticker.

### 16. `get_vix()` — le VIX

```python
def get_vix():
    """VIX : volatilité implicite à 30 jours du S&P 500, en %."""
    return float(yf.Ticker("^VIX").fast_info["last_price"])
```

- `float(yf.Ticker("^VIX").fast_info["last_price"])` : le VIX a son propre ticker, `^VIX`.
- **À savoir :** le VIX est la volatilité **implicite** à 30 jours du **S&P 500**. L'utiliser pour une action européenne est une approximation grossière, utile seulement comme valeur de repli.

### 17. `_telecharger_historique()` — historique contrôlé

```python
def _telecharger_historique(ticker, periode):
    """Télécharge l'historique OHLC ajusté, trié par date et sans doublon.

    auto_adjust=True : prix ajustés des dividendes et des splits, sinon un split
    4-pour-1 ressemblerait à une chute de -75 % en une séance.
    """
    data = yf.Ticker(ticker).history(period=periode, auto_adjust=True)
    if data.empty:
        raise ValueError(f"Aucune donnée historique disponible pour {ticker}.")
    data = data.sort_index()
    if data.index.has_duplicates:
        raise ValueError("L'historique contient des dates dupliquées.")
    return data
```

- La bannière `# === 3. HISTORIQUE CONTRÔLÉ ===` ouvre la section.
- `data = yf.Ticker(ticker).history(period=periode, auto_adjust=True)` : un tableau pandas avec les colonnes Open, High, Low, Close, une ligne par séance. **`auto_adjust=True` est essentiel** : les prix sont ajustés des dividendes et des divisions d'actions (*splits*). Sans ça, un split 4-pour-1 ressemblerait à une chute de −75 % en une séance et ferait exploser la volatilité.
- `if data.empty:` : ticker inconnu ou sans historique.
- `data = data.sort_index()` : tri chronologique (l'index du tableau est la date).
- `if data.index.has_duplicates:` : une date en double fausserait les rendements.

### 18. `_verifier_cours()` — cours valides

```python
def _verifier_cours(*series):
    """Tous les cours doivent être finis et strictement positifs (sinon log(0) = -inf)."""
    for serie in series:
        if not np.all(np.isfinite(serie)) or np.any(serie <= 0):
            raise ValueError("L'historique contient des cours manquants, nuls ou non finis.")
```

- `for serie in series:` : la fonction accepte plusieurs séries (`*series` = nombre variable d'arguments).
- `if not np.all(np.isfinite(serie)) or np.any(serie <= 0):` : tous les cours doivent être finis (pas de trou `NaN`) et strictement positifs (sinon `log(0)` = −∞ dans les rendements).

### 19. `get_vol_historique()` — σ historique des onglets de pricing

```python
def get_vol_historique(ticker, periode="1y"):
    """Volatilité historique close-to-close annualisée, en pourcentage.

    Utilisée par /api/market pour pré-remplir σ dans les onglets de pricing.
    """
    close = _telecharger_historique(ticker, periode)["Close"].dropna().to_numpy(dtype=float)
    _verifier_cours(close)
    if len(close) < 20:
        raise ValueError("Pas assez d'historique pour calculer une volatilité.")
    return historical_volatility(close) * 100
```

- La bannière `# === 4. VOLATILITÉ HISTORIQUE (onglets de pricing) ===` ouvre la section.
- `close = _telecharger_historique(...)["Close"].dropna().to_numpy(dtype=float)` : les clôtures, sans valeurs manquantes, en tableau NumPy.
- `_verifier_cours(close)` : contrôle.
- `if len(close) < 20:` : en dessous de 20 cours, l'estimation n'a pas de sens.
- `return historical_volatility(close) * 100` : en % pour l'API. Dans `main.py`, si cette fonction échoue, la vol historique vaut `None` et l'interface bascule sur le VIX.

### 20. `get_volatility_snapshot()` — toutes les mesures de l'onglet Chantier

```python
def get_volatility_snapshot(ticker, periode="1y", lambda_=0.94):
    """Toutes les mesures sur un seul historique OHLC ajusté.

    Un seul téléchargement garantit les mêmes séances pour toutes les mesures.
    Moteurs : décimaux ; réponse destinée à l'API : pourcentages.
    Parkinson scalaire couvre toute la période ; sa courbe couvre 20 séances.
    Les quatre courbes démarrent à la première fenêtre complète de 60 rendements.
    """
    data = _telecharger_historique(ticker, periode)
    if not {"Close", "High", "Low"}.issubset(data.columns):
        raise ValueError("Les cours de clôture, plus hauts et plus bas sont nécessaires.")
    close = data["Close"].to_numpy(dtype=float)
    high = data["High"].to_numpy(dtype=float)
    low = data["Low"].to_numpy(dtype=float)
    _verifier_cours(close, high, low)
    if np.any(high < low) or np.any(close < low) or np.any(close > high):
        raise ValueError("Les cours OHLC sont incohérents.")
    if len(close) < 61:
        raise ValueError("Il faut au moins 61 séances pour la fenêtre de 60 rendements.")

    vol_hist = historical_volatility(close)
    vol_20 = rolling_volatility(close, window=20)[40:]
    vol_60 = rolling_volatility(close, window=60)
    ewma = ewma_volatility_series(log_returns(close), lambda_)[59:]
    parkinson = parkinson_volatility(high, low)
    # Chaque point utilise 20 amplitudes, jusqu'à la séance affichée incluse.
    parkinson_20 = [parkinson_volatility(high[i-19:i+1], low[i-19:i+1]) for i in range(60, len(close))]

    def percent_series(series):
        return [round(float(value * 100), 4) for value in series]

    return {
        "ticker": ticker, "periode": periode,
        "vol_historique": round(vol_hist * 100, 4),
        "vol_20": round(float(vol_20[-1] * 100), 4),
        "vol_60": round(float(vol_60[-1] * 100), 4),
        "vol_ewma": round(float(ewma[-1] * 100), 4),
        "vol_parkinson": round(parkinson * 100, 4),
        "lambda": lambda_, "ewma_half_life": round(ewma_half_life(lambda_), 2),
        "dates": [date.strftime("%Y-%m-%d") for date in data.index[60:]],
        "series_20": percent_series(vol_20), "series_60": percent_series(vol_60),
        "series_ewma": percent_series(ewma), "series_parkinson_20": percent_series(parkinson_20),
        "annualization": ANNUALISATION, "observations": len(close),
        "start_date": data.index[0].strftime("%Y-%m-%d"),
        "end_date": data.index[-1].strftime("%Y-%m-%d"),
    }
```

- La bannière `# === 5. LABORATOIRE DE VOLATILITÉ ===` ouvre la section.
- **Docstring** : un seul téléchargement garantit les mêmes séances pour toutes les mesures. En téléchargeant séparément les clôtures puis les plus hauts / plus bas, une séance pourrait s'ajouter entre deux appels.

**Données**
- `data = _telecharger_historique(ticker, periode)` puis le contrôle des colonnes `Close`, `High`, `Low` (`issubset` = « est inclus dans »).
- `close`, `high`, `low` : trois tableaux NumPy.
- `_verifier_cours(close, high, low)` : cours finis et positifs.
- `if np.any(high < low) or np.any(close < low) or np.any(close > high):` : **cohérence OHLC** : la clôture est entre le plus bas et le plus haut.
- `if len(close) < 61:` : 61 séances = 60 rendements pour la fenêtre longue.

**Mesures**
- `vol_hist = historical_volatility(close)` : sur toute la période.
- `vol_20 = rolling_volatility(close, window=20)[40:]` et `vol_60 = rolling_volatility(close, window=60)` : vols glissantes.
- `ewma = ewma_volatility_series(log_returns(close), lambda_)[59:]` : EWMA.
- `parkinson = parkinson_volatility(high, low)` : sur toute la période.
- `parkinson_20 = [parkinson_volatility(high[i-19:i+1], low[i-19:i+1]) for i in range(60, len(close))]` : Parkinson glissant sur les 20 séances qui se terminent à la séance affichée **incluse** (`i+1`, car la borne haute d'une tranche Python est exclue).

**Alignement des courbes.** Les séries n'ont pas la même longueur. Pour les superposer sur un même graphe, toutes démarrent à la première fenêtre complète de 60 rendements (n = nombre de cours) :

| Série | Longueur brute | Découpe | Longueur finale |
|---|---|---|---|
| `vol_20` | n − 20 | `[40:]` | n − 60 |
| `vol_60` | n − 60 | — | n − 60 |
| `ewma` | n − 1 | `[59:]` | n − 60 |
| `parkinson_20` | `i` de 60 à n−1 | — | n − 60 |
| `dates` | n | `index[60:]` | n − 60 |

**Réponse**
- `percent_series(series)` : petite fonction interne qui convertit une série en liste de % arrondis.
- Le dictionnaire renvoyé contient : les cinq indicateurs en % (la dernière valeur de chaque série glissante), λ et la demi-vie, les dates au format `AAAA-MM-JJ` (`strftime`), les quatre séries, l'annualisation, le nombre d'observations et les dates de début et de fin. Tout ce qu'il faut pour savoir **sur quoi** porte le calcul.
- **Deux Parkinson différents** (piège pour le lecteur) : l'indicateur `vol_parkinson` couvre toute la période ; la courbe `series_parkinson_20` couvre 20 séances. L'interface l'écrit sous le graphe.

---

## Exercices

1. Comparez la vol historique 1 an d'une action et sa vol EWMA juste après une publication de résultats : laquelle réagit le plus ? Pourquoi ?
2. Prenez λ = 0,97 puis λ = 0,90 : calculez les demi-vies et observez la réactivité des courbes.
3. Trouvez une action avec de gros gaps d'ouverture : Parkinson est-il au-dessus ou en dessous du close-to-close ?
