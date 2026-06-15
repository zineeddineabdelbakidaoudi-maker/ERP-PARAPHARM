with open('ui/pages/deliveries_page.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_history = False
for line in lines:
    if line.startswith('        def _show_delivery_history(self):'):
        in_history = True
        new_lines.append('    def _show_delivery_history(self):\n')
        continue
        
    if in_history:
        if line.startswith('from app.models.setting import AuditLog'):
            new_lines.append('        from app.models.setting import AuditLog\n')
            continue
            
        if line.startswith('        def _show_invoice_history(self):') or line.startswith('    def '):
            in_history = False
            new_lines.append(line)
            continue
            
        # Unindent by 4 spaces
        if line.startswith('    '):
            new_lines.append(line[4:])
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open('ui/pages/deliveries_page.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
