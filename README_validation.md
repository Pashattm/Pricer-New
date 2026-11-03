# `validation.py` — lecture, conversion et vérification des paramètres

C'est le **seul** endroit du projet où les paramètres envoyés par le site sont contrôlés.

```
navigateur ──JSON──► main.py ──data──► validation.parametres_xxx(data) ──dict propre──► moteur
                                              │
                                              └── ValueError("message en français") ──► réponse 400
```

- `main.py` appelle **une fonction par produit** : `parametres_option`, `parametres_forward`, etc.
- Chaque fonction **lit** le JSON, **convertit** les % en décimal, **vérifie** tout, et renvoie un dictionnaire prêt à être passé au moteur.
- Les moteurs ne revérifient rien : leur code ne contient que des maths.
- Toute erreur lève une `ValueError` avec un message lisible ; `main.py` la transforme en réponse 400, affichée en rouge sous le bouton.

**Pourquoi un module à part ?** Avant ce module, les mêmes contrôles existaient à plusieurs niveaux : un contrôle générique dans `main.py`, un contrôle dans chaque route, et un autre dans certains moteurs. Les bornes n'étaient d'ailleurs pas toujours identiques d'un endroit à l'autre. Un seul module = une seule liste de bornes, des messages homogènes, et un fichier à lire pour connaître toutes les limites du pricer.

**Pourquoi tant de contrôles ?** En C#, un champ `double` ne peut pas recevoir `"abc"` ni `true` : le typage statique protège. En Python, n'importe quoi peut arriver dans le JSON (chaînes, booléens, `NaN`). Ce fichier fait le travail que ferait le compilateur.

---

# Le code, ligne par ligne
### 1. En-tête du fichier

```python
"""Lecture, conversion et vérification des paramètres envoyés par le site.

C'est le SEUL endroit du projet où les paramètres sont contrôlés :
- main.py appelle une fonction parametres_xxx(data) par produit ;
- chaque fonction lit le JSON, convertit les % en décimal, vérifie tout,
  et renvoie un dictionnaire propre ;
- les moteurs reçoivent ce dictionnaire et ne revérifient rien.

Toute erreur lève une ValueError avec un message en français ;
main.py la transforme en réponse 400 affichée en rouge sous le bouton.
Les bornes sont toutes regroupées ci-dessous : une seule valeur à changer.
"""
```

- La docstring décrit le **contrat** du module : `main.py` appelle une fonction `parametres_xxx(data)` par produit ; chaque fonction lit, convertit, vérifie et renvoie un dictionnaire propre ; les moteurs ne revérifient rien.
- Elle rappelle le mécanisme d'erreur : une `ValueError` avec un message en français, transformée en réponse 400 par `main.py`.
- Dernière ligne : toutes les bornes sont regroupées en tête de fichier ; pour changer une limite, il n'y a qu'une valeur à modifier.

### 2. Imports

```python
import numpy as np

from strutu_engine import barrieres_de_rappel
```

- `import numpy as np` : utilisé pour `np.isfinite` (tester qu'un nombre n'est ni `NaN` ni infini), `np.any` et `np.atleast_1d`.
- `from strutu_engine import barrieres_de_rappel` : la formule des barrières de rappel avec step-down. On la **réutilise** pour la validation au lieu de la réécrire : le contrôle et le calcul ne peuvent pas diverger.

### 3. Les bornes communes

```python
SPOT_MAX = 1e9            # spot, strike, niveaux absolus
NOMINAL_MAX = 1e12
TAUX_MAX = 0.5            # |r| ≤ 50 %
DIVIDENDE_MAX = 0.5       # 0 ≤ q ≤ 50 %
SIGMA_MAX = 2.0           # 200 % de vol
MATURITE_MAX = 30.0       # en années
COUPON_MAX = 1.0          # 100 % du nominal sur une période
BARRIERE_MAX = 3.0        # 300 % du niveau de référence
MONEYNESS_MIN = 0.5       # strike entre 50 % ...
MONEYNESS_MAX = 1.5       # ... et 150 % du spot
N_SIM_MIN = 1_000         # en dessous le prix Monte Carlo bouge trop
N_SIM_MAX = 500_000       # au-dessus ça rame
CONSTATS_MAX = 6_000_000  # simulations × dates d'observation
FREQUENCES = (1, 2, 4, 12)            # observations par an
FREQUENCE_DEFAUT = 2
GRAINE_MAX = 2**32 - 1
PERIODES_VOLATILITE = ("6mo", "1y", "2y", "5y")
```

Toutes les limites du pricer, au même endroit. Les noms en MAJUSCULES sont la convention Python pour des **constantes** (valeurs qu'on ne modifie pas pendant l'exécution).

