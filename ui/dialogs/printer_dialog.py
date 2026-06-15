from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
    QCheckBox, QPushButton, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt
from app.models.setting import PrinterConfig

class PrinterDialog(QDialog):
    def __init__(self, db_session, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.setWindowTitle("Ajouter une imprimante")
        self.setMinimumWidth(450)
        self._setup_ui()
        self._load_system_printers()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex: Xprinter 80mm")
        form.addRow("Nom :", self.name_input)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["THERMAL", "A4", "LABEL"])
        form.addRow("Type :", self.type_combo)
        
        self.conn_combo = QComboBox()
        self.conn_combo.addItems(["SPOOLER", "USB", "NETWORK"])
        form.addRow("Connexion :", self.conn_combo)
        
        # Change to editable combobox
        self.conn_string_combo = QComboBox()
        self.conn_string_combo.setEditable(True)
        self.conn_string_combo.lineEdit().setPlaceholderText("Sélectionner ou taper (IP / Port)")
        form.addRow("Chaîne de connexion :", self.conn_string_combo)
        
        self.chk_receipt = QCheckBox("Imprimante Ticket par défaut")
        self.chk_a4 = QCheckBox("Imprimante A4 par défaut")
        self.chk_label = QCheckBox("Imprimante Étiquette par défaut")
        
        form.addRow("", self.chk_receipt)
        form.addRow("", self.chk_a4)
        form.addRow("", self.chk_label)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Enregistrer")
        btn_save.setStyleSheet("background-color: #2E7D32; color: white;")
        btn_save.clicked.connect(self._on_save)
        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)
        
    def _load_system_printers(self):
        """Fetch all installed printers in Windows and populate the combobox."""
        try:
            import win32print
            printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            self.conn_string_combo.addItems(printers)
        except Exception as e:
            print(f"Failed to fetch system printers: {e}")
            
    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return
            
        printer = PrinterConfig(
            name=name,
            printer_type=self.type_combo.currentText(),
            connection_type=self.conn_combo.currentText(),
            connection_string=self.conn_string_combo.currentText().strip() or name,
            is_default_receipt=1 if self.chk_receipt.isChecked() else 0,
            is_default_a4=1 if self.chk_a4.isChecked() else 0,
            is_default_label=1 if self.chk_label.isChecked() else 0,
        )
        
        try:
            self.db_session.add(printer)
            self.db_session.commit()
            self.accept()
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement: {str(e)}")
