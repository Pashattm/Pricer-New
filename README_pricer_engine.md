# `pricer_engine.py` — options vanilles, grecques, forwards, stratégies, digitales

Ce fichier est la **base mathématique** du projet. Il ne dépend que de NumPy, de `statistics.NormalDist` (bibliothèque standard) et du simulateur commun `simulation_engine.py`. Il ne sait rien de Flask ni du navigateur : on pourrait l'importer tel quel dans un autre programme.

**Convention :** `r`, `q`, `sigma` en décimal (`0.05` = 5 %), `T` en années, `S0` et `K` en prix.

**Aucun contrôle de paramètre ici :** `validation.py` vérifie tout avant l'appel. Les fonctions ressemblent donc aux formules du cours, sans lignes de garde.

**Un repère de lecture :** les lignes `# =========================` encadrant un titre sont des **bannières de section**. Elles n'ont aucun effet sur le programme ; elles découpent le fichier en chapitres.

---

# Le code, ligne par ligne
### 1. En-tête du fichier

```python
"""Moteur de pricing : options vanilles, grecques, forwards, stratégies et digitales.

Convention : r, q et sigma en décimal (0.05 = 5 %), T en années.
Les paramètres sont vérifiés par validation.py avant d'arriver ici.
Les simulations passent par simulation_engine.py (une seule diffusion dans tout le projet).
"""
```

- La première ligne résume le contenu du fichier.
- `Convention : r, q et sigma en décimal (0.05 = 5 %), T en années.` : la règle d'unités, source d'erreurs n°1 dans un pricer. Le formulaire travaille en %, les moteurs en décimal ; la conversion est faite dans `validation.py`.
- `Les paramètres sont vérifiés par validation.py avant d'arriver ici.` : explique pourquoi aucune fonction ne teste ses arguments.
- `Les simulations passent par simulation_engine.py` : la diffusion Monte Carlo n'est écrite qu'à un seul endroit.

### 2. Imports

```python
import numpy as np
from statistics import NormalDist

from simulation_engine import simuler_cours_observations
```

- `import numpy as np` : tableaux et fonctions mathématiques vectorisées (`np.exp`, `np.log`, `np.maximum`…).
- `from statistics import NormalDist` : la loi normale de la **bibliothèque standard** de Python (disponible depuis Python 3.8). On évite ainsi d'installer SciPy, une dépendance lourde, juste pour deux fonctions.
- `from simulation_engine import simuler_cours_observations` : le simulateur commun, utilisé par Monte Carlo et Longstaff-Schwartz.

### 3. `Ncdf()` — fonction de répartition de la loi normale

```python
def Ncdf(x):
    """Fonction de répartition N(x) de la loi normale centrée réduite."""
    return NormalDist().cdf(x)
```

- Les trois lignes de commentaires `# === Fonctions maths ===` ouvrent la première section du fichier.
- `def Ncdf(x):` : N(x), la probabilité qu'une variable normale centrée réduite soit inférieure à x. C'est le N(d1), N(d2) des formules de Black-Scholes.
- `return NormalDist().cdf(x)` : `NormalDist()` crée une loi normale de moyenne 0 et d'écart-type 1 ; `.cdf` (*cumulative distribution function*) calcule la fonction de répartition.
- **Limite :** `NormalDist().cdf` travaille sur un seul nombre, pas sur un tableau NumPy. C'est suffisant ici car Black-Scholes est appelé pour un seul jeu de paramètres à la fois. Pour pricer 10 000 options d'un coup, il faudrait `scipy.special.ndtr`, vectorisé.

### 4. `Npdf()` — densité de la loi normale

```python
def Npdf(x):
    """Densité n(x) de la loi normale centrée réduite."""
    return NormalDist().pdf(x)
```

- `def Npdf(x):` : n(x) = e^(−x²/2)/√(2π), la densité de la loi normale centrée réduite.
- `return NormalDist().pdf(x)` : `.pdf` (*probability density function*). Elle apparaît dans toutes les grecques : c'est la dérivée de N.

### 5. `_d1_d2()` — les deux quantités de Black-Scholes

```python
def _d1_d2(S0, K, T, r, q, sigma):
    """Calcule d1 et d2, que j'utilise dans Black-Scholes et toutes les grecques."""
    d1 = (np.log(S0 / K) + (r - q + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2
```

- Le `_` en tête du nom signale une fonction **interne** au fichier : elle n'est pas destinée à être appelée depuis `main.py`.
- `d1 = (np.log(S0 / K) + (r - q + sigma**2 / 2) * T) / (sigma * np.sqrt(T))` : la formule de d1 avec dividende continu. `np.log(S0 / K)` mesure l'éloignement du spot au strike (la *moneyness*), `(r − q + σ²/2)·T` la dérive, et `σ·√T` l'écart-type du log-rendement jusqu'à maturité.
- `d2 = d1 - sigma * np.sqrt(T)` : d2 se déduit de d1.
- `return d1, d2` : on renvoie les deux à la fois (un tuple).
- **Pourquoi une fonction à part ?** d1 et d2 servent dans **toutes** les formules (prix, grecques, digitales). Les calculer à un seul endroit évite de les recopier, et donc d'introduire une faute de frappe dans une des copies.
- **Lecture économique :** N(d2) est la probabilité risque-neutre que le call finisse dans la monnaie ; S0·e^(−qT)·N(d1) est la valeur actuelle de l'action reçue dans ce cas.

### 6. `black_scholes()` — prix d'une option européenne

```python
def black_scholes(S0, K, T, r, q, sigma, option_type):
    """Prix d'une option européenne par Black-Scholes, avec dividende continu q.

    Paramètres : S0, K, T, r, q, sigma, option_type ("call" ou "put").
    Renvoie : le prix de l'option.
    """
    d1, d2 = _d1_d2(S0, K, T, r, q, sigma)

    if option_type == "call":
        prix = S0 * np.exp(-q*T) * Ncdf(d1) - K * np.exp(-r*T) * Ncdf(d2)
    else:
        prix = K * np.exp(-r*T) * Ncdf(-d2) - S0 * np.exp(-q*T) * Ncdf(-d1)

    return prix
```