- `SPOT_MAX = 1e9` : spot et prix absolus jusqu'à 10⁹. `1e9` est l'écriture scientifique de 1 000 000 000.
- `NOMINAL_MAX = 1e12` : montant investi maximal pour les produits structurés.
- `TAUX_MAX = 0.5` : |r| ≤ 50 % ; `DIVIDENDE_MAX = 0.5` : 0 ≤ q ≤ 50 %.
- `SIGMA_MAX = 2.0` : volatilité jusqu'à 200 %.
- `MATURITE_MAX = 30.0` : 30 ans au plus.
- `COUPON_MAX = 1.0` : un coupon ne dépasse pas 100 % du nominal sur une période ; `BARRIERE_MAX = 3.0` : barrières jusqu'à 300 % du niveau de référence.
- `MONEYNESS_MIN = 0.5` / `MONEYNESS_MAX = 1.5` : strike entre 50 % et 150 % du spot. Le site lit ces deux valeurs via `/api/config`.
- `N_SIM_MIN = 1_000` / `N_SIM_MAX = 500_000` : en dessous de 1 000 simulations le prix Monte Carlo bouge trop, au-dessus de 500 000 le calcul devient long. Les `_` dans `1_000` sont ignorés par Python et rendent les grands nombres lisibles.
- `CONSTATS_MAX = 6_000_000` : plafond de simulations × dates d'observation, soit environ 48 Mo par matrice de `float64` (8 octets par nombre).
- `FREQUENCES = (1, 2, 4, 12)` : observations annuelles, semestrielles, trimestrielles ou mensuelles ; `FREQUENCE_DEFAUT = 2` : semestriel par défaut.
- `GRAINE_MAX = 2**32 - 1` : la plus grande graine acceptée (entier non signé sur 32 bits).
- `PERIODES_VOLATILITE = ("6mo", "1y", "2y", "5y")` : la **liste blanche** des périodes historiques. On ne transmet jamais une chaîne libre à Yahoo Finance.

Ce sont des bornes « de bon sens » : on n'interdit pas les marchés extrêmes, on attrape les fautes de frappe (vol de 2 500 % au lieu de 25 %).

### 4. `STRIKES_STRATEGIE` — les strikes de chaque stratégie

```python
# Strikes nécessaires à chaque stratégie (sert aussi à centrer le graphe dans main.py)
STRIKES_STRATEGIE = {
    "covered_call":   ["K"],
    "protective_put": ["K"],
    "straddle":       ["K"],
    "strangle":       ["K_put", "K_call"],
    "call_spread":    ["K1", "K2"],
    "put_spread":     ["K1", "K2"],
    "collar":         ["K_put", "K_call"],
}
```

- Un dictionnaire « nom de stratégie → liste des champs de strike à lire ». Un straddle n'a qu'un strike `K` ; un strangle et un collar ont un strike de put et un strike de call ; les spreads ont `K1` et `K2`.
- Il sert deux fois : ici, pour ne lire **que** les strikes utiles (un champ en trop envoyé par le navigateur est ignoré), et dans `main.py`, pour centrer la grille du graphe sur les strikes.
- Ajouter une stratégie = une ligne ici et une ligne dans `STRATEGY_BUILDERS` (`main.py`).

### 5. `_vers_nombre()` — convertir une valeur en nombre fini

```python
def _vers_nombre(valeur, nom):
    """Convertit une valeur JSON en float fini.

    Pièges Python évités : True est un int (on le refuse), float("nan") passe
    le test "x <= 0" (NaN <= 0 vaut False), donc on teste np.isfinite.
    """
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float, str)):
        raise ValueError(f"{nom} doit être un nombre.")
    try:
        x = float(valeur)
    except ValueError:
        raise ValueError(f"{nom} doit être un nombre.") from None
    if not np.isfinite(x):
        raise ValueError(f"{nom} doit être un nombre fini.")
    return x
```

Toutes les lectures de nombres passent par cette fonction.

- **Docstring — deux pièges Python** : `True` est un `int` (`isinstance(True, int)` vaut `True`), et `float("nan")` passe le test `x <= 0` car `NaN <= 0` vaut `False`. Un `sigma = NaN` passerait donc un contrôle naïf `if sigma <= 0`.
- `if isinstance(valeur, bool) or not isinstance(valeur, (int, float, str)):` : on refuse les booléens, et tout ce qui n'est ni un nombre ni une chaîne (une liste, un dictionnaire…). Le test `bool` vient **avant** le test `int` justement parce qu'un booléen est aussi un `int`.
- `try: x = float(valeur)` / `except ValueError:` : `float("abc")` lève une `ValueError` Python peu lisible (« could not convert string to float »). On la remplace par un message en français. `from None` masque l'erreur d'origine dans la trace.
- `if not np.isfinite(x):` : refuse `NaN`, `inf` et `-inf` (qui peuvent arriver sous forme de chaîne, `"nan"`).
- `return x` : un `float` sûr.

### 6. `nombre()` — champ numérique

```python
def nombre(data, cle, defaut=None):
    """Champ numérique obligatoire (ou valeur par défaut si absent ou vide).

    Un <input> vide envoie "", pas null : les deux comptent comme absents.
    """
    valeur = data.get(cle, defaut)
    if valeur is None or valeur == "":
        valeur = defaut
    if valeur is None:
        raise ValueError(f"Paramètre manquant : {cle}.")
    return _vers_nombre(valeur, cle)
```

- `valeur = data.get(cle, defaut)` : `.get` renvoie la valeur par défaut si la clé est absente (au lieu de lever une `KeyError`).
- `if valeur is None or valeur == "": valeur = defaut` : un `<input>` vide envoie `""`, pas `null` ; les deux comptent comme absents. Sans cette ligne, `float("")` planterait.
- `if valeur is None: raise ValueError(f"Paramètre manquant : {cle}.")` : champ obligatoire (pas de valeur par défaut) et absent.
- `return _vers_nombre(valeur, cle)` : conversion et contrôles.

