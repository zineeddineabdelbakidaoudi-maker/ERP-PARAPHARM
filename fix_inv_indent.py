with open('ui/pages/invoices_page.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i in range(len(lines)):
    if lines[i] == '            from app.models.setting import AuditLog\n':
        lines[i] = '        from app.models.setting import AuditLog\n'
with open('ui/pages/invoices_page.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
