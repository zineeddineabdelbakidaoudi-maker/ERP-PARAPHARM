import re

with open('ui/pages/products_page.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('        from app.models.setting import AuditLog\n', '')
text = text.replace('from app.models.product import Category\n', 'from app.models.product import Category\nfrom app.models.setting import AuditLog\n')

with open('ui/pages/products_page.py', 'w', encoding='utf-8') as f:
    f.write(text)
