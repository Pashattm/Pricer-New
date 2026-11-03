# `pdf_engine.py` — export PDF du dernier calcul

Toute la philosophie du fichier tient dans sa première ligne : le PDF **relit** l'instantané mémorisé par `main.py` (paramètres + résultats) et le met en page. Il ne recalcule rien. Le PDF correspond donc **exactement** à ce qui était affiché, même si le formulaire a été modifié depuis.

**Pourquoi `reportlab` ?**
- C'est la bibliothèque PDF Python la plus répandue, sans dépendance système (contrairement à WeasyPrint, qui demande des bibliothèques graphiques).
- Son module **Platypus** permet d'empiler des blocs (titre, paragraphe, tableau, dessin) ; `reportlab` gère la pagination tout seul.

---

# Le code, ligne par ligne
### 1. En-tête du fichier

```python
"""Export PDF du calcul mémorisé : aucun moteur de pricing n'est rappelé.

Le PDF relit l'instantané gardé par main.py (paramètres + résultats) : il
correspond donc exactement à ce qui était affiché à l'écran.
"""
```

- Elle résume le principe : aucun moteur de pricing n'est rappelé ; le PDF relit l'instantané gardé par `main.py`, donc il correspond à l'écran.

### 2. Imports

```python
from io import BytesIO
from html import escape
```

- `from io import BytesIO` : un « fichier » en mémoire. Le PDF y est écrit, puis envoyé au navigateur sans jamais toucher le disque.
- `from html import escape` : transforme `&` en `&amp;`, `<` en `&lt;`, etc. (voir `texte` ci-dessous).

### 3. `generer_pdf_calcul()`

```python
def generer_pdf_calcul(snapshot):
    """Construit le PDF en mémoire et renvoie ses octets."""
    # reportlab est importé ici : sans lui, seul l'export échoue, pas tout le pricer
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4

    styles = getSampleStyleSheet()
    sortie = BytesIO()
    story = []   # la liste ordonnée des blocs du document

    def texte(t, style='BodyText'):
        # escape : un « & » ou un « < » dans une valeur casserait le mini-HTML de reportlab
        return Paragraph(escape(str(t)), styles[style])

    def nombre(x):
        # 6 chiffres significatifs avec séparateur de milliers ; les booléens restent du texte
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            return f'{x:,.6g}'
        return str(x)

    def table(lignes):
        t = Table([[texte(c) for c in ligne] for ligne in lignes],
                  colWidths=[230, 280], repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9edf2')),
            ('LINEBELOW', (0, 0), (-1, -1), .3, colors.lightgrey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    # Titre, route et date du calcul
    story += [texte('PRICER - Dernier calcul', 'Title'),
              texte(snapshot['route'] + ' | ' + snapshot['date']),
              Spacer(1, 14)]

    # Paramètres tels que saisis
    parametres = [[cle, nombre(valeur)] for cle, valeur in snapshot['parametres'].items() if valeur is not None]
    story += [texte('Paramètres du calcul', 'Heading2'), table([['Paramètre', 'Valeur']] + parametres)]

    # Résultats simples (les listes et dictionnaires seraient illisibles en tableau)
    r = snapshot['resultats']
    resultats = [[cle, nombre(valeur)] for cle, valeur in r.items()
                 if not isinstance(valeur, (dict, list)) and valeur is not None]
    story += [Spacer(1, 12), texte('Résultats', 'Heading2'), table([['Indicateur', 'Valeur']] + resultats)]

    # Intervalles de confiance Monte Carlo
    for cle in ['ic95', 'ic95_pct']:
        if cle in r:
            story.append(texte(cle + ' : ' + ' à '.join(nombre(x) for x in r[cle])))

    # Flux moyens par date (produits structurés)
    dates = r.get('obs_dates', [])
    flux = r.get('flux_attendus_par_date', [])
    flux_actualises = r.get('flux_attendus_actualises_par_date', [])
    if dates and flux:
        lignes = [[nombre(t), nombre(flux[i]) + (' / ' + nombre(flux_actualises[i]) if flux_actualises else '')]
                  for i, t in enumerate(dates)]
        story += [texte('Flux moyens par date', 'Heading2'),
                  table([['Date (années)', 'Flux moyen / actualisé']] + lignes)]

    # Grecques
    if 'primaires' in r:
        grecques = [[cle, nombre(valeur)] for cle, valeur in r['primaires'].items()]
        story += [texte('Grecques', 'Heading2'), table([['Grecque', 'Valeur']] + grecques)]

    # Graphe du payoff, dessiné en vectoriel
    if r.get('ST_grid') and r.get('payoff'):
        from reportlab.graphics.shapes import Drawing, PolyLine, String, Line
        xs, ys = r['ST_grid'], r['payoff']
        lo, hi = min(ys), max(ys)
        hauteur = max(hi - lo, 1e-9)            # évite une division par zéro si le payoff est plat
        largeur = max(max(xs) - min(xs), 1e-9)
        titre_graphe = 'Remboursement / payoff à maturité (sans rappel antérieur)'
        dessin = Drawing(510, 180)
        dessin.add(String(15, 165, titre_graphe, fontSize=9))
        points = []
        for x, y in zip(xs, ys):
            points += [25 + 460 * (x - min(xs)) / largeur, 25 + 125 * (y - lo) / hauteur]
        dessin.add(Line(25, 25, 485, 25, strokeColor=colors.grey))
        dessin.add(PolyLine(points, strokeColor=colors.darkorange, strokeWidth=1.4))
        dessin.add(String(25, 10, f'Sous-jacent : {min(xs):.3g} à {max(xs):.3g} | payoff : {lo:.3g} à {hi:.3g}',
                          fontSize=8))
        story += [Spacer(1, 14), dessin]

    # Avertissement final
    avertissement = ' '.join([
        'Résultat mémorisé, sans recalcul. Taux et volatilités saisis en %, montants dans la devise des paramètres.',
        'Les résultats Monte Carlo dépendent du modèle et du nombre de simulations ; ce ne sont pas des prévisions.',
        'Hors défaut émetteur, frais et funding. Pour les notes, marge affichée = 100 % moins valeur théorique.',
    ])
    story += [Spacer(1, 14), texte(avertissement)]

    def pied_de_page(canvas, doc):
        canvas.drawRightString(550, 25, str(doc.page))

    document = SimpleDocTemplate(sortie, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=40, bottomMargin=42)
    document.build(story, onFirstPage=pied_de_page, onLaterPages=pied_de_page)
    return sortie.getvalue()
```

