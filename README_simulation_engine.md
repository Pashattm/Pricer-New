# `simulation_engine.py` — le simulateur Monte Carlo commun

C'est le **seul** endroit du projet où la diffusion du sous-jacent est écrite. Tous les calculs Monte Carlo passent par lui :

| Utilisateur | Usage |
|---|---|
| `pricer_engine.monte_carlo` et `digital_monte_carlo` | Une seule date : la maturité |
| `pricer_engine.longstaff_schwartz` | 100 dates régulières (chemins complets pour l'option américaine) |
| `strutu_engine` (Phoenix, Athéna) | Les dates d'observation du produit |

**Pourquoi un fichier à part ?** Au départ, le mouvement brownien géométrique était écrit **trois fois** : dans `monte_carlo`, dans `longstaff_schwartz` et dans `strutu_engine`. Les deux premières versions utilisaient `np.random.normal` sans graine : deux clics donnaient deux prix différents. Seule la version de `strutu_engine` acceptait une graine : c'est elle qui a été gardée et déplacée ici. Autre avantage : pour accélérer tout le projet, il n'y a plus qu'une fonction à modifier.

### Le modèle simulé

Sous la probabilité risque-neutre de Black-Scholes, entre deux dates séparées de dt :

S(t + dt) = S(t) × exp[(r − q − σ²/2)·dt + σ·√dt·Z], avec Z ~ N(0, 1)

- `r − q` : le sous-jacent croît au taux sans risque moins le dividende (portage).
- `− σ²/2` : **correction d'Itô**. Sans elle, l'espérance de S serait trop haute, car E[e^(σW)] = e^(σ²t/2).
- Cette formule est **exacte** quel que soit dt : il n'y a aucune erreur de discrétisation à sauter directement d'une date à la suivante, même éloignée. C'est pourquoi on ne simule que les dates utiles.

---

# Le code, ligne par ligne
### 1. En-tête du fichier

```python
"""Simulateur commun : mouvement brownien géométrique sous la probabilité risque-neutre.

C'est le SEUL endroit du projet où la diffusion du sous-jacent est écrite.
Il est utilisé par :
- pricer_engine (Monte Carlo européen, digitales, Longstaff-Schwartz) ;
- strutu_engine (Phoenix, Athéna) ;

Convention : r, q, sigma en décimal, dates en années.
Les paramètres sont vérifiés par validation.py avant d'arriver ici.
"""
```

Le texte entre triples guillemets en tête de fichier est la **docstring du module** : Python la garde en mémoire (`simulation_engine.__doc__`) et les éditeurs l'affichent au survol.

- Elle dit ce que fait le fichier (simuler un mouvement brownien géométrique sous la probabilité risque-neutre).
- Elle liste **qui l'utilise** : c'est la carte des dépendances du projet.
- Elle rappelle les **conventions** (r, q, sigma en décimal, dates en années) : c'est la première chose à vérifier quand un prix paraît faux.
- Elle précise que les paramètres sont déjà vérifiés par `validation.py` : ce fichier ne contient donc aucun contrôle, seulement des maths.

### 2. Imports

```python
import numpy as np
```

- `import numpy as np` : NumPy fournit les tableaux et les calculs vectorisés. `np` est l'abréviation universelle ; tout le monde la reconnaît.
- C'est le seul import : le simulateur ne dépend d'aucun autre fichier du projet, ce qui évite les imports circulaires (tous les moteurs l'importent, lui n'importe personne).

### 3. `simuler_cours_observations()`

```python
def simuler_cours_observations(S0, r, q, sigma, obs_dates, n_simulations, rng=None):
    """Simule le sous-jacent uniquement aux dates d'observation.

    Sous Black-Scholes, le passage d'une date à la suivante est exact, quel que
    soit l'écart entre les dates : on ne simule que les dates utiles.

    rng   : générateur numpy (np.random.default_rng(graine)) pour des tirages reproductibles.
    Renvoie : une matrice (n_simulations, n_dates + 1), colonne 0 = S0.
    """
    if rng is None:
        rng = np.random.default_rng()

    prix = np.zeros((n_simulations, len(obs_dates) + 1))
    prix[:, 0] = S0  # tous les scénarios partent du même spot

    t_precedent = 0.0
    for i, t in enumerate(obs_dates):
        dt = t - t_precedent  # temps écoulé depuis la dernière observation
        Z = rng.standard_normal(n_simulations)
        croissance = (r - q - sigma**2 / 2) * dt   # dérive avec correction d'Itô
        choc = sigma * np.sqrt(dt) * Z
        prix[:, i + 1] = prix[:, i] * np.exp(croissance + choc)
        t_precedent = t

    return prix
```

**Signature.**
- `S0, r, q, sigma` : spot initial, taux, dividende, volatilité (en décimal).
- `obs_dates` : liste croissante des dates (en années) où l'on veut connaître le prix.
- `n_simulations` : nombre de trajectoires.
- `rng=None` : générateur aléatoire. On le **passe en paramètre** plutôt que d'utiliser l'état global de NumPy : avec `np.random.default_rng(42)`, on retrouve exactement les mêmes trajectoires à chaque appel. Indispensable pour comparer deux paramétrages et pour qu'un prix ne change pas d'un clic à l'autre.

**Docstring.** Elle rappelle l'idée clé : sous Black-Scholes, passer d'une date à la suivante est exact, donc on ne simule que les dates utiles (un produit semestriel sur 3 ans n'a besoin que de 6 points, pas de 756 jours). Elle décrit aussi la forme du résultat.

**Corps, ligne par ligne :**
- `if rng is None: rng = np.random.default_rng()` : si l'appelant n'a pas fourni de générateur, on en crée un sans graine (tirages différents à chaque appel). `default_rng` est le générateur moderne de NumPy, plus rapide et de meilleure qualité statistique que l'ancien `np.random.normal`.
- `prix = np.zeros((n_simulations, len(obs_dates) + 1))` : une matrice avec **une ligne par trajectoire** et **une colonne par date**, plus la colonne 0 pour aujourd'hui. On réserve toute la mémoire d'un coup (plus rapide que d'ajouter des colonnes au fur et à mesure).
- `prix[:, 0] = S0` : `[:, 0]` veut dire « toutes les lignes, colonne 0 ». Toutes les trajectoires partent du même spot.
- `t_precedent = 0.0` : la date de la colonne précédente ; on part d'aujourd'hui.
- `for i, t in enumerate(obs_dates):` : on parcourt les dates ; `enumerate` donne à la fois l'indice `i` (0, 1, 2…) et la date `t`. **La boucle tourne sur les dates, pas sur les trajectoires** : chaque tour met à jour toutes les trajectoires d'un coup.
- `dt = t - t_precedent` : l'écart entre deux dates. Il peut varier d'une période à l'autre : un calendrier irrégulier est accepté.
- `Z = rng.standard_normal(n_simulations)` : un tirage normal centré réduit par trajectoire, tous d'un coup (vecteur NumPy).
- `croissance = (r - q - sigma**2 / 2) * dt` : la partie déterministe de l'exposant, avec la correction d'Itô `− σ²/2`. `**` est la puissance en Python.
- `choc = sigma * np.sqrt(dt) * Z` : la partie aléatoire ; l'écart-type du choc grandit comme la racine du temps écoulé.
- `prix[:, i + 1] = prix[:, i] * np.exp(croissance + choc)` : le prix de la colonne suivante pour **toutes** les trajectoires en une seule ligne. C'est la **vectorisation** : NumPy fait la boucle sur les 50 000 trajectoires en C, beaucoup plus vite qu'une boucle Python.
- `t_precedent = t` : on avance la date de référence pour le tour suivant.
- `return prix` : la matrice complète. Aucun contrôle de finitude ici : le contrôle de sortie de `main.py` (`after_request`) refuse tout résultat non fini pour toutes les routes.

Pour une option européenne, la boucle fait 1 tour ; pour Longstaff-Schwartz, 100 ; pour un Phoenix semestriel sur 3 ans, 6.

---

## Exercices

1. Simulez 100 000 trajectoires à une date T = 1 et vérifiez que la moyenne de S_T·e^(−rT) vaut S0·e^(−qT) (le prix actualisé est une martingale).
2. Retirez le terme `− sigma**2 / 2` : de combien la moyenne dérive-t-elle pour σ = 40 % ?
