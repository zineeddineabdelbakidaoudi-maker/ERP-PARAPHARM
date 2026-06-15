with open('ui/pages/fiscal_pages.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

replacements = {
    "Ã‰": "É",
    "Ã©": "é",
    "Ãˆ": "È",
    "Ã¨": "è",
    "Ã€": "À",
    "Ã": "à", # sometimes à
    "Ã¢": "â",
    "Ãª": "ê",
    "Ã®": "î",
    "Ã´": "ô",
    "Ã»": "û",
    "Ã§": "ç",
    "Ã¯": "ï",
    "Ã«": "ë",
    "Ã¼": "ü",
    "Â°": "°",
    "Â": "",
    "Ã%tat 104": "État 104",
    "%tat 104 ?\" Registre des Ventes": "État 104 — Registre des Ventes",
    "%tat 104 prǦt pour l'export": "État 104 prêt pour l'export",
    "implǸmenter": "implémenter",
    "Ã%tat 104 ã€\" Registre des Ventes": "État 104 — Registre des Ventes",
    "DÃ©signation": "Désignation",
    "Ventes locales soumises Ã  TVA 19%": "Ventes locales soumises à TVA 19%",
    "Ventes locales soumises Ã  TVA 9%": "Ventes locales soumises à TVA 9%",
    "Ventes exonÃ©rÃ©es de TVA": "Ventes exonérées de TVA",
    "Avoirs Ã©mis (DÃ©duction)": "Avoirs émis (Déduction)",
    "PÃ©riode :": "Période :",
    "Actualiser": "Actualiser",
    "Exporter PDF": "Exporter PDF",
    "TVA 19% (DÃ©clarÃ©)": "TVA 19% (Déclaré)",
    "TVA 9% (DÃ©clarÃ©)": "TVA 9% (Déclaré)",
    "Droits de Timbre (EspÃ¨ces)": "Droits de Timbre (Espèces)",
    "RelevÃ© des Ventes": "Relevé des Ventes",
    "RÃ©f": "Réf",
    "Montant TTC": "Montant TTC",
    "DÃ©claration Mensuelle des ImpÃ´ts (G50)": "Déclaration Mensuelle des Impôts (G50)",
    "DÃ©claration": "Déclaration",
    "ImpÃ´ts": "Impôts",
    "Chiffre d'Affaires Imposable (TAP)": "Chiffre d'Affaires Imposable (TAP)",
}

for old, new in replacements.items():
    text = text.replace(old, new)
    
# also fix raw garbled text seen in the screenshot:
# Ã%tat 104 ã€" Registre des Ventes
text = text.replace('Ã%tat 104 ã€" Registre des Ventes', 'État 104 — Registre des Ventes')

with open('ui/pages/fiscal_pages.py', 'w', encoding='utf-8') as f:
    f.write(text)
