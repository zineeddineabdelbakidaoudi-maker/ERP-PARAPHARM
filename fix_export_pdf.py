import re

with open('ui/pages/fiscal_pages.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_export_method = """    def export_pdf(self):
        from app.utils.pdf_exporter import PDFExporter
        import os, tempfile
        from PySide6.QtWidgets import QMessageBox
        
        headers = []
        for j in range(self.table.columnCount()):
            headers.append(self.table.horizontalHeaderItem(j).text())
            
        data = []
        for i in range(self.table.rowCount()):
            row = []
            for j in range(self.table.columnCount()):
                item = self.table.item(i, j)
                row.append(item.text() if item else "")
            data.append(row)
            
        pdf_path = os.path.join(tempfile.gettempdir(), f"etat_104_{self.month_combo.currentText()}_{self.year_spin.value()}.pdf")
        
        try:
            PDFExporter.export_table_to_pdf(
                file_path=pdf_path,
                title=f"État 104 — Registre des Ventes — Période: {self.month_combo.currentText()}/{self.year_spin.value()}",
                headers=headers,
                data=data,
                filters="",
                is_landscape=True
            )
            import win32api
            win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'impression: {str(e)}")"""

text = re.sub(r'    def export_pdf\(self\):\n\s+QMessageBox\.information\(self, "Export", ".*?"\)', new_export_method, text)

# Also fix the `` characters globally because I screwed them up!
replacements = {
    "tat": "État",
    "prt": "prêt",
    "implmenter": "implémenter",
    "Y": "📄", # Exporter PDF
    "": "é", # Catch-all for remaining bad characters
}
for old, new in replacements.items():
    text = text.replace(old, new)

with open('ui/pages/fiscal_pages.py', 'w', encoding='utf-8') as f:
    f.write(text)
