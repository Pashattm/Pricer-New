# `strutu_engine.py` — Phoenix et Athéna (Autocall Plain)

Ce moteur price les produits autocallables. Il n'existe pas de formule fermée pour ces produits : le flux dépend du **chemin** suivi par le sous-jacent (rappel anticipé, coupons conditionnels, effet mémoire). On simule donc des milliers de trajectoires (avec `simulation_engine.py`), on suit les flux trajectoire par trajectoire, puis on fait la moyenne actualisée.

**Conventions :**
- `r`, `q`, `sigma`, coupons en décimal ; dates en années.
- Phoenix : barrières en **fraction du strike de référence** (`strike_pct × S0`).
- Athéna : barrières en **fraction de S0**.
- Tous les montants sont en **fraction du nominal** (`1` = 100 %). C'est `main.py` qui multiplie par le nominal.
- Aucun contrôle de paramètre ici : `validation.py` s'en charge.

## Les produits en quelques mots

### Phoenix autocallable

Exemple : 3 ans, observations semestrielles, coupon 4 % par semestre, rappel 100 %, coupon 70 %, protection 60 %.

À chaque date d'observation :
- **Si le sous-jacent ≥ 100 %** du niveau initial (hors dernière date) : le produit s'arrête, le client récupère 100 % + le coupon.
- **Si ≥ 70 %** : le client touche le coupon de 4 %.
- **Avec effet mémoire** : un coupon manqué est récupéré dès qu'une date ultérieure repasse au-dessus de 70 %.

À maturité, si le produit n'a pas été rappelé :
- ≥ 60 % : 100 % du capital (+ coupon si ≥ 70 %) ;
- < 60 % : le client perd comme le sous-jacent (ex. finit à 45 % → récupère 45 %).

**Économiquement**, le client a **vendu un put down-and-in** (la protection à 60 %) à la banque et touche en échange des coupons élevés. Plus la vol est forte, plus ce put vaut cher, plus les coupons offerts sont élevés.

### Athéna (coupons accumulés)

« Athéna » est le nom commercial courant en France de ce produit. Le code l'appelle `autocall_plain` (Autocall Plain) : c'est le même produit.

Pas de coupon versé aux dates intermédiaires. Les coupons **s'accumulent** et sont payés d'un coup :
- au rappel (k-ième date : 100 % + k × coupon) ;
- à maturité, **tous** les coupons si le seuil final est atteint, **aucun** sinon.

Option `has_autocall=False` : plus de rappel anticipé, tout se joue à maturité.

Les deux analyses suivent les **mêmes étapes** : calendrier → générateur aléatoire → cours simulés → flux → statistiques. Tout ce qui est commun est écrit une seule fois ; seules les fonctions de flux restent séparées, parce que les règles de coupon sont réellement différentes.

---

# Le code, ligne par ligne
### 1. En-tête du fichier

```python
"""Moteur des produits structurés : Phoenix et Autocall Plain à rappel optionnel.

Je simule le sous-jacent par Monte Carlo aux dates d'observation, je suis
les flux du produit scénario par scénario, puis je fais la moyenne.
Les montants sont en fraction du nominal (1 = 100 %).
Les paramètres sont vérifiés par validation.py avant d'arriver ici.
Les deux analyses suivent les mêmes étapes : calendrier, graine, cours, flux, statistiques.
"""
```

- Elle présente le moteur : Phoenix et Athéna (appelé ici Autocall Plain), à rappel optionnel.
- Elle décrit la méthode : simulation aux dates d'observation, suivi des flux scénario par scénario, moyenne.
- Elle rappelle les unités (fraction du nominal), que les paramètres sont déjà vérifiés, et que les deux analyses suivent les mêmes étapes.

### 2. Imports

```python
import numpy as np

from simulation_engine import simuler_cours_observations
```

- `import numpy as np` : tableaux et calculs vectorisés.
- `from simulation_engine import simuler_cours_observations` : le simulateur commun.

### 3. `barrieres_de_rappel()` — la barrière de rappel à chaque date

```python
def barrieres_de_rappel(K_auto, step_down, n_dates):
    """Barrière de rappel à chaque date, en fraction du niveau de référence.

    Le step-down l'abaisse dès le deuxième constat : K_auto, K_auto - s, K_auto - 2s...
    Une seule formule, utilisée par les flux, l'affichage et la validation.
    """
    return K_auto - step_down*np.arange(n_dates)
```

