import re

with open('ui/pages/settings_page.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_method = """    def _on_add_printer(self):
        from ui.dialogs.printer_dialog import PrinterDialog
        dlg = PrinterDialog(self.db_session, self)
        if dlg.exec():
            self._load_printers()"""

text = re.sub(r'    def _on_add_printer\(self\):.*?implémenter \(Configuration matérielle\)\."\)', new_method, text, flags=re.DOTALL)

with open('ui/pages/settings_page.py', 'w', encoding='utf-8') as f:
    f.write(text)