### 7. `pourcentage()` — champ saisi en %

```python
def pourcentage(data, cle, defaut=None):
    """Champ saisi en % dans le formulaire, renvoyé en décimal (5 -> 0.05)."""
    return nombre(data, cle, defaut) / 100
```

- `return nombre(data, cle, defaut) / 100` : **la seule conversion % → décimal du projet**. Le formulaire envoie `5` pour 5 % ; les moteurs reçoivent `0.05`. Si une vol paraît 100 fois trop grande ou trop petite, c'est ici qu'il faut regarder.

### 8. `optionnel()` — champ facultatif

```python
def optionnel(data, cle):
    """Champ numérique facultatif : None s'il est absent ou vide."""
    valeur = data.get(cle)
    return None if valeur is None or valeur == "" else _vers_nombre(valeur, cle)
```

- `valeur = data.get(cle)` puis `return None if valeur is None or valeur == "" else _vers_nombre(valeur, cle)` : `None` si le champ est vide, sinon un nombre vérifié. Sert au seuil de bonus du Phoenix, qui peut ne pas exister.

### 9. `entier()` — champ entier

```python
def entier(data, cle, defaut=None):
    """Refuse 50000.5 au lieu de le tronquer silencieusement en 50000."""
    x = nombre(data, cle, defaut)
    if not x.is_integer():
        raise ValueError(f"{cle} doit être entier.")
    return int(x)
```

- `x = nombre(data, cle, defaut)` : lecture comme un nombre.
- `if not x.is_integer():` : `is_integer()` vaut `True` pour `50000.0`, `False` pour `50000.5`. On **refuse** au lieu de tronquer silencieusement : une troncature cachée est un bug en attente.
- `return int(x)` : un vrai entier Python.

### 10. `booleen()` — case à cocher

```python
def booleen(data, cle, defaut):
    """Convertit un true/false venu du JSON en vrai booléen.

    Attention : bool("false") donne True en Python, d'où cette fonction.
    """
    valeur = data.get(cle, defaut)
    if isinstance(valeur, bool):
        return valeur
    if isinstance(valeur, str) and valeur.strip().lower() in ("true", "1", "oui", "yes"):
        return True
    if isinstance(valeur, str) and valeur.strip().lower() in ("false", "0", "non", "no"):
        return False
    if valeur in (0, 1):
        return bool(valeur)
    raise ValueError(f"{cle} doit valoir true ou false (reçu : {valeur!r}).")
```

- **Docstring** : `bool("false")` vaut `True` en Python (toute chaîne non vide est vraie). Si le navigateur envoyait la chaîne `"false"`, l'effet mémoire s'activait : c'est un bug réellement rencontré.
- `if isinstance(valeur, bool): return valeur` : cas normal, un vrai booléen JSON.
- Les deux lignes suivantes lisent explicitement les chaînes `"true"`, `"1"`, `"oui"`, `"yes"` et `"false"`, `"0"`, `"non"`, `"no"`. `.strip().lower()` retire les espaces et met en minuscules.
- `if valeur in (0, 1): return bool(valeur)` : accepte aussi les nombres 0 et 1.
- Tout le reste est **refusé** avec un message qui montre la valeur reçue (`{valeur!r}` affiche la représentation Python, guillemets compris).

### 11. `choix()` — valeur dans une liste fermée

```python
def choix(data, cle, options, defaut=None, libelle=None):
    """Champ texte qui doit appartenir à une liste fermée."""
    valeur = data.get(cle, defaut)
    if valeur not in options:
        raise ValueError(f"{libelle or cle} invalide : valeurs possibles {', '.join(options)}.")
    return valeur
```

- `valeur = data.get(cle, defaut)` : lecture du champ texte.
- `if valeur not in options:` : la valeur doit faire partie de la liste (par exemple `("call", "put")`).
- Le message liste les valeurs possibles ; `libelle or cle` affiche un nom lisible (« Type d'option ») s'il est fourni, sinon le nom technique du champ.
- C'est grâce à cette fonction que les moteurs peuvent écrire `if option_type == "call": ... else: ...` sans se méfier : le `else` est forcément un put.

### 12. `verifier_marche()` — limites de marché communes

```python
def verifier_marche(S0, T, r, q, sigma=None, sigma_nulle=False):
    """Limites de marché communes à tous les produits (valeurs déjà en décimal)."""
    if not 0 < S0 <= SPOT_MAX:
        raise ValueError("Le spot doit être strictement positif et ≤ 10⁹.")
    if not 0 < T <= MATURITE_MAX:
        raise ValueError("La maturité doit être comprise entre 0 et 30 ans.")
    if abs(r) > TAUX_MAX:
        raise ValueError("Le taux doit être compris entre −50 % et 50 %.")
    if not 0 <= q <= DIVIDENDE_MAX:
        raise ValueError("Le dividende doit être compris entre 0 et 50 %.")
    if sigma is not None and not (0 <= sigma <= SIGMA_MAX and (sigma > 0 or sigma_nulle)):
        raise ValueError("La volatilité doit être strictement positive et ≤ 200 %."
                         if not sigma_nulle else "La volatilité doit être comprise entre 0 et 200 %.")
```

- La bannière `# === Contrôles communs ===` ouvre la section des contrôles partagés par plusieurs produits.
- Elle reçoit des valeurs **déjà en décimal**.
- `if not 0 < S0 <= SPOT_MAX:` : Python autorise les comparaisons enchaînées, qui se lisent comme en mathématiques.
- Maturité dans ]0 ; 30 ans], |r| ≤ 50 % (`abs` = valeur absolue), dividende dans [0 ; 50 %].
- `sigma_nulle=False` : quand ce paramètre vaut `True`, une vol nulle est acceptée. C'est le cas de l'Athéna, simulé, où le calcul reste défini avec σ = 0 ; Black-Scholes, lui, divise par σ et exige σ > 0.
- La dernière condition combine les deux cas : `0 <= sigma <= SIGMA_MAX` et, si `sigma_nulle` est faux, `sigma > 0`. Le message d'erreur s'adapte avec une expression conditionnelle (`"..." if not sigma_nulle else "..."`).

