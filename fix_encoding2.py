with open('ui/pages/fiscal_pages.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

replacements = {
    "Complmentaire": "Complémentaire",
    "rgularisation": "régularisation",
    "Mme": "Même",
    "Exonrations": "Exonérations",
    "Exonr": "Exonéré",
    "Collecte": "Collectée",
    "N Facture": "N° Facture",
    "Montant d": "Montant dû",
    "Factures": "Facturées",
    "Crances": "Créances",
}

for old, new in replacements.items():
    text = text.replace(old, new)

with open('ui/pages/fiscal_pages.py', 'w', encoding='utf-8') as f:
    f.write(text)
