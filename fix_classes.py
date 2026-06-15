with open('ui/pages/fiscal_pages.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

replacements = {
    "FacturéesAvoirPage": "FacturesAvoirPage",
    "FacturéesComplementairePage": "FacturesComplementairePage",
    "FacturéesAchatPage": "FacturesAchatPage",
    "Etat104Page": "Etat104Page",
    "État104Page": "Etat104Page", 
    "Ét": "Et",
}

for old, new in replacements.items():
    text = text.replace(old, new)

with open('ui/pages/fiscal_pages.py', 'w', encoding='utf-8') as f:
    f.write(text)