### 13. `verifier_strikes()` — strike proche du spot

```python
def verifier_strikes(S0, strikes):
    """Chaque strike entre 50 % et 150 % du spot.

    Un strike à 100 pour un spot à 300 se price, mais n'a pas de sens pédagogique.
    Le site lit ces bornes via /api/config : une seule source de vérité.
    """
    lo, hi = MONEYNESS_MIN * S0, MONEYNESS_MAX * S0
    for K in strikes:
        if not lo <= K <= hi:
            raise ValueError(f"Strike {K:.2f} trop éloigné du spot {S0:.2f} : "
                             f"il doit être entre {lo:.2f} et {hi:.2f} "
                             f"({MONEYNESS_MIN:.0%} à {MONEYNESS_MAX:.0%} du spot).")
```

- **Docstring** : un strike à 100 pour un spot à 300 se price, mais n'a aucun intérêt pédagogique et rend les grecques illisibles.
- `lo, hi = MONEYNESS_MIN * S0, MONEYNESS_MAX * S0` : les bornes en prix (affectation multiple).
- `for K in strikes:` : une stratégie peut avoir plusieurs strikes ; la fonction reçoit donc une liste.
- Le message d'erreur donne le strike, le spot et l'intervalle autorisé : `{K:.2f}` affiche 2 décimales, `{MONEYNESS_MIN:.0%}` affiche `50%`. Les trois morceaux de f-string sont collés automatiquement par Python (chaînes adjacentes).
- **Une seule source de vérité** : la même règle était autrefois écrite dans `main.py` **et** dans `index.html`. Le site lit maintenant les bornes via `/api/config`.

### 14. `simulations()` — nombre de simulations

```python
def simulations(data, defaut):
    """Nombre de simulations : entier entre 1 000 et 500 000."""
    maximum = N_SIM_MAX
    n = entier(data, "n_simulations", defaut)
    if not N_SIM_MIN <= n <= maximum:
        raise ValueError(f"Le nombre de simulations doit être un entier entre "
                         f"{N_SIM_MIN:,} et {maximum:,}.".replace(",", " "))
    return n
```

- `n = entier(data, "n_simulations", defaut)` : un entier, avec une valeur par défaut propre à chaque produit (30 000 pour les options).
- `maximum = N_SIM_MAX` : le plafond commun.
- `if not N_SIM_MIN <= n <= maximum:` : contrôle de l'intervalle.
- `f"{N_SIM_MIN:,}"` affiche `1,000` ; `.replace(",", " ")` le transforme en `1 000`, à la française.
- `return n`.

### 15. `graine()` — graine du générateur aléatoire

```python
def graine(data):
    """Graine du générateur aléatoire : même graine = mêmes tirages = même prix."""
    seed = entier(data, "seed", 42)
    if not 0 <= seed <= GRAINE_MAX:
        raise ValueError("La graine doit être un entier entre 0 et 4 294 967 295.")
    return seed
```

- `seed = entier(data, "seed", 42)` : 42 par défaut. Même graine = mêmes tirages = même prix : un calcul Monte Carlo ne change plus d'un clic à l'autre.
- `if not 0 <= seed <= GRAINE_MAX:` : NumPy accepte des graines positives ; on fixe une limite raisonnable.

### 16. `dates_observation()` — calendrier d'observation

```python
def dates_observation(T, frequence):
    """Construit [1/f, 2/f, ..., T] : dates forcément positives et croissantes.

    T doit tomber pile sur un nombre entier de périodes. Tolérance 1e-9 car
    2,5 × 2 peut donner 4,999999999 en flottant.
    """
    if frequence not in FREQUENCES:
        raise ValueError("La fréquence doit être 1 (annuelle), 2, 4 ou 12 (mensuelle).")
    n_obs = T * frequence
    if abs(n_obs - round(n_obs)) > 1e-9:
        raise ValueError(f"Avec une fréquence de {frequence}/an, la maturité doit être un "
                         f"multiple de {1 / frequence:g} an (reçu : T = {T}).")
    return [k / frequence for k in range(1, int(round(n_obs)) + 1)]
```