**Imports de `reportlab`, dans la fonction**
- Les quatre lignes `from reportlab...` sont placées **dans** la fonction : si `reportlab` n'est pas installé, le reste du pricer fonctionne ; seul l'export lève une `ImportError`, que `main.py` transforme en message « Installez les dépendances ».
- `SimpleDocTemplate` (le document), `Paragraph` (un paragraphe), `Spacer` (un espace vertical), `Table` et `TableStyle` (tableaux), `getSampleStyleSheet` (styles prêts à l'emploi), `colors`, `A4` (format de page).

**Préparation**
- `styles = getSampleStyleSheet()` : les styles par défaut (`Title`, `Heading2`, `BodyText`).
- `sortie = BytesIO()` : le fichier en mémoire.
- `story = []` : la liste ordonnée des blocs du document (vocabulaire de Platypus).

**Trois petites fonctions internes** (définies dans la fonction, car elles n'ont de sens qu'ici)
- `texte(t, style)` : crée un paragraphe. `escape` est **indispensable** : les `Paragraph` de reportlab interprètent un mini-HTML ; un `&` dans une valeur (par exemple « P&L ») ou un `<` casserait la génération.
- `nombre(x)` : `f'{x:,.6g}'` affiche 6 chiffres significatifs avec séparateur de milliers. Les booléens sont exclus (sinon `True` s'afficherait « 1 ») ; tout le reste devient du texte.
- `table(lignes)` : un tableau à deux colonnes (230 et 280 points de large). Chaque cellule est un `Paragraph`, donc un texte long **passe à la ligne** au lieu de déborder. `repeatRows=1` répète l'en-tête en haut de chaque page. Le style : alignement en haut, fond gris clair pour l'en-tête (ligne 0), fines lignes de séparation, un peu d'espace sous chaque ligne. Les coordonnées `(0, 0), (-1, -1)` désignent « de la première cellule à la dernière ».

**Contenu du document, dans l'ordre**
- **Titre**, route appelée et date du calcul (UTC), puis un espace.
- **Paramètres** tels que reçus (donc en %, comme saisis), sans les valeurs vides (`if valeur is not None`).
- **Résultats simples** : on ne garde que les valeurs scalaires (`not isinstance(valeur, (dict, list))`) ; les grilles et les séries seraient illisibles dans un tableau.
- **Intervalles de confiance** : `' à '.join(...)` écrit « 9,8 à 10,2 ».
- **Flux moyens par date** : si la réponse contient des dates et des flux, un tableau date / flux moyen / flux actualisé. Tous les produits structurés renvoient ces champs sous les mêmes noms : un seul export pour tous.
- **Grecques**, si le résultat en contient (`primaires`).
- **Graphe du payoff**, dessiné en vectoriel si la réponse contient une grille et un payoff :
   - l'import de `Drawing`, `PolyLine`, `String`, `Line` n'est fait que si un graphe est nécessaire ;
   - `hauteur` et `largeur` : étendue des valeurs ; `max(..., 1e-9)` évite une division par zéro si toutes les valeurs sont égales (payoff plat) ;
   - `titre_graphe` : le titre du dessin ;
   - la boucle `for x, y in zip(xs, ys)` fait un **changement d'échelle** : chaque point est ramené dans un cadre de 460 × 125 points, décalé de 25 points du bord. `zip` parcourt les deux listes en parallèle ;
   - une ligne grise sert d'axe, la courbe est une `PolyLine` orange, et une légende indique les bornes min / max.
- **Avertissement final** : rappel des conventions, du fait que les résultats Monte Carlo ne sont pas des prévisions, et de la définition de la marge émetteur (hors défaut, frais et funding). `' '.join([...])` colle les phrases avec un espace.

**Fin**
- `pied_de_page(canvas, doc)` : écrit le numéro de page en bas à droite ; reportlab l'appelle sur chaque page (`onFirstPage`, `onLaterPages`).
- `SimpleDocTemplate(sortie, pagesize=A4, marges...)` puis `document.build(story, ...)` : reportlab assemble les blocs et gère la pagination.
- `return sortie.getvalue()` : les octets du PDF, envoyés par `main.py` avec `send_file`.

---

## Limites

- Mise en page simple (pas de logo, pas d'axes gradués détaillés sur le graphe : seulement les bornes min / max en légende).
- Dépend de l'instantané en mémoire : après 30 minutes ou un redémarrage du serveur, il faut relancer le calcul.
