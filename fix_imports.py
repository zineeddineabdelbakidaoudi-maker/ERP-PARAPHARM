import re

# Fix deliveries_page.py
with open('ui/pages/deliveries_page.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(len(lines)):
    if lines[i] == 'from app.models.setting import AuditLog, SaleItem\n':
        lines[i] = '            from app.models.setting import AuditLog\n            from app.models.sale import SaleItem\n'
    elif lines[i] == 'from app.models.setting import AuditLog\n':
        lines[i] = '            from app.models.setting import AuditLog\n'
with open('ui/pages/deliveries_page.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

# Fix invoices_page.py
with open('ui/pages/invoices_page.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(len(lines)):
    if lines[i] == 'from app.models.setting import AuditLog\n':
        lines[i] = '            from app.models.setting import AuditLog\n'
with open('ui/pages/invoices_page.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

# Fix products_page.py
with open('ui/pages/products_page.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(len(lines)):
    if lines[i] == 'from app.models.setting import AuditLog\n':
        lines[i] = '        from app.models.setting import AuditLog\n'
with open('ui/pages/products_page.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
