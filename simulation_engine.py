"""Simulateur commun : mouvement brownien géométrique sous la probabilité risque-neutre.

C'est le SEUL endroit du projet où la diffusion du sous-jacent est écrite.
Il est utilisé par :
- pricer_engine (Monte Carlo européen, digitales, Longstaff-Schwartz) ;
- strutu_engine (Phoenix, Athéna) ;

Convention : r, q, sigma en décimal, dates en années.
Les paramètres sont vérifiés par validation.py avant d'arriver ici.
"""

import numpy as np


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