- **Docstring** : construit `[1/f, 2/f, ..., T]`. Les dates ne sont jamais saisies à la main : elles sont **forcément positives et croissantes**.
- `if frequence not in FREQUENCES:` : 1, 2, 4 ou 12 observations par an.
- `n_obs = T * frequence` : le nombre de dates (3 ans × 2 = 6).
- `if abs(n_obs - round(n_obs)) > 1e-9:` : T doit tomber pile sur un nombre entier de périodes (une maturité de 13 mois en semestriel est refusée : la dernière période serait incomplète). **Tolérance 1e-9** : en flottant, 2,5 × 2 peut donner 4,999999999 ; comparer `n_obs == round(n_obs)` échouerait au hasard.
- `{1 / frequence:g}` : le format `g` affiche `0.5` et non `0.500000`.
- `return [k / frequence for k in range(1, int(round(n_obs)) + 1)]` : une **liste en compréhension** : pour k de 1 à n_obs, la date k/f.

### 17. `verifier_constats()` — plafond de calcul

```python
def verifier_constats(n_simulations, n_dates):
    """Plafond mémoire / temps : simulations × dates d'observation."""
    maximum = CONSTATS_MAX
    if n_simulations * n_dates > maximum:
        raise ValueError(f"Calcul trop volumineux : réduisez les simulations ou la fréquence "
                         f"(maximum {maximum:,} constats simulés).".replace(",", " "))
```

- `maximum = CONSTATS_MAX` : 6 millions de constats simulés.
- `if n_simulations * n_dates > maximum:` : simulations × dates = nombre de prix à calculer et à garder en mémoire.
- Le message dit quoi faire (réduire les simulations ou la fréquence).

### 18. `step_down()` — baisse de la barrière de rappel

```python
def step_down(data, K_auto, n_dates, actif, minimum=0.0):
    """Baisse de la barrière de rappel à chaque constat (en décimal), 0 sans rappel.

    Les barrières de rappel possibles (toutes sauf la maturité) doivent rester
    positives et, pour le Phoenix, au-dessus de la barrière coupon.
    """
    baisse = pourcentage(data, "step_down", 0)
    if baisse < 0:
        raise ValueError("Le step-down doit être positif ou nul.")
    if not actif:
        return 0.0
    niveaux = barrieres_de_rappel(K_auto, baisse, max(2, n_dates))[:max(1, n_dates - 1)]
    if np.any(niveaux <= 0) or np.any(niveaux < minimum):
        raise ValueError("Les seuils de rappel doivent rester positifs et au-dessus du seuil coupon Phoenix.")
    return baisse
```

- **Docstring** : le step-down abaisse la barrière de rappel à chaque constat (100 %, 95 %, 90 %…) ; il est ignoré sans rappel.
- `baisse = pourcentage(data, "step_down", 0)` : saisie en points de %, renvoyée en décimal ; 0 par défaut (désactivé).
- `if baisse < 0:` : une baisse négative serait une hausse.
- `if not actif: return 0.0` : sans rappel anticipé, le step-down n'a pas de sens.
- `niveaux = barrieres_de_rappel(K_auto, baisse, max(2, n_dates))[:max(1, n_dates - 1)]` : on calcule les barrières avec **la même fonction que le moteur**, puis on ne garde que les dates où le rappel est possible (toutes sauf la maturité). `[:n]` garde les n premiers éléments ; les `max(...)` gèrent le cas d'une seule date.
- `if np.any(niveaux <= 0) or np.any(niveaux < minimum):` : toutes les barrières doivent rester positives et, pour le Phoenix (`minimum = B_phoenix`), au-dessus de la barrière coupon.
- `return baisse` : en décimal.

### 19. `_marche()` — lire les paramètres de marché

```python
def _marche(data, sigma_nulle=False):
    """Lit et vérifie S0, T, r, q, sigma (formulaire en %, renvoyé en décimal)."""
    S0, T = nombre(data, "S0"), nombre(data, "T")
    r, q, sigma = pourcentage(data, "r"), pourcentage(data, "q", 0), pourcentage(data, "sigma")
    verifier_marche(S0, T, r, q, sigma, sigma_nulle)
    return S0, T, r, q, sigma
```

- `S0, T = nombre(data, "S0"), nombre(data, "T")` : spot et maturité, tels quels.
- `r, q, sigma = pourcentage(...)` : taux, dividende et vol saisis en %, convertis. `pourcentage(data, "q", 0)` : le dividende est facultatif (0 par défaut).
- `verifier_marche(S0, T, r, q, sigma, sigma_nulle)` : les limites communes, en transmettant l'autorisation éventuelle d'une vol nulle.
- `return S0, T, r, q, sigma` : cinq valeurs, que l'appelant « déballe » en une ligne.
- Le `_` en tête du nom : fonction interne au fichier.

### 20. `_nominal()` — montant investi

```python
def _nominal(data):
    nominal = nombre(data, "nominal", 1000)
    if not 0 < nominal <= NOMINAL_MAX:
        raise ValueError("Le montant investi doit être strictement positif et ≤ 10¹².")
    return nominal
```

- `nombre(data, "nominal", 1000)` : 1 000 par défaut.
- Contrôle : strictement positif et au plus 10¹².

### 21. `_sens()` — sens de la position

```python
def _sens(data):
    return choix(data, "side", ("buy", "sell"), "buy", "Sens")
```

- `return choix(data, "side", ("buy", "sell"), "buy", "Sens")` : achat ou vente, achat par défaut. Une fonction de deux lignes, mais utilisée par plusieurs produits.

### 22. `parametres_option()` — option classique

