import re

with open('ui/pages/fiscal_pages.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('class EEtat104Page', 'class Etat104Page')

with open('ui/pages/fiscal_pages.py', 'w', encoding='utf-8') as f:
    f.write(text)

# Also fix the main_window.py where it imports Etat104Page
with open('ui/main_window.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('EEtat104Page', 'Etat104Page')

with open('ui/main_window.py', 'w', encoding='utf-8') as f:
    f.write(text)
