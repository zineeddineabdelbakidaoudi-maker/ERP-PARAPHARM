import os

filepath = "ui/pages/fiscal_pages.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

injection = """            from app.config import config
            co = {
                "name": config.company_name,
                "address": config.company_address,
                "nif": config.company_nif,
                "nis": config.company_nis,
                "rc": config.company_rc,
                "ai": config.company_ai,
            }
            """

# Replace 1: Etat 104
content = content.replace(
    "FiscalPDFExporter.export_etat_104_pdf(pdf_path, period_str, data)",
    injection + "FiscalPDFExporter.export_etat_104_pdf(pdf_path, period_str, data, company_info=co)"
)

# Replace 2: Annexe 5
content = content.replace(
    "FiscalPDFExporter.export_annexe_5_pdf(pdf_path, period_str, data)",
    injection + "FiscalPDFExporter.export_annexe_5_pdf(pdf_path, period_str, data, company_info=co)"
)

# Replace 3: G50
content = content.replace(
    "FiscalPDFExporter.export_g50_pdf(pdf_path, period_str, self.g50_data)",
    injection + "FiscalPDFExporter.export_g50_pdf(pdf_path, period_str, self.g50_data, company_info=co)"
)

# Replace 4: G12
content = content.replace(
    "FiscalPDFExporter.export_g12_pdf(pdf_path, str(self.year_spin.value()), self.g12_data)",
    injection + "FiscalPDFExporter.export_g12_pdf(pdf_path, str(self.year_spin.value()), self.g12_data, company_info=co)"
)

# Replace 5: G12 Complementaire
content = content.replace(
    "FiscalPDFExporter.export_g12_pdf(pdf_path, str(self.year_spin.value()), self.g12_data, is_comp=True)",
    injection + "FiscalPDFExporter.export_g12_pdf(pdf_path, str(self.year_spin.value()), self.g12_data, is_comp=True, company_info=co)"
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patch applied to UI PDF Exports.")