```python
def parametres_option(data):
    """Option européenne (Black-Scholes ou Monte Carlo) ou américaine (Longstaff-Schwartz)."""
    S0, T, r, q, sigma = _marche(data)
    K = nombre(data, "K")
    verifier_strikes(S0, [K])
    return dict(S0=S0, K=K, T=T, r=r, q=q, sigma=sigma,
                option_type=choix(data, "option_type", ("call", "put"), libelle="Type d'option"),
                style=choix(data, "style", ("european", "american"), libelle="Style d'exercice"),
                method=choix(data, "method", ("black_scholes", "monte_carlo", "longstaff_schwartz"),
                              "black_scholes", "Méthode"),
                side=_sens(data), n_simulations=simulations(data, 30000), seed=graine(data))
```

- La bannière `# === Un contrôle par produit ===` ouvre la section des fonctions appelées par `main.py`.
- `S0, T, r, q, sigma = _marche(data)` : marché lu et vérifié.
- `K = nombre(data, "K")` puis `verifier_strikes(S0, [K])` : strike obligatoire, dans l'intervalle de moneyness.
- `return dict(...)` : `dict(a=1, b=2)` est une autre façon d'écrire `{"a": 1, "b": 2}`. On y trouve :
  - `option_type`, `style` et `method` lus par `choix` dans des listes fermées (la méthode vaut Black-Scholes par défaut) ;
  - `side` (achat ou vente) ;
  - `n_simulations` (30 000 par défaut) et `seed`, utilisés seulement par Monte Carlo et Longstaff-Schwartz.

### 23. `parametres_forward()` — forward / future

```python
def parametres_forward(data):
    """Forward : pas de volatilité, le prix contractuel K doit être positif."""
    S0, T = nombre(data, "S0"), nombre(data, "T")
    r, q = pourcentage(data, "r"), pourcentage(data, "q", 0)
    verifier_marche(S0, T, r, q)
    K = nombre(data, "K")
    if not 0 < K <= SPOT_MAX:
        raise ValueError("Le prix contractuel doit être strictement positif et ≤ 10⁹.")
    return dict(S0=S0, K=K, T=T, r=r, q=q, side=_sens(data))
```

- **Pas de volatilité** : un forward n'en dépend pas. On lit donc S0 et T par `nombre`, r et q par `pourcentage`, et on appelle `verifier_marche` sans sigma.
- `K = nombre(data, "K")` : le prix contractuel. Il n'est pas soumis à la règle de moneyness : un forward signé il y a longtemps peut avoir un K très éloigné du spot actuel. Seule contrainte : strictement positif et au plus 10⁹.
- `return dict(S0=..., K=..., T=..., r=..., q=..., side=...)`.

### 24. `parametres_strategie()` — stratégie optionnelle

```python
def parametres_strategie(data):
    """Stratégie : on ne lit que les strikes utiles à la stratégie choisie."""
    strategie = choix(data, "strategy", tuple(STRIKES_STRATEGIE), libelle="Stratégie")
    S0, T, r, q, sigma = _marche(data)
    qty = nombre(data, "qty", 1)
    if qty <= 0:
        raise ValueError("La quantité doit être strictement positive.")
    strikes = {cle: nombre(data, cle) for cle in STRIKES_STRATEGIE[strategie]}
    verifier_strikes(S0, list(strikes.values()))
    return dict(strategie=strategie, S0=S0, T=T, r=r, q=q, sigma=sigma,
                qty=qty, side=_sens(data), strikes=strikes)
```

- `strategie = choix(data, "strategy", tuple(STRIKES_STRATEGIE), libelle="Stratégie")` : le nom doit être une clé de `STRIKES_STRATEGIE`. On vérifie le nom **avant** de s'en servir comme clé : une clé inconnue lèverait une erreur peu lisible.
- `_marche(data)` : marché.
- `qty = nombre(data, "qty", 1)` et le contrôle `qty <= 0` : quantité strictement positive.
- `strikes = {cle: nombre(data, cle) for cle in STRIKES_STRATEGIE[strategie]}` : une **compréhension de dictionnaire** qui ne lit que les strikes utiles (par exemple `{"K_put": 95, "K_call": 105}`).
- `verifier_strikes(S0, list(strikes.values()))` : tous les strikes dans l'intervalle de moneyness.
- Le dictionnaire renvoyé garde les strikes à part (`strikes=strikes`) : `main.py` les passe au constructeur de la stratégie et s'en sert pour centrer le graphe.

### 25. `parametres_digitale()` — digitale

```python
def parametres_digitale(data):
    """Digitale européenne cash-or-nothing ou asset-or-nothing."""
    if data.get("style", "european") != "european":
        raise ValueError("La digitale est européenne uniquement.")
    S0, T, r, q, sigma = _marche(data)
    K = nombre(data, "K")
    verifier_strikes(S0, [K])
    payout = nombre(data, "payout", 1)
    if payout < 0:
        raise ValueError("Le paiement fixe doit être positif ou nul.")
    return dict(S0=S0, K=K, T=T, r=r, q=q, sigma=sigma, payout=payout,
                option_type=choix(data, "option_type", ("call", "put"), "call", "Type d'option"),
                digital_type=choix(data, "digital_type", ("cash", "asset"), "cash", "Type de digitale"),
                side=_sens(data), n_simulations=simulations(data, 30000), seed=graine(data))
```

