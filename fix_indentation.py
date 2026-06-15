import os
import re

filepath = "ui/pages/fiscal_pages.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the bad indentation
# We replace 24 spaces (or whatever it is) with 12 spaces.
content = re.sub(r' +from app\.config import config', '            from app.config import config', content)
content = re.sub(r' +co = \{', '            co = {', content)
content = re.sub(r' +"name": config\.company_name,', '                "name": config.company_name,', content)
content = re.sub(r' +"address": config\.company_address,', '                "address": config.company_address,', content)
content = re.sub(r' +"nif": config\.company_nif,', '                "nif": config.company_nif,', content)
content = re.sub(r' +"nis": config\.company_nis,', '                "nis": config.company_nis,', content)
content = re.sub(r' +"rc": config\.company_rc,', '                "rc": config.company_rc,', content)
content = re.sub(r' +"ai": config\.company_ai,', '                "ai": config.company_ai,', content)
content = re.sub(r' +\}', '            }', content)
content = re.sub(r' +FiscalPDFExporter\.export', '            FiscalPDFExporter.export', content)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Indentation fixed.")
