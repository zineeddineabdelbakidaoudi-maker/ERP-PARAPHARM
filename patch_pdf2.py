import re

with open('app/utils/pdf_exporter.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix export_invoice_to_pdf loop
old_invoice_loop = """            ht = qty * uprice - disc
            tva = ht * tax_rate / 100.0
            total_ht  += ht
            total_tva += tva
            total_qty += int(qty)"""

new_invoice_loop = """            # Fix: uprice is TTC. Reverse calculate HT
            uprice_ht = uprice / (1 + tax_rate / 100.0)
            disc_ht = disc / (1 + tax_rate / 100.0)
            ht = (qty * uprice_ht) - disc_ht
            tva = ht * (tax_rate / 100.0)
            
            total_ht  += ht
            total_tva += tva
            total_qty += int(qty)"""

text = text.replace(old_invoice_loop, new_invoice_loop)

# Let's fix the totals in `totals` dictionary if needed
# Wait, `net_a_payer` will be `net_ht + total_tva` which will perfectly equal the sum of TTCs! This is correct now.

with open('app/utils/pdf_exporter.py', 'w', encoding='utf-8') as f:
    f.write(text)