- La bannière `# === BLACK-SCHOLES ===` ouvre la section.
- **Docstring** : paramètres et valeur renvoyée.
- `d1, d2 = _d1_d2(S0, K, T, r, q, sigma)` : on récupère les deux quantités (« déballage » du tuple).
- `if option_type == "call":` : le type d'option a déjà été vérifié par `validation.py` (seulement `"call"` ou `"put"`), donc le `else` couvre forcément le put.
- `prix = S0 * np.exp(-q*T) * Ncdf(d1) - K * np.exp(-r*T) * Ncdf(d2)` : formule du call avec **dividende continu q** (modèle de Merton). On remplace S0 par S0·e^(−qT), car l'action « perd » des dividendes que le détenteur de l'option ne touche pas. Le second terme est le strike actualisé, pondéré par la probabilité d'exercice.
- `prix = K * np.exp(-r*T) * Ncdf(-d2) - S0 * np.exp(-q*T) * Ncdf(-d1)` : formule du put, avec N(−d) = 1 − N(d). On aurait pu passer par la parité call-put, mais la formule directe évite de soustraire deux grands nombres (perte de précision pour les options très en dehors de la monnaie).
- `return prix` : le prix pour une option (une unité de sous-jacent).
- **Vérification pour un étudiant :** call − put doit valoir S0·e^(−qT) − K·e^(−rT) (parité call-put).

### 7. `_simuler_ST()` — simuler le prix final

```python
def _simuler_ST(S0, T, r, q, sigma, n_simulations, seed):
    """Simule directement S_T : une européenne ne dépend que du prix final."""
    rng = np.random.default_rng(seed)
    return simuler_cours_observations(S0, r, q, sigma, [T], n_simulations, rng)[:, 1]
```

- La bannière `# === MONTE CARLO EUROPÉEN ===` ouvre la section des deux Monte Carlo européens (option vanille et digitale), qui partagent les mêmes briques.
- `rng = np.random.default_rng(seed)` : un générateur avec graine ; la même graine redonne exactement les mêmes tirages, donc le même prix.
- `return simuler_cours_observations(S0, r, q, sigma, [T], n_simulations, rng)[:, 1]` : on appelle le simulateur commun avec **une seule date d'observation, la maturité** `[T]`. Une européenne ne dépend que du prix final : inutile de simuler les jours intermédiaires, et la formule est exacte. Le simulateur renvoie une matrice à deux colonnes (aujourd'hui, maturité) ; `[:, 1]` garde la colonne de la maturité.
- **Historique :** avant le nettoyage des doublons, `monte_carlo` avait sa propre simulation, sans graine et sans intervalle de confiance. C'est le schéma de la digitale, plus complet, qui a été généralisé.

### 8. `_resultat_monte_carlo()` — prix et intervalle de confiance

```python
def _resultat_monte_carlo(flux):
    """Prix, écart-type des flux actualisés, erreur standard et IC normal à 95 %."""
    prix = float(np.mean(flux))
    ecart_type = float(np.std(flux, ddof=1))
    erreur_standard = ecart_type/np.sqrt(len(flux))
    return {"price": prix, "ecart_type": ecart_type,
            "erreur_standard": float(erreur_standard),
            "ic95": [prix-1.96*erreur_standard, prix+1.96*erreur_standard]}
```

- `flux` : un tableau contenant, pour chaque trajectoire, le paiement déjà **actualisé**.
- `prix = float(np.mean(flux))` : le prix Monte Carlo est la moyenne des flux actualisés (définition du prix risque-neutre). `float(...)` transforme le nombre NumPy en nombre Python, que `jsonify` sait envoyer au navigateur.
- `ecart_type = float(np.std(flux, ddof=1))` : écart-type **empirique** ; `ddof=1` divise par n − 1 au lieu de n (estimateur non biaisé).
- `erreur_standard = ecart_type/np.sqrt(len(flux))` : l'erreur du prix Monte Carlo diminue en 1/√N. Diviser l'erreur par 2 demande 4 fois plus de simulations.
- `return {...}` : un dictionnaire avec le prix, l'écart-type, l'erreur standard et l'**intervalle de confiance à 95 %** : prix ± 1,96 × erreur standard. C'est lui qui permet de dire si un écart avec Black-Scholes est du bruit ou une erreur.

### 9. `monte_carlo()` — option européenne par simulation

```python
def monte_carlo(S0, K, T, r, q, sigma, option_type, n_simulations, seed=None):
    """Prix d'une option européenne par Monte Carlo, avec son intervalle de confiance.

    Le résultat doit être proche de Black-Scholes : l'IC95 permet de le vérifier.
    seed permet de retrouver exactement le même prix.
    """
    ST = _simuler_ST(S0, T, r, q, sigma, n_simulations, seed)
    payoff = np.maximum(ST - K, 0) if option_type == "call" else np.maximum(K - ST, 0)
    return _resultat_monte_carlo(np.exp(-r*T)*payoff)
```

- **Docstring** : le résultat doit être proche de Black-Scholes, et l'IC95 permet de le vérifier ; `seed` permet de retrouver exactement le même prix.
- `ST = _simuler_ST(S0, T, r, q, sigma, n_simulations, seed)` : un prix final par trajectoire.
- `payoff = np.maximum(ST - K, 0) if option_type == "call" else np.maximum(K - ST, 0)` : le payoff de chaque trajectoire, calculé sans boucle. `np.maximum` compare élément par élément avec 0.
- `return _resultat_monte_carlo(np.exp(-r*T)*payoff)` : on actualise chaque payoff au taux sans risque, puis on calcule moyenne et IC95.
- **Pourquoi garder Monte Carlo alors que Black-Scholes donne la réponse exacte ?** Pour l'enseignement : comparer les deux montre la convergence en 1/√N, et prépare aux produits structurés où aucune formule fermée n'existe.

