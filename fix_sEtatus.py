import re

with open('ui/pages/fiscal_pages.py', 'r', encoding='utf-8') as f:
    text = f.read()

replacements = {
    "sÉtatus": "status",
    "Sétatut": "Statut",
    "eétat": "etat",
    "État104": "Etat104", # if there is a class name Etat104Page
}

for old, new in replacements.items():
    text = text.replace(old, new)

# Ensure class name is still Etat104Page
text = text.replace('class État104Page', 'class Etat104Page')

with open('ui/pages/fiscal_pages.py', 'w', encoding='utf-8') as f:
    f.write(text)