- `if data.get("style", "european") != "european":` : une digitale est européenne uniquement ; un style américain est refusé explicitement.
- `_marche`, `K`, `verifier_strikes` : comme pour une option.
- `payout = nombre(data, "payout", 1)` et `if payout < 0:` : le paiement fixe de la cash-or-nothing, positif ou nul.
- `option_type` et `digital_type` (`"cash"` ou `"asset"`) lus par `choix`, avec des valeurs par défaut.
- `n_simulations` et `seed` : la digitale est aussi pricée par Monte Carlo, pour comparaison.

### 26. `parametres_phoenix()` — Phoenix

```python
def parametres_phoenix(data):
    """Phoenix : barrières, coupons et bonus saisis en % (70 = 70 %).

    Ordre imposé : protection ≤ coupon ≤ rappel (le rappel seulement s'il est actif).
    """
    S0, T, r, q, sigma = _marche(data)
    nominal = _nominal(data)
    obs_dates = dates_observation(T, entier(data, "frequence", FREQUENCE_DEFAUT))
    n = simulations(data, 50000)
    verifier_constats(n, len(obs_dates))

    K_auto = pourcentage(data, "K_auto", 100)
    B_phoenix = pourcentage(data, "B_phoenix")
    B_pdi = pourcentage(data, "B_pdi")
    strike_pct = pourcentage(data, "strike_pct", 100)
    has_autocall = booleen(data, "has_autocall", True)
    if not all(0 < b <= BARRIERE_MAX for b in (K_auto, B_phoenix, B_pdi, strike_pct)):
        raise ValueError("Les barrières et le strike doivent être strictement positifs et ≤ 300 %.")
    if B_pdi > B_phoenix:
        raise ValueError("La barrière de protection doit être inférieure ou égale à la barrière coupon.")
    if has_autocall and B_phoenix > K_auto:
        raise ValueError("La barrière coupon doit être inférieure ou égale à la barrière de rappel.")

    # coupons : un seul montant ou une liste (step-up) avec un coupon par date
    brut = data.get("coupon")
    if isinstance(brut, list):
        if len(brut) != len(obs_dates):
            raise ValueError(f"Il faut un coupon par date d'observation "
                             f"({len(obs_dates)} dates, {len(brut)} coupons).")
        coupon = [_vers_nombre(c, "coupon") / 100 for c in brut]
    else:
        coupon = pourcentage(data, "coupon")
    if not all(0 <= c <= COUPON_MAX for c in np.atleast_1d(coupon)):
        raise ValueError("Chaque coupon doit être compris entre 0 et 100 % du nominal.")

    bonus_threshold = optionnel(data, "bonus_threshold")
    if bonus_threshold is not None:
        bonus_threshold /= 100
        if bonus_threshold <= 0:
            raise ValueError("Le seuil du bonus doit être strictement positif.")
    bonus_amount = pourcentage(data, "bonus_amount", 0)
    if bonus_amount < 0:
        raise ValueError("Le bonus ne peut pas être négatif.")

    return dict(S0=S0, r=r, q=q, sigma=sigma, nominal=nominal, obs_dates=obs_dates,
                K_auto=K_auto, B_phoenix=B_phoenix, B_pdi=B_pdi, strike_pct=strike_pct,
                coupon=coupon, memory=booleen(data, "memory", False), has_autocall=has_autocall,
                bonus_threshold=bonus_threshold, bonus_amount=bonus_amount,
                n_simulations=n, seed=graine(data),
                step_down=step_down(data, K_auto, len(obs_dates), has_autocall, B_phoenix))
```

**Marché et calendrier**
- `_marche(data)` : marché (vol strictement positive).
- `nominal = _nominal(data)` : montant investi.
- `obs_dates = dates_observation(T, entier(data, "frequence", FREQUENCE_DEFAUT))` : les dates d'observation, à partir de la maturité et de la fréquence.
- `n = simulations(data, 50000)` puis `verifier_constats(n, len(obs_dates))` : nombre de trajectoires et plafond de calcul.

**Barrières**
- `K_auto`, `B_phoenix`, `B_pdi`, `strike_pct` : rappel (100 % par défaut), coupon, protection et strike de référence, saisis en % et convertis.
- `has_autocall = booleen(data, "has_autocall", True)` : rappel anticipé actif ou non.
- `if not all(0 < b <= BARRIERE_MAX for b in (...)):` : `all(...)` vaut vrai si **toutes** les barrières sont dans ]0 ; 300 %].
- `if B_pdi > B_phoenix:` puis `if has_autocall and B_phoenix > K_auto:` : l'ordre **protection ≤ coupon ≤ rappel**. Sinon le produit est incohérent (on toucherait le coupon sous la protection…). La seconde règle ne s'applique que si le rappel est actif.

**Coupons**
- `brut = data.get("coupon")` : soit un nombre (coupon fixe), soit une liste (coupon **step-up**, qui augmente à chaque période).
- `if isinstance(brut, list):` : une liste doit avoir exactement un coupon par date ; chaque élément est converti par `_vers_nombre` puis divisé par 100.
- `else: coupon = pourcentage(data, "coupon")` : coupon fixe.
- `np.atleast_1d(coupon)` : transforme un nombre seul en tableau d'un élément, pour vérifier les deux cas avec la même ligne : chaque coupon entre 0 et 100 %.

**Bonus**
- `bonus_threshold = optionnel(data, "bonus_threshold")` : seuil facultatif ; s'il existe, converti en décimal (`/= 100`) et strictement positif.
- `bonus_amount = pourcentage(data, "bonus_amount", 0)` : montant du bonus, positif ou nul.