### 10. `digital_monte_carlo()` — digitale par simulation

```python
def digital_monte_carlo(S0, K, T, r, q, sigma, option_type, n_simulations,
                        payout=1.0, seed=None, digital_type="cash"):
    """Prix Monte Carlo d'une digitale, avec son intervalle de confiance.

    payout ne concerne que la cash-or-nothing ; l'asset-or-nothing livre S_T.
    """
    ST = _simuler_ST(S0, T, r, q, sigma, n_simulations, seed)
    condition = ST > K if option_type == "call" else ST < K
    flux = np.exp(-r*T)*condition*(ST if digital_type == "asset" else payout)
    return _resultat_monte_carlo(flux)
```

- Mêmes briques que `monte_carlo` : seul le payoff change.
- `ST = _simuler_ST(...)` : les prix finaux.
- `condition = ST > K if option_type == "call" else ST < K` : un tableau de booléens (`True` si l'option finit dans la monnaie). Inégalité **stricte** : le cas S_T = K a une probabilité nulle, mais il faut une convention, la même que celle du graphe dans `main.py`.
- `flux = np.exp(-r*T)*condition*(ST if digital_type == "asset" else payout)` : multiplier par un booléen vaut 0 ou 1. Une **cash-or-nothing** paie le montant fixe `payout` ; une **asset-or-nothing** livre le sous-jacent, donc paie `ST`. Le tout est actualisé.
- `return _resultat_monte_carlo(flux)` : prix et IC95.

### 11. `longstaff_schwartz()` — option américaine

```python
def longstaff_schwartz(S0, K, T, r, q, sigma, option_type, n_simulations, n_steps=100, seed=None):
    """Prix d'une option américaine par Longstaff-Schwartz.

    Je simule les chemins complets sur n_steps dates, puis je remonte le temps :
    à chaque date, je compare le payoff d'exercice immédiat avec la valeur de
    continuation, que j'estime par une régression polynomiale de degré 2 sur
    les chemins dans la monnaie.
    Renvoie : le prix, avec au minimum la valeur d'exercice immédiat.
    """
    dt = T / n_steps

    # chemins complets (ici j'ai besoin de toutes les dates), avec le simulateur commun
    dates = np.arange(1, n_steps + 1) * dt
    prix = simuler_cours_observations(S0, r, q, sigma, dates, n_simulations,
                                      np.random.default_rng(seed))

    # je calcule le payoff d'exercice à chaque date
    if option_type == "call":
        payoff = np.maximum(prix - K, 0)
    else:
        payoff = np.maximum(K - prix, 0)

    # au départ je suppose qu'on exerce à maturité
    cashflow = payoff[:, -1]

    # je remonte dans le temps
    for t in range(n_steps - 1, 0, -1):

        cashflow *= np.exp(-r * dt)  # je ramène les flux d'une période

        # je fais la régression seulement sur les chemins dans la monnaie
        itm = payoff[:, t] > 0

        if np.sum(itm) > 2:

            X = prix[itm, t]
            Y = cashflow[itm]

            # je standardise X sinon polyfit est instable (grands nombres au carré)
            X_norm = (X - X.mean()) / X.std()

            # j'estime la valeur de continuation avec un polynôme de degré 2
            regression = np.polyfit(X_norm, Y, 2)
            continuation = np.polyval(regression, X_norm)

            # j'exerce si le payoff immédiat est mieux que continuer
            exercice = payoff[itm, t] > continuation

            indices = np.where(itm)[0]
            cashflow[indices[exercice]] = payoff[indices[exercice], t]

    prix_lsm = np.mean(cashflow) * np.exp(-r * dt)

    # une américaine vaut au moins son exercice immédiat, je mets ce plancher
    return max(prix_lsm, payoff[0, 0])
```

Une américaine peut être exercée à tout moment : il faut décider, à chaque date, s'il vaut mieux exercer ou attendre. Longstaff-Schwartz (2001) estime la **valeur d'attente** par régression.

**Préparation**
- `dt = T / n_steps` : on découpe la vie de l'option en 100 dates (valeur par défaut de `n_steps`) ; c'est une approximation de l'exercice continu.
- `dates = np.arange(1, n_steps + 1) * dt` : les dates dt, 2dt, …, T. `np.arange(1, n+1)` donne 1, 2, …, n.
- `prix = simuler_cours_observations(..., dates, n_simulations, np.random.default_rng(seed))` : ici on a besoin de **tout le chemin**, car l'exercice peut arriver n'importe quand. Le simulateur commun avec graine rend le prix américain reproductible. Mémoire : 30 000 × 101 × 8 octets ≈ 24 Mo, c'est pour ça que `n_steps` reste modeste.

**Payoff d'exercice**
- `payoff = np.maximum(prix - K, 0)` (call) ou `np.maximum(K - prix, 0)` (put) : la valeur d'un exercice immédiat, pour chaque trajectoire et **chaque date** (toute la matrice d'un coup).
- `cashflow = payoff[:, -1]` : point de départ : on suppose qu'on exerce à maturité. `[:, -1]` = dernière colonne.

