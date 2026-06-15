with open('ui/pages/deliveries_page.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if 1711 <= i <= 1720:  # 0-indexed: 1711 is line 1712
        if "reference_id=0" in line or "total_amount=0.0" in line or "paid_amount=excess" in line or "remaining_amount=-excess" in line or "status=DebtStatus.PAID.value" in line or "notes=" in line or line.strip() == ")" or "self.db_session.add(credit_debt)" in line:
            continue
    new_lines.append(line)

with open('ui/pages/deliveries_page.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
