import re

with open('app/models/__init__.py', 'r', encoding='utf-8') as f:
    text = f.read()

if 'fiscal' not in text:
    text = text.replace('from app.models.report import SavedReport', 'from app.models.report import SavedReport\nfrom app.models.fiscal import ExonerationTVA')
    text = text.replace('"SavedReport",', '"SavedReport",\n    "ExonerationTVA",')

with open('app/models/__init__.py', 'w', encoding='utf-8') as f:
    f.write(text)
