import re

# Fix debts_page.py
with open('ui/pages/debts_page.py', 'r', encoding='utf-8') as f:
    text = f.read()

if 'self.btn_imprimer.clicked.connect' not in text:
    text = text.replace("self.btn_imprimer.setStyleSheet('background-color: #2196F3; color: white;')\n", "self.btn_imprimer.setStyleSheet('background-color: #2196F3; color: white;')\n    self.btn_imprimer.clicked.connect(self._on_print)\n")
    
    print_method = """
    def _on_print(self):
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
            
        pdf_path = os.path.join(tempfile.gettempdir(), "etat_dettes_fournisseurs.pdf")
        
        try:
            PDFExporter.export_table_to_pdf(
                file_path=pdf_path,
                title="ETAT DES DETTES FOURNISSEURS",
                headers=headers,
                data=data,
                filters="Toutes les dettes" if self.rad_tous.isChecked() else "Par période",
                is_landscape=True
            )
            import win32api
            win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'impression: {str(e)}")
"""
    # Insert at the end of the class
    # Actually, we can just append it if there's no trailing methods that would break
    # Find last def and append after it
    text += print_method

with open('ui/pages/debts_page.py', 'w', encoding='utf-8') as f:
    f.write(text)

# Fix client_fiche_dialog.py
with open('ui/dialogs/client_fiche_dialog.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Hide annexe button
text = text.replace("self.btn_annexe.clicked.connect(self._not_implemented)", "self.btn_annexe.hide()")

with open('ui/dialogs/client_fiche_dialog.py', 'w', encoding='utf-8') as f:
    f.write(text)
