import re

# Fix deliveries_page.py
with open('ui/pages/deliveries_page.py', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('if sale and sale.user:', 'if sale and sale.cashier:')
text = text.replace('creator_name = sale.user.full_name or sale.user.username', 'creator_name = sale.cashier.full_name or sale.cashier.username')
with open('ui/pages/deliveries_page.py', 'w', encoding='utf-8') as f:
    f.write(text)

# Fix invoices_page.py
with open('ui/pages/invoices_page.py', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('if inv.user:', 'if inv.cashier:')
text = text.replace('creator_name = inv.user.full_name or inv.user.username', 'creator_name = inv.cashier.full_name or inv.cashier.username')
with open('ui/pages/invoices_page.py', 'w', encoding='utf-8') as f:
    f.write(text)

# Fix additional_pages.py
with open('ui/pages/additional_pages.py', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('"user": f"User #{s.user_id}"', '"user": f"User #{s.cashier_id}"')
text = text.replace('s.user_id', 's.cashier_id') # just in case
with open('ui/pages/additional_pages.py', 'w', encoding='utf-8') as f:
    f.write(text)
