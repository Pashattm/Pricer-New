"""Export PDF du calcul mémorisé : aucun moteur de pricing n'est rappelé.

Le PDF relit l'instantané gardé par main.py (paramètres + résultats) : il
correspond donc exactement à ce qui était affiché à l'écran.
"""
from io import BytesIO
from html import escape


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