**Remontée dans le temps**
- `for t in range(n_steps - 1, 0, -1):` : on part de l'avant-dernière date et on recule jusqu'à la date 1 (`range` avec un pas de −1).
- `cashflow *= np.exp(-r * dt)` : chaque flux est ramené d'une période en arrière (actualisation).
- `itm = payoff[:, t] > 0` : les trajectoires **dans la monnaie** à cette date. Hors de la monnaie, exercer ne rapporte rien : on ne les inclut pas dans la régression (recommandation de l'article original, qui améliore l'estimation).
- `if np.sum(itm) > 2:` : il faut au moins 3 points pour ajuster un polynôme de degré 2.
- `X = prix[itm, t]` et `Y = cashflow[itm]` : les prix du jour (variable explicative) et les flux futurs actualisés (variable expliquée) des trajectoires dans la monnaie.
- `X_norm = (X - X.mean()) / X.std()` : **problème rencontré** : avec des prix de l'ordre de 300, X² ≈ 90 000 ; `np.polyfit` devenait mal conditionné et le prix sautait d'un calcul à l'autre. **Contournement** : standardiser X (moyenne 0, écart-type 1) avant la régression.
- `regression = np.polyfit(X_norm, Y, 2)` : ajuste un polynôme de degré 2 (a·x² + b·x + c) par moindres carrés.
- `continuation = np.polyval(regression, X_norm)` : la valeur d'attente estimée pour chaque trajectoire.
- `exercice = payoff[itm, t] > continuation` : on exerce si l'exercice immédiat rapporte plus que l'attente estimée.
- `indices = np.where(itm)[0]` : les numéros des trajectoires dans la monnaie dans le tableau complet. Nécessaire car `exercice` ne concerne que ces trajectoires.
- `cashflow[indices[exercice]] = payoff[indices[exercice], t]` : pour les trajectoires qui exercent, le flux devient le payoff immédiat (les flux futurs sont abandonnés).

**Prix final**
- `prix_lsm = np.mean(cashflow) * np.exp(-r * dt)` : dernière actualisation de la date 1 vers aujourd'hui, puis moyenne.
- `return max(prix_lsm, payoff[0, 0])` : **plancher** : une américaine vaut toujours au moins son exercice immédiat. `payoff[0, 0]` est justement le payoff en t = 0 (colonne 0 = S0), déjà calculé. Le bruit Monte Carlo pourrait sinon donner un prix inférieur pour une option très dans la monnaie.

**Limites :** base polynomiale de degré 2 seulement (le choix de base influence le prix), 100 dates d'exercice (approximation du continu), estimateur légèrement biaisé vers le bas (règle d'exercice sous-optimale).

### 12. `grecs_primaires_bs()` — grecques du premier ordre

```python
def grecs_primaires_bs(S0, K, T, r, q, sigma, option_type):
    """Grecques primaires Black-Scholes (avec dividende q).

    Renvoie : un dict {Delta, Gamma, Vega, Theta, Rho}.
    Vega et Rho sont pour une variation de 1 (100 %) de sigma ou de r,
    Theta est annuel.
    """
    d1, d2 = _d1_d2(S0, K, T, r, q, sigma)

    # delta : sensibilité au spot
    if option_type == "call":
        Delta = np.exp(-q*T)*Ncdf(d1)
    else:
        Delta = np.exp(-q*T)*(Ncdf(d1)-1)

    # gamma : variation du delta, pareil pour call et put
    Gamma = np.exp(-q*T)*Npdf(d1)/(S0*sigma*np.sqrt(T))

    # vega : sensibilité à la vol, pareil pour call et put
    Vega = S0*np.exp(-q*T)*Npdf(d1)*np.sqrt(T)

    # theta : perte de valeur avec le temps (par an)
    if option_type == "call":
        Theta = -(S0*sigma*np.exp(-q*T)*Npdf(d1))/(2*np.sqrt(T)) - r*K*np.exp(-r*T)*Ncdf(d2) + q*S0*np.exp(-q*T)*Ncdf(d1)
    else:
        Theta = -(S0*sigma*np.exp(-q*T)*Npdf(d1))/(2*np.sqrt(T)) + r*K*np.exp(-r*T)*Ncdf(-d2) - q*S0*np.exp(-q*T)*Ncdf(-d1)

    # rho : sensibilité aux taux
    if option_type == "call":
        Rho = K*T*np.exp(-r*T)*Ncdf(d2)
    else:
        Rho = -K*T*np.exp(-r*T)*Ncdf(-d2)

    return {"Delta": Delta, "Gamma": Gamma, "Vega": Vega, "Theta": Theta, "Rho": Rho}
```