- La bannière `# === Briques communes ===` ouvre la section des fonctions partagées par les deux produits.
- `return K_auto - step_down*np.arange(n_dates)` : `np.arange(n)` vaut 0, 1, 2, …, n − 1. On obtient K_auto, K_auto − s, K_auto − 2s… Le **step-down** abaisse la barrière dès le deuxième constat : le produit a plus de chances d'être rappelé avec le temps.
- **Une seule formule** : elle était écrite trois fois (flux du Phoenix, flux de l'Athéna, validation). Elle est maintenant utilisée par les flux, par l'affichage (`barrieres_rappel`) et par `validation.step_down`.

### 4. `calculer_remboursement_phoenix_maturite()` — règle de maturité du Phoenix

```python
def calculer_remboursement_phoenix_maturite(ST, S0, B_phoenix, B_pdi, coupon_final, strike_pct=1.0,
                                            bonus_threshold=None, bonus_amount=0.0):
    """Remboursement à maturité d'un Phoenix qui n'a PAS été rappelé.

    Sert au graphe (en fonction du prix final S_T) ET au calcul des flux :
    la règle de maturité n'est écrite qu'ici.
    Limite pour le graphe : je ne compte que le dernier coupon. Avec l'effet
    mémoire, le coupon final dépend du chemin, donc il ne se lit pas sur S_T.

    Renvoie : un dict avec le remboursement, le coupon, le bonus et le total
    (en fraction du nominal) pour chaque valeur de ST.
    """
    ST = np.asarray(ST, dtype=float)
    strike_reference = strike_pct * S0

    # au-dessus de la protection : 100 % ; en dessous : perte du sous-jacent (ex : 50/100 -> 50 %)
    remboursement = np.where(ST >= B_pdi * strike_reference, 1.0, ST / strike_reference)
    coupon = np.where(ST >= B_phoenix * strike_reference, coupon_final, 0.0)
    if bonus_threshold is not None:
        bonus = np.where(ST >= bonus_threshold * strike_reference, bonus_amount, 0.0)
    else:
        bonus = np.zeros_like(ST)

    return {"remboursement": remboursement, "coupon": coupon, "bonus": bonus,
            "total": remboursement + coupon + bonus}
```

- **Docstring** : remboursement d'un Phoenix **non rappelé**, en fonction du prix final. Elle sert au graphe **et** au calcul des flux : la règle de maturité n'est écrite qu'ici. Avant, la même formule était recopiée dans la fonction de flux ; rien ne garantissait que la courbe affichée corresponde au prix calculé.
- `ST = np.asarray(ST, dtype=float)` : accepte un nombre, une liste ou un tableau (la grille du graphe ou les prix finaux simulés).
- `strike_reference = strike_pct * S0` : le niveau de référence des barrières.
- `remboursement = np.where(ST >= B_pdi * strike_reference, 1.0, ST / strike_reference)` : `np.where(condition, a, b)` est un « si alors sinon » vectorisé. Au-dessus de la protection : 100 %. En dessous : perte proportionnelle à la baisse depuis le **strike** (pas depuis la barrière) : un sous-jacent à 45 % rembourse 45 %, pas 45/60.
- `coupon = np.where(ST >= B_phoenix * strike_reference, coupon_final, 0.0)` : le dernier coupon si la barrière coupon est atteinte.
- `if bonus_threshold is not None:` : bonus optionnel au-dessus d'un seuil ; sinon un tableau de zéros de même forme (`np.zeros_like`).
- `return {...}` : les trois composantes et leur total. Le graphe utilise `total` ; le moteur passe `coupon_final=0` car il traite le dernier coupon dans sa boucle.
- **Limite pour le graphe :** avec l'effet mémoire, le coupon final dépend des coupons manqués avant, donc du chemin. Impossible de le représenter en fonction du seul S_T : le graphe ne compte que le dernier coupon, et l'interface l'écrit en note.

### 5. `calculer_remboursement_autocall_maturite()` — règle de maturité de l'Athéna

```python
def calculer_remboursement_autocall_maturite(ST, S0, K_auto, B_pdi, coupons_accumules):
    """Remboursement à maturité d'un Autocall Plain qui n'a PAS été rappelé.

    Tous les coupons accumulés si S_T >= K_auto*S0, sinon aucun.
    Capital : 100 %, sauf sous la protection où il vaut S_T/S0.
    B_pdi=None : capital toujours remboursé à 100 % dans le modèle.
    Sert au graphe ET au calcul des flux.
    """
    ST = np.asarray(ST, dtype=float)
    capital = np.ones_like(ST)
    if B_pdi is not None:
        capital = np.where(ST >= B_pdi * S0, 1.0, ST / S0)
    coupons = np.where(ST >= K_auto * S0, coupons_accumules, 0.0)
    return {"capital": capital, "coupons": coupons, "total": capital + coupons}
```

- `capital = np.ones_like(ST)` : par défaut, 100 % du capital (cas sans protection, `B_pdi=None`).
- `if B_pdi is not None: capital = np.where(ST >= B_pdi * S0, 1.0, ST / S0)` : avec protection, perte proportionnelle sous la barrière.
- `coupons = np.where(ST >= K_auto * S0, coupons_accumules, 0.0)` : **tous** les coupons accumulés si le seuil final est atteint, **aucun** sinon.
- `return {"capital": ..., "coupons": ..., "total": ...}`. Comme pour le Phoenix, la même fonction sert au graphe (`main.py`) et aux flux.

### 6. `_calculer_flux_phoenix()` — le cœur du Phoenix

```python
def _calculer_flux_phoenix(prix, S0, r, obs_dates, K_auto, B_phoenix, B_pdi, coupon_schedule,
                           memory, has_autocall, bonus_threshold, bonus_amount, strike_pct, step_down=0.0):
    """Suit les flux du Phoenix pour chaque scénario.

    À chaque date : rappel si S >= barrière de rappel, coupon si S >= barrière
    coupon (avec ou sans effet mémoire). À maturité : remboursement final.
    Renvoie : un dict avec les flux actualisés, les coupons actualisés, la date
    de rappel (-1 si jamais), S_T et un masque des scénarios en perte.
    """
    n_dates = len(obs_dates)
    n_simulations = prix.shape[0]

    # je passe les barrières en niveau de prix (ex : 70 % d'un strike à 100 -> 70)
    strike_reference = strike_pct * S0
    B_phoenix_level = B_phoenix * strike_reference
    rappel_levels = barrieres_de_rappel(K_auto, step_down, n_dates) * strike_reference

    flux_actualises = np.zeros(n_simulations)      # tout ce que le client reçoit, actualisé
    coupons_actualises = np.zeros(n_simulations)   # seulement la partie coupons
    rappele = np.zeros(n_simulations, dtype=bool)  # False tant que pas rappelé
    date_rappel = np.full(n_simulations, -1)       # -1 = jamais rappelé
    flux_attendus = np.zeros(n_dates)
    flux_attendus_actualises = np.zeros(n_dates)
    coupons_en_attente = np.zeros(n_simulations)   # j'en ai besoin pour l'effet mémoire

    for k in range(1, n_dates + 1):
        t_k = obs_dates[k - 1]
        S_k = prix[:, k]
        actualisation = np.exp(-r * t_k)

        # je ne regarde que les scénarios encore en vie
        actifs = ~rappele

        # je bloque le rappel à la dernière date, à maturité je passe par le remboursement final
        # (sinon mon bonus ne serait jamais versé)
        if has_autocall and k < n_dates:
            autocall_now = actifs & (S_k >= rappel_levels[k - 1])
        else:
            autocall_now = np.zeros(n_simulations, dtype=bool)

        coupon_du = actifs & (S_k >= B_phoenix_level)

        coupon_periode = coupon_schedule[k - 1]
        if memory:
            # j'accumule le coupon de la période, et je paie tout le stock dès que c'est au-dessus
            coupons_en_attente += np.where(actifs, coupon_periode, 0.0)
            montant_coupon = np.where(coupon_du, coupons_en_attente, 0.0)
            coupons_en_attente = np.where(coupon_du, 0.0, coupons_en_attente)  # je remets à 0 si c'est payé
        else:
            # sans mémoire un coupon raté est perdu
            montant_coupon = np.where(coupon_du, coupon_periode, 0.0)

        coupons_actualises += montant_coupon * actualisation
        flux_actualises += montant_coupon * actualisation
        # si rappel : je rends le nominal (1 = 100 %)
        flux_actualises += np.where(autocall_now, actualisation, 0.0)

        paiement = montant_coupon + autocall_now.astype(float)
        flux_attendus[k-1] += np.mean(paiement)
        flux_attendus_actualises[k-1] += np.mean(paiement * actualisation)
        date_rappel[autocall_now] = k - 1
        rappele = rappele | autocall_now

    # maturité : je traite ceux qui n'ont jamais été rappelés
    # (le coupon de la dernière date a déjà été traité dans la boucle, coupon_final=0 ici)
    S_T = prix[:, n_dates]
    actualisation_T = np.exp(-r * obs_dates[-1])
    non_rappelees = ~rappele
    final = calculer_remboursement_phoenix_maturite(S_T, S0, B_phoenix, B_pdi, 0.0, strike_pct,
                                                    bonus_threshold, bonus_amount)
    remboursement_T = np.where(non_rappelees, final["total"], 0.0)

    flux_actualises += remboursement_T * actualisation_T
    flux_attendus[-1] += np.mean(remboursement_T)
    flux_attendus_actualises[-1] += np.mean(remboursement_T * actualisation_T)

    return {
        "flux": flux_actualises,
        "flux_attendus": flux_attendus,
        "flux_attendus_actualises": flux_attendus_actualises,
        "coupons": coupons_actualises,
        "date_rappel": date_rappel,
        "S_T": S_T,
        "perte_capital": non_rappelees & (S_T < B_pdi * strike_reference),
        "strike_reference": strike_reference,
    }
```

La bannière `# === Phoenix : les flux scénario par scénario ===` ouvre la section. `prix` est la matrice simulée (une ligne par trajectoire, une colonne par date).

**Préparation**
- `n_dates`, `n_simulations` : dimensions du problème (`prix.shape[0]` = nombre de lignes).
- `strike_reference`, `B_phoenix_level`, `rappel_levels` : les barrières converties **en prix** une fois pour toutes ; `rappel_levels` vient de `barrieres_de_rappel` (step-down compris).
- Les tableaux de suivi, un élément par trajectoire :
  - `flux_actualises` : tout ce que le client reçoit, actualisé ;
  - `coupons_actualises` : uniquement la part coupons ;
  - `rappele` : `False` tant que la trajectoire n'a pas été rappelée (`dtype=bool`) ;
  - `date_rappel` : indice de la date de rappel, `-1` si jamais (`np.full` remplit avec une valeur) ;
  - `coupons_en_attente` : coupons manqués, pour l'effet mémoire.
- `flux_attendus` et `flux_attendus_actualises` : un élément par **date** : le paiement moyen à chaque date (tableau « flux par date » de l'interface).

**Boucle sur les dates** (`for k in range(1, n_dates + 1):` ; k = 1 pour la première date)
- `t_k`, `S_k = prix[:, k]`, `actualisation = np.exp(-r * t_k)` : la date, les prix de toutes les trajectoires à cette date, le facteur d'actualisation.
- `actifs = ~rappele` : `~` inverse un tableau de booléens. On ne paie plus rien à une trajectoire déjà rappelée : toutes les conditions sont combinées avec `actifs &`.
- **Rappel :** `if has_autocall and k < n_dates:` puis `autocall_now = actifs & (S_k >= rappel_levels[k - 1])`. **Le rappel est bloqué à la dernière date** (`k < n_dates`). Problème rencontré : un produit « rappelé » à maturité ne passait jamais par le remboursement final, donc le **bonus n'était jamais versé**. Désormais la maturité passe toujours par le remboursement final (qui rembourse aussi 100 % au-dessus de la protection : même résultat, plus le bonus). Sinon `autocall_now` est un tableau de `False`.
- **Coupon :** `coupon_du = actifs & (S_k >= B_phoenix_level)` ; `coupon_periode = coupon_schedule[k - 1]` (le coupon peut varier par date : **step-up**).
  - avec mémoire : on ajoute le coupon de la période au stock (`coupons_en_attente += np.where(actifs, coupon_periode, 0.0)`), on paie tout le stock si la condition est remplie, puis on le remet à zéro pour les trajectoires payées ;
  - sans mémoire : un coupon raté est perdu (`np.where(coupon_du, coupon_periode, 0.0)`).
- **Paiements :** `coupons_actualises += ...` et `flux_actualises += montant_coupon * actualisation` ; si rappel, on rend le nominal (`np.where(autocall_now, actualisation, 0.0)`, 1 = 100 %). Chaque flux est actualisé **à sa propre date** : un rappel précoce vaut un peu plus qu'un remboursement tardif.
- **Flux par date :** `paiement = montant_coupon + autocall_now.astype(float)` (le booléen devient 0 ou 1), puis la moyenne sur **toutes** les trajectoires, y compris celles qui ne paient rien. Conséquence vérifiable : la somme des flux actualisés par date redonne le prix.
- `date_rappel[autocall_now] = k - 1` et `rappele = rappele | autocall_now` : on mémorise la date et on « éteint » les trajectoires rappelées (`|` = ou logique).

**Maturité** (trajectoires jamais rappelées)
- `S_T`, `actualisation_T`, `non_rappelees = ~rappele`.
- `final = calculer_remboursement_phoenix_maturite(S_T, S0, B_phoenix, B_pdi, 0.0, ...)` : la règle commune. `coupon_final = 0.0` car le coupon de la dernière date a **déjà** été traité dans la boucle (qui va jusqu'à `n_dates` inclus).
- `remboursement_T = np.where(non_rappelees, final["total"], 0.0)` : seules les trajectoires non rappelées touchent ce remboursement.
- On l'ajoute aux flux actualisés et aux flux de la dernière date.

**Résultat** : un dictionnaire avec les flux, les flux par date, les coupons, la date de rappel, les prix finaux, le masque des trajectoires **en perte** (`non_rappelees & (S_T < protection)`) et le niveau de référence, utilisés par les statistiques.

### 7. `_calculer_flux_autocall()` — l'Athéna

```python
def _calculer_flux_autocall(prix, S0, r, obs_dates, K_auto, B_pdi, coupon,
                            has_autocall, first_call_date, step_down=0.0):
    """Suit les flux du Plain sur des cours déjà simulés, comme pour le Phoenix.

    Les coupons sont accumulés depuis le début et payés à la sortie,
    jamais aux dates intermédiaires.
    """
    n_dates = len(obs_dates)
    n_simulations = prix.shape[0]
    rappel_levels = barrieres_de_rappel(K_auto, step_down, n_dates) * S0

    flux_actualises = np.zeros(n_simulations)
    coupons_actualises = np.zeros(n_simulations)
    rappele = np.zeros(n_simulations, dtype=bool)
    date_rappel = np.full(n_simulations, -1)
    flux_attendus = np.zeros(n_dates)
    flux_attendus_actualises = np.zeros(n_dates)
    nombre_coupons = np.zeros(n_simulations)

    for k in range(1, n_dates + 1):
        t_k = obs_dates[k - 1]
        S_k = prix[:, k]
        actualisation = np.exp(-r * t_k)
        actifs = ~rappele
        coupons_accumules = coupon * k

        rappel_autorise = first_call_date is None or t_k >= first_call_date
        if has_autocall and k < n_dates and rappel_autorise:
            autocall_now = actifs & (S_k >= rappel_levels[k - 1])
        else:
            autocall_now = np.zeros(n_simulations, dtype=bool)

        # À la sortie, je paie d'un coup tous les coupons accumulés.
        montant_coupon = np.where(autocall_now, coupons_accumules, 0.0)
        coupons_actualises += montant_coupon * actualisation
        flux_actualises += montant_coupon * actualisation
        flux_actualises += np.where(autocall_now, actualisation, 0.0)
        nombre_coupons[autocall_now] = k
        paiement = montant_coupon + autocall_now.astype(float)
        flux_attendus[k-1] += np.mean(paiement)
        flux_attendus_actualises[k-1] += np.mean(paiement * actualisation)
        date_rappel[autocall_now] = k - 1
        rappele = rappele | autocall_now

    # Comme pour le Phoenix, je traite à part ceux qui arrivent à maturité.
    S_T = prix[:, n_dates]
    actualisation_T = np.exp(-r * obs_dates[-1])
    non_rappelees = ~rappele
    final = calculer_remboursement_autocall_maturite(S_T, S0, K_auto, B_pdi, coupon * n_dates)
    montant_coupon = np.where(non_rappelees, final["coupons"], 0.0)
    remboursement_T = np.where(non_rappelees, final["capital"], 0.0)
    nombre_coupons[non_rappelees & (S_T >= K_auto * S0)] = n_dates

    coupons_actualises += montant_coupon * actualisation_T
    flux_actualises += (montant_coupon + remboursement_T) * actualisation_T
    flux_attendus[-1] += np.mean(montant_coupon + remboursement_T)
    flux_attendus_actualises[-1] += np.mean((montant_coupon + remboursement_T) * actualisation_T)

    perte_capital = np.zeros(n_simulations, dtype=bool)
    if B_pdi is not None:
        perte_capital = non_rappelees & (S_T < B_pdi * S0)

    return {
        "flux": flux_actualises,
        "flux_attendus": flux_attendus,
        "flux_attendus_actualises": flux_attendus_actualises,
        "coupons": coupons_actualises,
        "date_rappel": date_rappel,
        "S_T": S_T,
        "perte_capital": perte_capital,
        "strike_reference": S0,
        "nombre_coupons": nombre_coupons,
    }
```

La bannière ouvre la section. Même structure que le Phoenix ; seules les différences sont détaillées.

- `rappel_levels = barrieres_de_rappel(K_auto, step_down, n_dates) * S0` : barrières en fraction de **S0**.
- `nombre_coupons` : combien de coupons chaque trajectoire a touchés (pour la statistique « nombre moyen de coupons »).
- `coupons_accumules = coupon * k` : pas de condition de coupon intermédiaire ; à la k-ième date, le stock vaut simplement k × coupon.
- `rappel_autorise = first_call_date is None or t_k >= first_call_date` : période de **non-rappel** au début (fréquent en pratique : « premier rappel possible à 12 mois »). Les coupons s'accumulent quand même pendant cette période.
- `if has_autocall and k < n_dates and rappel_autorise:` : même blocage du rappel à la dernière date que pour le Phoenix.
- `montant_coupon = np.where(autocall_now, coupons_accumules, 0.0)` : les coupons ne sont payés **qu'au rappel**, tous d'un coup, avec le nominal.
- `nombre_coupons[autocall_now] = k` : une trajectoire rappelée à la k-ième date a touché k coupons.

**Maturité**
- `final = calculer_remboursement_autocall_maturite(S_T, S0, K_auto, B_pdi, coupon * n_dates)` : la règle commune, avec tous les coupons accumulés. Le seuil final est `K_auto` **sans** step-down : c'est voulu (l'interface précise que le seuil du coupon final ne change pas).
- `montant_coupon` et `remboursement_T` : coupons et capital des trajectoires non rappelées.
- `nombre_coupons[non_rappelees & (S_T >= K_auto * S0)] = n_dates` : celles qui touchent les coupons à maturité les touchent tous.
- Flux actualisés et flux de la dernière date mis à jour.
- `perte_capital` : seulement s'il existe une protection (`B_pdi` non `None`).

### 8. `_calculer_statistiques()` — statistiques communes

```python
def _calculer_statistiques(res, dates, K_auto, step_down):
    """Statistiques communes aux deux produits, à partir du résultat d'une fonction de flux.

    Toutes les moyennes portent sur toutes les trajectoires, sauf le
    remboursement moyen si perte (moyenne conditionnelle, hors coupons et bonus).
    """
    flux_actualises, date_rappel, perte = res["flux"], res["date_rappel"], res["perte_capital"]
    n_simulations = len(flux_actualises)
    prix = float(np.mean(flux_actualises))
    erreur_type = float(np.std(flux_actualises, ddof=1) / np.sqrt(n_simulations))
    # np.maximum(..., 0) évite l'indice -1 (dernière date) pour les non-rappelés
    durees = np.where(date_rappel >= 0, dates[np.maximum(date_rappel, 0)], dates[-1])
    principal_si_perte = res["S_T"][perte] / res["strike_reference"]
    return {
        "prix": prix,
        "erreur_type": erreur_type,
        "ic95": (prix - 1.96 * erreur_type, prix + 1.96 * erreur_type),
        "marge_emetteur": 1.0 - prix,
        "proba_rappel_par_date": [float(np.mean(date_rappel == k)) for k in range(len(dates))],
        "proba_maturite": float(np.mean(date_rappel == -1)),
        "proba_perte_capital": float(np.mean(perte)),
        "remboursement_moyen_si_perte": float(np.mean(principal_si_perte)) if perte.any() else None,
        "duree_de_vie_moyenne": float(np.mean(durees)),
        "coupons_moyens_actualises": float(np.mean(res["coupons"])),
        "obs_dates": dates.tolist(),
        "flux_attendus_par_date": res["flux_attendus"].tolist(),
        "flux_attendus_actualises_par_date": res["flux_attendus_actualises"].tolist(),
        "barrieres_rappel": barrieres_de_rappel(K_auto, step_down, len(dates)).tolist(),
    }
```

- La bannière `# === Statistiques communes ===` ouvre la section.
- Elle reçoit le résultat d'une fonction de flux (`res`) et calcule tout ce qui est commun aux deux produits.
- `prix = float(np.mean(flux_actualises))` : la valeur théorique en fraction du nominal.
- `erreur_type = ... / np.sqrt(n_simulations)` : erreur standard Monte Carlo ; `ic95` : prix ± 1,96 × erreur.
- `durees = np.where(date_rappel >= 0, dates[np.maximum(date_rappel, 0)], dates[-1])` : la date de sortie de chaque trajectoire (date de rappel, ou maturité). `np.maximum(..., 0)` évite l'indice −1, qui pointerait sur la dernière date en Python.
- `principal_si_perte = res["S_T"][perte] / res["strike_reference"]` : le capital remboursé des seules trajectoires en perte (indexation par masque booléen).

| Statistique | Lecture |
|---|---|
| `prix` | Valeur théorique en % du nominal |
| `ic95` | Intervalle de confiance Monte Carlo à 95 % |
| `marge_emetteur` | 100 % − valeur : ce que la banque garde (avant crédit, frais, couverture) |
| `proba_rappel_par_date` | Part des trajectoires rappelées à chaque date (`np.mean` d'un booléen = une proportion) |
| `proba_maturite` | Part des trajectoires jamais rappelées |
| `proba_perte_capital` | Part qui finit sous la protection |
| `remboursement_moyen_si_perte` | Capital moyen récupéré **sachant** qu'il y a perte (hors coupons et bonus) ; `None` s'il n'y a aucune perte, pour éviter une moyenne vide (`nan`) qui casserait le JSON |
| `duree_de_vie_moyenne` | Date de sortie moyenne, en années |
| `coupons_moyens_actualises` | Valeur actuelle moyenne des coupons |
| `obs_dates`, `flux_attendus_*`, `barrieres_rappel` | Calendrier, flux par date et barrières effectives, pour l'affichage |

**Pourquoi la marge est-elle importante pédagogiquement ?** Elle montre qu'un produit vendu 100 % vaut souvent 95–97 % en théorie : l'écart rémunère la structuration, la couverture et le risque de crédit.

### 9. `analyse_phoenix()` — fonction appelée par `main.py`

```python
def analyse_phoenix(S0, r, q, sigma, obs_dates, K_auto, B_phoenix, B_pdi, coupon,
                    n_simulations, memory=False, has_autocall=True,
                    bonus_threshold=None, bonus_amount=0.0, strike_pct=1.0, seed=None, step_down=0.0):
    """Price le Phoenix et calcule les stats des scénarios.

    Paramètres : S0, r, q, sigma en décimal, obs_dates en années, barrières
    K_auto / B_phoenix / B_pdi en fraction du strike (0.7 = 70 %), coupon
    (un nombre ou une liste pour un step-up), n_simulations, memory,
    has_autocall, bonus_threshold / bonus_amount (optionnels), strike_pct,
    seed (pour retomber sur les mêmes tirages), step_down.
    """
    dates = np.asarray(obs_dates, dtype=float)
    # coupon fixe -> je mets le même à chaque date, sinon j'ai une liste (step-up)
    coupon_schedule = np.broadcast_to(np.asarray(coupon, dtype=float), dates.shape)

    prix = simuler_cours_observations(S0, r, q, sigma, dates, n_simulations, np.random.default_rng(seed))
    res = _calculer_flux_phoenix(prix, S0, r, dates, K_auto, B_phoenix, B_pdi,
                                 coupon_schedule, memory, has_autocall,
                                 bonus_threshold, bonus_amount, strike_pct, step_down)
    return {**_calculer_statistiques(res, dates, K_auto, step_down),
            "coupon_schedule": coupon_schedule.tolist()}
```

- La bannière ouvre la section des fonctions publiques ; la docstring liste tous les paramètres et leurs unités.
- `dates = np.asarray(obs_dates, dtype=float)`.
- `coupon_schedule = np.broadcast_to(np.asarray(coupon, dtype=float), dates.shape)` : transforme un coupon fixe en liste constante, et laisse une liste step-up telle quelle. La fonction de flux ne gère ainsi qu'un seul cas.
- `prix = simuler_cours_observations(..., np.random.default_rng(seed))` : les trajectoires, avec graine.
- `res = _calculer_flux_phoenix(...)` : les flux.
- `return {**_calculer_statistiques(res, dates, K_auto, step_down), "coupon_schedule": ...}` : les statistiques communes, plus le calendrier de coupons (`.tolist()` convertit en liste Python pour le JSON).

### 10. `analyse_autocall_plain()` — fonction appelée par `main.py`

```python
def analyse_autocall_plain(S0, r, q, sigma, obs_dates, K_auto, B_pdi, coupon,
                           n_simulations=50000, first_call_date=None, seed=None, has_autocall=True, step_down=0.0):
    """Autocall Plain : coupon accumulé jusqu'au rappel ou à maturité.

    Conventions identiques au Phoenix : r, q, sigma et coupon en décimal,
    barrières en fraction de S0, dates en années, montants en fraction du nominal.
    Exemple : coupon=0.02 signifie 2 % PAR OBSERVATION (pas par an).

    Rappel à la k-ième date (k = 1, 2...) si S >= barrière : paiement de 1 + k*coupon.
    Sans rappel, à maturité : tous les coupons si S_T >= K_auto*S0 ; sinon
    aucun coupon. Capital : 1, sauf sous B_pdi*S0 où il vaut S_T/S0.
    has_autocall=False supprime uniquement le rappel anticipé.
    B_pdi=None désactive la perte conditionnelle de capital.
    first_call_date décale le début des rappels, sans décaler l'accumulation.
    La protection n'est jamais surveillée entre les dates ni avant maturité.

    Traduction en phrase : on attend le rappel, puis on paie d'un coup le
    nominal et les coupons accumulés. Ce n'est pas un Phoenix à coupons périodiques.
    """
    dates = np.asarray(obs_dates, dtype=float)

    prix = simuler_cours_observations(S0, r, q, sigma, dates, n_simulations, np.random.default_rng(seed))
    res = _calculer_flux_autocall(prix, S0, r, dates, K_auto, B_pdi, coupon,
                                  has_autocall, first_call_date if has_autocall else None, step_down)
    return {**_calculer_statistiques(res, dates, K_auto, step_down),
            "nombre_moyen_coupons": float(np.mean(res["nombre_coupons"]))}
```

- **Docstring** : la règle complète du produit, avec un exemple d'unité (« coupon=0.02 signifie 2 % **par observation**, pas par an »), et une phrase de résumé : « on attend le rappel, puis on paie d'un coup le nominal et les coupons accumulés. Ce n'est pas un Phoenix à coupons périodiques. » C'est la confusion la plus fréquente chez les étudiants.
- Graine → simulation → flux → statistiques, comme pour le Phoenix.
- `first_call_date if has_autocall else None` : sans rappel, la date de premier rappel n'a pas de sens ; on la neutralise.
- Le résultat ajoute `nombre_moyen_coupons` aux statistiques communes.

---

## Pour aller plus loin

- **Exercice :** vérifiez que `sum(flux_attendus_actualises_par_date)` est égal au prix (à l'arrondi près).
- **Exercice :** augmentez la vol de 20 % à 30 % : le prix du Phoenix baisse (le put vendu par le client vaut plus cher). C'est pour ça que les Phoenix sur actions volatiles offrent de gros coupons.
- **Amélioration :** grecques par différences finies, avec la même graine (`seed`) pour que le bruit s'annule.