**Résultat**
- Le dictionnaire contient **exactement** les arguments de `analyse_phoenix`, plus le nominal (que `main.py` retire avant l'appel). `memory` (effet mémoire) est lu au passage par `booleen`.
- `step_down=step_down(..., has_autocall, B_phoenix)` : le step-down est validé avec la barrière coupon comme minimum.

### 27. `parametres_autocall()` — Athéna (Autocall Plain)

```python
def parametres_autocall(data):
    """Autocall Plain : coupon par observation, rappel optionnel, protection optionnelle."""
    if data.get("produit") != "autocall_plain":
        raise ValueError("Produit autocall inconnu.")

    S0, T, r, q, sigma = _marche(data, sigma_nulle=True)
    nominal = _nominal(data)
    obs_dates = dates_observation(T, entier(data, "frequence", FREQUENCE_DEFAUT))
    n = simulations(data, 50000)
    verifier_constats(n, len(obs_dates))

    K_auto = pourcentage(data, "K_auto", 100)
    coupon = pourcentage(data, "coupon")
    if not 0 < K_auto <= BARRIERE_MAX or not 0 <= coupon <= COUPON_MAX:
        raise ValueError("Barrière : 0 à 300 % ; coupon par observation : 0 à 100 %.")
    B_pdi = pourcentage(data, "B_pdi", 60) if booleen(data, "protection", True) else None
    if B_pdi is not None and not 0 < B_pdi <= min(1.0, K_auto):
        raise ValueError("La protection doit être dans ]0 ; min(100 %, barrière de rappel)].")

    has_autocall = booleen(data, "has_autocall", True)
    first_call_date = None
    if has_autocall:
        first_call_date = nombre(data, "first_call_months", 0) / 12   # mois -> années
        if not 0 <= first_call_date <= obs_dates[-1]:
            raise ValueError("La première date de rappel doit être entre 0 et la maturité.")

    return dict(S0=S0, r=r, q=q, sigma=sigma, nominal=nominal, obs_dates=obs_dates,
                K_auto=K_auto, B_pdi=B_pdi, coupon=coupon, n_simulations=n, seed=graine(data),
                has_autocall=has_autocall, first_call_date=first_call_date,
                step_down=step_down(data, K_auto, len(obs_dates), has_autocall))
```

- `if data.get("produit") != "autocall_plain":` : la route vérifie qu'elle reçoit bien le produit attendu (`autocall_plain` est le nom technique de l'Athéna).
- `_marche(data, sigma_nulle=True)` : une vol nulle est acceptée (le calcul reste défini).
- `_nominal`, `dates_observation`, `simulations`, `verifier_constats` : comme pour le Phoenix.
- `K_auto` (seuil de rappel et de coupon final) et `coupon` (par observation) : contrôlés ensemble.
- `B_pdi = pourcentage(data, "B_pdi", 60) if booleen(data, "protection", True) else None` : si la case « protection » est décochée, `B_pdi` vaut `None` et le capital est toujours remboursé à 100 % dans le modèle.
- `if B_pdi is not None and not 0 < B_pdi <= min(1.0, K_auto):` : la protection ne peut pas dépasser 100 %, ni la barrière de rappel.
- `has_autocall` et `first_call_date` : la date du premier rappel possible est saisie en **mois** et convertie en années (`/ 12`) ; elle doit être entre 0 et la maturité. Sans rappel, elle reste `None`.
- Le dictionnaire renvoyé correspond aux arguments de `analyse_autocall_plain`, plus le nominal.

### 28. `parametres_volatilite()` — onglet Chantier

```python
def parametres_volatilite(args):
    """Onglet Chantier : ticker, période (liste blanche) et λ de l'EWMA."""
    ticker = args.get("ticker", "").strip().upper()
    if not ticker:
        raise ValueError("Veuillez renseigner un ticker.")
    periode = args.get("periode", "1y")
    if periode not in PERIODES_VOLATILITE:
        raise ValueError("Période historique invalide.")
    lambda_ = nombre(args, "lambda", 0.94)
    if not 0 < lambda_ < 1:
        raise ValueError("Lambda doit être strictement compris entre 0 et 1.")
    return ticker, periode, lambda_
```

- `ticker = args.get("ticker", "").strip().upper()` : `args` contient les paramètres de l'URL (`?ticker=aapl`) ; on retire les espaces et on met en majuscules.
- `if not ticker:` : une chaîne vide est « fausse » en Python.
- `periode` : doit appartenir à la liste blanche `PERIODES_VOLATILITE`.
- `lambda_ = nombre(args, "lambda", 0.94)` : le paramètre de l'EWMA, strictement entre 0 et 1. Le `_` final évite le conflit avec le mot réservé `lambda` de Python.
- `return ticker, periode, lambda_`.

---

## Comment ajouter un produit

1. Écrire `parametres_mon_produit(data)` sur le modèle des autres, en réutilisant `nombre`, `pourcentage`, `_marche`, `simulations`, `graine`…
2. Si une nouvelle borne apparaît, l'ajouter en tête de fichier plutôt que d'écrire le nombre en dur.
3. Dans `main.py`, la route appelle cette fonction puis le moteur. Aucun `try / except` à écrire : la `ValueError` est déjà transformée en réponse 400.