- La bannière `# === Grecques primaires ===` ouvre la section.
- **Docstring — piège d'unités :** Vega et Rho sont pour une variation de **1,00** (100 points de vol ou de taux) ; pour « 1 point », diviser par 100. Theta est **annuel** ; pour un theta par jour, diviser par 365 (calendaire) ou 252 (ouvré).
- `d1, d2 = _d1_d2(...)` : les deux quantités communes.
- **Delta** (∂V/∂S, sensibilité au spot) : `np.exp(-q*T)*Ncdf(d1)` pour un call, `np.exp(-q*T)*(Ncdf(d1)-1)` pour un put. Un delta de 0,6 signifie que l'option gagne ≈ 0,6 quand le spot gagne 1.
- **Gamma** (∂²V/∂S², variation du delta) : `np.exp(-q*T)*Npdf(d1)/(S0*sigma*np.sqrt(T))`. Identique pour call et put (la parité call-put l'annule).
- **Vega** (∂V/∂σ) : `S0*np.exp(-q*T)*Npdf(d1)*np.sqrt(T)`. Identique pour call et put.
- **Theta** (∂V/∂t, perte de valeur avec le temps) : trois termes. Le premier, `−S·σ·e^(−qT)·n(d1)/(2√T)`, est l'érosion due au temps ; le deuxième vient du strike actualisé (`r·K·e^(−rT)·N(±d2)`) ; le troisième du dividende (`q·S·e^(−qT)·N(±d1)`). Les signes s'inversent entre call et put.
- **Rho** (∂V/∂r) : `K*T*np.exp(-r*T)*Ncdf(d2)` pour un call, l'opposé avec N(−d2) pour un put. Un call gagne quand les taux montent (le strike actualisé baisse).
- `return {...}` : un dictionnaire, lu par `main.py` et affiché dans l'ordre imposé par l'interface.

### 13. `grecs_secondaires_bs()` — grecques du second ordre

```python
def grecs_secondaires_bs(S0, K, T, r, q, sigma, option_type):
    """Grecques secondaires Black-Scholes.

    Renvoie : un dict {Vanna, Vomma, Charm, Color, Speed, Zomma, Ultima, Lambda}.
    Lambda = élasticité de l'option (Delta x S0 / prix).
    """
    d1, d2 = _d1_d2(S0, K, T, r, q, sigma)
    # Delta, Gamma et Vega viennent des grecques primaires (une seule formule par grecque)
    primaires = grecs_primaires_bs(S0, K, T, r, q, sigma, option_type)
    Delta, Gamma, Vega = primaires["Delta"], primaires["Gamma"], primaires["Vega"]

    # vanna : delta par rapport à la vol
    Vanna = (-np.exp(-q*T)*Npdf(d1)*d2)/sigma

    # vomma : vega par rapport à la vol
    Vomma = (Vega*d1*d2)/sigma

    # charm : delta par rapport au temps
    if option_type == "call":
        Charm = q*np.exp(-q*T)*Ncdf(d1)-np.exp(-q*T)*Npdf(d1)*(2*(r-q)*T - d2*sigma*np.sqrt(T)) / (2*T*sigma*np.sqrt(T))
    else:
        Charm = -q*np.exp(-q*T)*Ncdf(-d1)-np.exp(-q*T)*Npdf(d1)*(2*(r-q)*T-d2*sigma*np.sqrt(T))/(2*T*sigma*np.sqrt(T))

    # color : gamma par rapport au temps
    Color = -np.exp(-q*T)*Npdf(d1)/(2*S0*T*sigma*np.sqrt(T))*(2*q*T+1+(2*(r-q)*T-d2*sigma*np.sqrt(T)))*d1/(sigma*np.sqrt(T))

    # speed : gamma par rapport au spot
    Speed = -Gamma/S0*(d1/(sigma*np.sqrt(T))+1)

    # zomma : gamma par rapport à la vol / ultima : vomma par rapport à la vol
    Zomma = Gamma*(d1*d2-1)/sigma
    Ultima = -Vega*(d1*d2*(1-d1*d2)+d1**2+d2**2)/sigma**2

    # lambda : élasticité (effet de levier de l'option)
    Lambda = Delta * S0 / black_scholes(S0, K, T, r, q, sigma, option_type)

    return {"Vanna": Vanna, "Vomma": Vomma, "Charm": Charm, "Color": Color,
            "Speed": Speed, "Zomma": Zomma, "Ultima": Ultima, "Lambda": Lambda}
```

- La bannière ouvre la section ; la docstring liste les grecques et définit Lambda.
- `d1, d2 = _d1_d2(...)` : les quantités communes.
- `primaires = grecs_primaires_bs(...)` puis `Delta, Gamma, Vega = ...` : on **réutilise** les grecques primaires. Avant le nettoyage des doublons, leurs formules étaient recopiées ici : une faute corrigée dans une copie aurait laissé l'autre fausse. Une seule formule par grecque.
- **Vanna** `(-e^(−qT)·n(d1)·d2)/σ` : variation du delta quand la vol bouge (∂Delta/∂σ).
- **Vomma** `Vega·d1·d2/σ` (aussi appelée Volga) : convexité du prix par rapport à la vol (∂Vega/∂σ). Vanna et Volga servent à pricer le smile (méthode « vanna-volga » sur le marché des changes).
- **Charm** : dérive du delta avec le temps (∂Delta/∂t) ; dit par exemple comment le delta bouge pendant un week-end. Formule différente pour call et put à cause du terme de dividende.
- **Color** : variation du gamma avec le temps (∂Gamma/∂t).
- **Speed** `−Gamma/S0·(d1/(σ√T) + 1)` : variation du gamma avec le spot (∂Gamma/∂S).
- **Zomma** `Gamma·(d1·d2 − 1)/σ` : variation du gamma avec la vol (∂Gamma/∂σ).
- **Ultima** : variation de la vomma avec la vol (∂Vomma/∂σ), troisième dérivée par rapport à σ.
- **Lambda** `Delta·S0/prix` : l'**élasticité**, ou effet de levier de l'option. Si Lambda = 8, une hausse de 1 % du sous-jacent fait gagner ≈ 8 % sur la prime. **Limite** : on divise par le prix ; pour une option très en dehors de la monnaie (prix ≈ 0), le chiffre explose et n'a plus de sens.
- `return {...}` : les huit grecques.

### 14. `forward_price()` — prix à terme

```python
def forward_price(S0, T, r, q):
    """Prix à terme théorique : F = S0 x e^((r - q) T)."""
    return S0*np.exp((r-q)*T)
```

- La bannière `# === Futures / Forward ===` ouvre la section.
- `return S0*np.exp((r-q)*T)` : prix de **portage**. Acheter l'action aujourd'hui coûte le financement (r) mais rapporte les dividendes (q) ; par absence d'arbitrage, F = S0·e^((r−q)T). Dans ce modèle à taux constants, le prix d'un future est égal à celui d'un forward.

### 15. `forward_value()` — valeur d'un contrat déjà signé

```python
def forward_value(S0, K, T, r, q, side):
    """Valeur aujourd'hui d'un forward déjà signé au prix K.

    side = "buy" ou "sell". Renvoie (F - K) actualisé pour l'acheteur,
    l'inverse pour le vendeur.
    """
    sign = 1 if side == "buy" else -1
    return sign*(forward_price(S0, T, r, q)-K)*np.exp(-r*T)
```

- **Docstring** : un forward signé au prix K vaut, aujourd'hui, la différence entre le prix à terme actuel F et K, actualisée.
- `sign = 1 if side == "buy" else -1` : l'acheteur gagne si F > K, le vendeur dans le cas inverse. Le signe évite d'écrire deux formules.
- `return sign*(forward_price(S0, T, r, q)-K)*np.exp(-r*T)` : (F − K) actualisé, avec le signe du sens. À la signature, K = F et la valeur est nulle : on n'échange pas de prime.

### 16. `forward_payoff()` — payoff à maturité

```python
def forward_payoff(ST, K, side):
    """Payoff à maturité d'un forward : S_T - K si long, K - S_T si short.

    ST peut être un nombre ou toute une grille numpy.
    """
    sign = 1 if side == "buy" else -1
    return sign*(np.asarray(ST, dtype=float)-K)
```

- `sign = 1 if side == "buy" else -1` : même logique de signe.
- `return sign*(np.asarray(ST, dtype=float)-K)` : S_T − K pour l'acheteur, K − S_T pour le vendeur. Un payoff **linéaire**, contrairement à une option. `np.asarray(ST, dtype=float)` accepte aussi bien un nombre qu'une grille entière : `main.py` passe directement les 121 points du graphe, sans boucle.

### 17. `make_position()` — une jambe option

```python
def make_position(option_type, side, K, T, qty=1):
    """Construit une jambe option (long ou short, call ou put)."""
    return {"instrument": "option", "option_type": option_type, "side": side,
            "K": K, "T": T, "qty": qty}
```

- La bannière `# === Legs ===` ouvre la partie des **stratégies** : une stratégie est une liste de « jambes » (*legs*).
- `return {"instrument": "option", "option_type": ..., "side": ..., "K": ..., "T": ..., "qty": ...}` : une jambe est un simple **dictionnaire**. C'est simple, lisible, et facile à transformer en JSON. Une classe `Leg` aurait été plus formelle (c'est ce qu'on ferait en C#), mais pour un projet pédagogique le dictionnaire montre directement les données.
- `qty=1` : valeur par défaut ; on peut acheter plusieurs options.

### 18. `make_stock_position()` — une jambe action

```python
def make_stock_position(side, qty=1):
    """Construit une jambe action (pas de strike ni de maturité)."""
    return {"instrument": "stock", "side": side, "qty": qty}
```

- `return {"instrument": "stock", "side": side, "qty": qty}` : une action n'a ni strike ni maturité. Elle sert au covered call, au protective put et au collar.

### 19. `_signe()` — le sens d'une jambe

```python
def _signe(leg):
    """+1 pour une jambe achetée, -1 pour une jambe vendue."""
    return 1 if leg["side"] == "buy" else -1
```

- `return 1 if leg["side"] == "buy" else -1` : +1 pour une jambe achetée, −1 pour une jambe vendue. C'est **l'idée clé** des stratégies : acheter = coût positif et payoff positif ; vendre = prime encaissée (coût négatif) et payoff négatif. Toute la stratégie devient une **somme signée**. Cette petite fonction est écrite une fois et utilisée par le prix, le payoff et les grecques.

### 20. `price_leg()` — coût d'une jambe

```python
def price_leg(leg, S0, r, q, sigma):
    """Coût d'une jambe aujourd'hui, avec le signe.

    Positif si j'achète, négatif si je vends (j'encaisse la prime).
    """
    if leg["instrument"] == "stock":
        prix_unitaire = S0
    else:
        prix_unitaire = black_scholes(S0, leg["K"], leg["T"], r, q, sigma, leg["option_type"])
    return _signe(leg) * leg["qty"] * prix_unitaire
```

- `if leg["instrument"] == "stock": prix_unitaire = S0` : une action coûte son spot.
- `else: prix_unitaire = black_scholes(...)` : une option coûte son prix Black-Scholes, avec le strike et la maturité de la jambe.
- `return _signe(leg) * leg["qty"] * prix_unitaire` : coût signé × quantité. Positif si on achète, négatif si on vend (on encaisse la prime).

### 21. `payoff_leg()` — payoff d'une jambe

```python
def payoff_leg(leg, ST):
    """Payoff à maturité d'une jambe, sur toute la grille de S_T (tableau numpy)."""
    if leg["instrument"] == "stock":
        payoff = ST
    elif leg["option_type"] == "call":
        payoff = np.maximum(ST - leg["K"], 0)
    else:
        payoff = np.maximum(leg["K"] - ST, 0)
    return _signe(leg) * leg["qty"] * payoff
```

- La bannière `# === Payoffs ===` ouvre la section.
- `ST` est **toute la grille** des prix finaux (un tableau NumPy) : on calcule le payoff de la jambe en chaque point d'un coup.
- action : `payoff = ST` (on détient l'action, qui vaut S_T) ; call : `np.maximum(ST - leg["K"], 0)` ; put : `np.maximum(leg["K"] - ST, 0)`.
- `return _signe(leg) * leg["qty"] * payoff` : payoff signé × quantité.

### 22. `payoff_strategie()` — payoff et P&L de la stratégie

```python
def payoff_strategie(legs, S0, r, q, sigma, ST_grid):
    """Payoff et P&L de toute la stratégie sur la grille de S_T.

    Je fais la somme des jambes. P&L = payoff total - coût total de mise en place.
    Renvoie : un dict {payoff, pnl}.
    """
    payoff_total = sum(payoff_leg(leg, ST_grid) for leg in legs)
    cout_total = sum(price_leg(leg, S0, r, q, sigma) for leg in legs)
    return {"payoff": payoff_total, "pnl": payoff_total - cout_total}
```

- `payoff_total = sum(payoff_leg(leg, ST_grid) for leg in legs)` : on additionne les payoffs de toutes les jambes. `sum(... for ...)` additionne directement des tableaux NumPy, point par point.
- `cout_total = sum(price_leg(leg, S0, r, q, sigma) for leg in legs)` : le coût de mise en place (somme signée des primes).
- `return {"payoff": payoff_total, "pnl": payoff_total - cout_total}` : le P&L à maturité = payoff − coût. On néglige le financement de la prime jusqu'à maturité (choix pédagogique, à mentionner si on compare avec un vrai P&L).
- **Limite :** une seule volatilité pour toutes les jambes (pas de smile). `main.py` refuse d'ailleurs explicitement un champ `leg_vols`.

### 23. `greeks_strategie()` — grecques agrégées

```python
def greeks_strategie(legs, S0, r, q, sigma):
    """Grecques primaires de la stratégie.

    J'additionne les grecques de chaque jambe avec leur signe. Une action
    apporte juste un delta de 1.
    Renvoie : un dict {Delta, Gamma, Vega, Theta, Rho}.
    """
    total = {"Delta": 0, "Gamma": 0, "Vega": 0, "Theta": 0, "Rho": 0}
    for leg in legs:
        poids = _signe(leg) * leg["qty"]
        if leg["instrument"] == "stock":
            # une action a juste un delta de 1, le reste vaut 0
            total["Delta"] += poids
        else:
            grecs = grecs_primaires_bs(S0, leg["K"], leg["T"], r, q, sigma, leg["option_type"])
            for cle in total:
                total[cle] += poids * grecs[cle]
    return total
```

- `total = {"Delta": 0, ..., "Rho": 0}` : un compteur par grecque.
- `for leg in legs:` puis `poids = _signe(leg) * leg["qty"]` : le poids de chaque jambe.
- `if leg["instrument"] == "stock": total["Delta"] += poids` : une action a un delta de 1 et toutes les autres grecques nulles.
- `else: grecs = grecs_primaires_bs(...)` puis `for cle in total: total[cle] += poids * grecs[cle]` : on ajoute les cinq grecques de l'option, pondérées. La boucle sur les clés évite cinq lignes recopiées.
- `return total` : les grecques de la stratégie entière ; par exemple, un straddle acheté à la monnaie a un delta proche de 0 mais un vega fortement positif.

### 24. `make_covered_call()` et les constructeurs de stratégies

```python
def make_covered_call(K, T, qty=1):
    """Covered call : achat de l'action + vente d'un call de strike K."""
    return [make_stock_position("buy", qty=qty), make_position("call", "sell", K, T, qty=qty)]
```

- La bannière `# === Stratégies ===` ouvre la section. Chaque constructeur renvoie la **liste des jambes** d'une stratégie classique.
- **Covered call** : `[make_stock_position("buy"), make_position("call", "sell", K, T)]` : on détient l'action et on vend un call. Vue neutre à légèrement haussière : on encaisse une prime en renonçant à la hausse au-delà de K.

### 25. `make_protective_put()`

```python
def make_protective_put(K, T, qty=1):
    """Protective put : achat de l'action + achat d'un put de strike K (assurance contre la baisse)."""
    return [make_stock_position("buy", qty=qty), make_position("put", "buy", K, T, qty=qty)]
```

- `[action achetée, put acheté de strike K]` : on est haussier mais **assuré** contre la baisse sous K. La prime du put est le coût de l'assurance.

### 26. `make_straddle()`

```python
def make_straddle(K, T, side="buy", qty=1):
    """Straddle : call + put de même strike K, même sens (pari sur la vol)."""
    return [make_position("call", side, K, T, qty=qty), make_position("put", side, K, T, qty=qty)]
```

- `[call K, put K]`, **même sens** (`side`) pour les deux : à l'achat, pari sur un gros mouvement dans un sens ou dans l'autre (achat de volatilité) ; à la vente, pari sur le calme.

### 27. `make_strangle()`

```python
def make_strangle(K_put, K_call, T, side="buy", qty=1):
    """Strangle : call K_call + put K_put (K_put < K_call), même sens. Moins cher qu'un straddle."""
    return [make_position("call", side, K_call, T, qty=qty), make_position("put", side, K_put, T, qty=qty)]
```

- `[call K_call, put K_put]` avec K_put < K_call, même sens : comme le straddle, en moins cher, mais il faut un plus gros mouvement pour gagner.

### 28. `make_call_spread()`

```python
def make_call_spread(K1, K2, T, qty=1):
    """Bull call spread : achat call K1 + vente call K2, avec K1 < K2."""
    return [make_position("call", "buy", K1, T, qty=qty), make_position("call", "sell", K2, T, qty=qty)]
```

- `[call K1 acheté, call K2 vendu]` avec K1 < K2 : vue haussière à gain plafonné ; moins cher qu'un call seul, car la vente du call K2 finance une partie de la prime.

### 29. `make_put_spread()`

```python
def make_put_spread(K1, K2, T, qty=1):
    """Bear put spread : achat put K1 + vente put K2, avec K1 > K2."""
    return [make_position("put", "buy", K1, T, qty=qty), make_position("put", "sell", K2, T, qty=qty)]
```

- `[put K1 acheté, put K2 vendu]` avec K1 > K2 : vue baissière à gain plafonné.

### 30. `make_collar()`

```python
def make_collar(K_put, K_call, T, qty=1):
    """Collar : achat de l'action + achat put K_put + vente call K_call (K_put < K_call)."""
    return [make_stock_position("buy", qty=qty),
            make_position("put", "buy", K_put, T, qty=qty),
            make_position("call", "sell", K_call, T, qty=qty)]
```

- `[action achetée, put K_put acheté, call K_call vendu]` : la protection contre la baisse (le put) est financée par la vente du potentiel de hausse (le call). La liste est écrite sur plusieurs lignes pour rester lisible.

### 31. `digital_bs()` — digitale cash-or-nothing

```python
def digital_bs(S0, K, T, r, q, sigma, option_type, payout=1.0):
    """Prix cash-or-nothing : paiement fixe à maturité si strictement dans la monnaie."""
    _, d2 = _d1_d2(S0, K, T, r, q, sigma)
    signe = 1 if option_type == "call" else -1
    return payout * np.exp(-r*T) * Ncdf(signe*d2)
```

- La bannière `# === Digitales ===` ouvre la section.
- **Le produit :** on reçoit le montant fixe `payout` à maturité si l'option finit **strictement** dans la monnaie (S_T > K pour un call).
- `_, d2 = _d1_d2(...)` : seul d2 sert ; le `_` est la convention Python pour « valeur ignorée ».
- `signe = 1 if option_type == "call" else -1` : N(d2) pour un call, N(−d2) pour un put, sans dupliquer la formule.
- `return payout * np.exp(-r*T) * Ncdf(signe*d2)` : montant actualisé × probabilité risque-neutre de finir dans la monnaie.

### 32. `asset_or_nothing_bs()` — digitale asset-or-nothing

```python
def asset_or_nothing_bs(S0, K, T, r, q, sigma, option_type):
    """Prix asset-or-nothing : livraison de S_T si strictement dans la monnaie."""
    d1, _ = _d1_d2(S0, K, T, r, q, sigma)
    signe = 1 if option_type == "call" else -1
    return S0 * np.exp(-q*T) * Ncdf(signe*d1)
```

- **Le produit :** on reçoit l'action (qui vaut S_T) si l'option finit dans la monnaie.
- `d1, _ = _d1_d2(...)` : seul d1 sert.
- `return S0 * np.exp(-q*T) * Ncdf(signe*d1)` : valeur actuelle de l'action reçue, pondérée par N(±d1).
- **Lien avec le call vanille :** call = asset-or-nothing − K × cash-or-nothing (de paiement 1). C'est cette décomposition qui sert aux grecques ci-dessous.

### 33. `grecs_digital_bs()` — grecques des digitales

```python
def grecs_digital_bs(S0, K, T, r, q, sigma, option_type, payout=1.0,
                     digital_type="cash"):
    """Grecques fermées : Vega/Rho pour 1 unité, Theta annuel = -dV/dT.

    Le gamma et le vega cash-or-nothing changent de signe selon le spot.
    Pour l'asset, j'utilise l'identité asset = vanille + K*cash (call),
    ou K*cash - vanille (put).
    """
    d1, d2 = _d1_d2(S0, K, T, r, q, sigma)
    signe = 1 if option_type == "call" else -1
    racine = np.sqrt(T)
    facteur = payout*np.exp(-r*T)
    densite = Npdf(d2)
    prix = facteur*Ncdf(signe*d2)
    derivee_t = (r-q-sigma**2/2)/(sigma*racine) - d2/(2*T)
    grecs = {
        "Delta": facteur*signe*densite/(S0*sigma*racine),
        "Gamma": -facteur*signe*densite*d1/(S0**2*sigma**2*T),
        "Vega": -facteur*signe*densite*d1/sigma,
        "Theta": r*prix-facteur*signe*densite*derivee_t,
        "Rho": -T*prix+facteur*signe*densite*racine/sigma,
    }
    if digital_type == "asset":
        cash = grecs_digital_bs(S0, K, T, r, q, sigma, option_type)
        vanille = grecs_primaires_bs(S0, K, T, r, q, sigma, option_type)
        return {cle: K*cash[cle]+signe*vanille[cle] for cle in cash}
    return grecs
```

- **Docstring** : mêmes unités que les grecques vanilles ; le gamma et le vega d'une digitale **changent de signe** autour du strike.
- `d1, d2`, `signe` : comme plus haut.
- `racine = np.sqrt(T)`, `facteur = payout*np.exp(-r*T)`, `densite = Npdf(d2)`, `prix = facteur*Ncdf(signe*d2)` : des quantités intermédiaires nommées, pour que les formules restent lisibles.
- `derivee_t = (r-q-sigma**2/2)/(sigma*racine) - d2/(2*T)` : la dérivée de d2 par rapport à T, utilisée dans Theta.
- Le dictionnaire `grecs` : chaque grecque est la dérivée de e^(−rT)·N(±d2). **Delta** : la densité au strike divisée par S·σ·√T ; **Gamma** et **Vega** contiennent un facteur `−d1`, d'où le changement de signe autour du strike ; **Theta** = −∂V/∂T (un terme d'actualisation `r·prix` et un terme de dérivée de N(d2)) ; **Rho** : un terme d'actualisation `−T·prix` et un terme lié à d2.
- **Particularité pédagogique :** à l'approche de la maturité près du strike, le delta d'une digitale explose. C'est pourquoi les traders couvrent une digitale par un call spread serré.
- `if digital_type == "asset":` : pour l'asset-or-nothing, on n'écrit **pas** de nouvelles formules. On utilise l'identité asset = vanille + K·cash (call) ou K·cash − vanille (put) :
  - `cash = grecs_digital_bs(S0, K, T, r, q, sigma, option_type)` : la fonction s'appelle elle-même (récursivité) avec un paiement de 1 et le type cash par défaut ;
  - `vanille = grecs_primaires_bs(...)` : les grecques de l'option classique ;
  - `return {cle: K*cash[cle]+signe*vanille[cle] for cle in cash}` : une « compréhension de dictionnaire » qui combine les deux, grecque par grecque.
- `return grecs` : les grecques de la cash-or-nothing. Moins de code = moins d'erreurs.

---

## Exercices

1. Vérifiez la parité call-put avec `black_scholes` : call − put = S0·e^(−qT) − K·e^(−rT).
2. Comparez `monte_carlo` avec 10 000 puis 40 000 simulations : la largeur de l'IC95 est-elle bien divisée par 2 ?
3. Pricez un put américain et un put européen de mêmes paramètres : l'écart (prime d'exercice anticipé) grandit-il avec le taux r ?
4. Calculez un call spread serré (strikes 99,5 et 100,5, quantité 1/1) et comparez-le à une digitale cash de paiement 1 au strike 100.
