"""
ParaFarm ERP — Settings Page
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout, QFrame, QComboBox,
    QSpinBox, QDoubleSpinBox, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.base_repository import BaseRepository
from app.models.setting import Setting, PrinterConfig


class SettingsPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.setting_repo = BaseRepository(self.db_session, Setting)
        self.printer_repo = BaseRepository(self.db_session, PrinterConfig)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.tabs = QTabWidget()

        # General Settings Tab
        general_widget = QWidget()
        general_layout = QVBoxLayout(general_widget)

        general_frame = QFrame()
        general_frame.setProperty("class", "card")
        form = QFormLayout(general_frame)
        form.setSpacing(12)

        self.shop_name_input = QLineEdit()
        form.addRow("Nom de la Pharmacie", self.shop_name_input)

        self.shop_address_input = QLineEdit()
        form.addRow("Adresse", self.shop_address_input)

        self.shop_phone_input = QLineEdit()
        form.addRow("Téléphone", self.shop_phone_input)

        self.shop_nif_input = QLineEdit()
        form.addRow("NIF", self.shop_nif_input)

        self.shop_rc_input = QLineEdit()
        form.addRow("Registre de Commerce", self.shop_rc_input)

        self.currency_input = QLineEdit()
        self.currency_input.setText("DA")
        form.addRow("Devise", self.currency_input)

        self.tva_spin = QDoubleSpinBox()
        self.tva_spin.setMaximum(100.0)
        self.tva_spin.setSuffix(" %")
        form.addRow("TVA par Défaut", self.tva_spin)

        general_layout.addWidget(general_frame)

        save_general_btn = QPushButton("Enregistrer les Paramètres")
        save_general_btn.clicked.connect(self._save_general)
        general_layout.addWidget(save_general_btn, alignment=Qt.AlignRight)
        general_layout.addStretch()

        self.tabs.addTab(general_widget, "Général")

        # Printers Tab
        printer_widget = QWidget()
        printer_layout = QVBoxLayout(printer_widget)

        printer_toolbar = QHBoxLayout()
        printer_toolbar.addStretch()
        add_printer_btn = QPushButton("➕ Ajouter Imprimante")
        add_printer_btn.clicked.connect(self._on_add_printer)
        printer_toolbar.addWidget(add_printer_btn)
        printer_layout.addLayout(printer_toolbar)

        self.printer_table = QTableWidget(0, 5)
        self.printer_table.setHorizontalHeaderLabels([
            "Nom", "Type", "Connexion", "Défaut", "Actions"
        ])
        self.printer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.printer_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.printer_table.verticalHeader().setVisible(False)
        self.printer_table.verticalHeader().setDefaultSectionSize(48)
        printer_layout.addWidget(self.printer_table)

        self.tabs.addTab(printer_widget, "Imprimantes")

        layout.addWidget(self.tabs)

    def _load_settings(self):
        """Load settings from the database into the form."""
        settings_map = {}
        res = self.setting_repo.get_all()
        items = res.get("items", []) if isinstance(res, dict) else res
        for s in items:
            settings_map[s.key] = s.value

        self.shop_name_input.setText(settings_map.get("shop_name", ""))
        self.shop_address_input.setText(settings_map.get("shop_address", ""))
        self.shop_phone_input.setText(settings_map.get("shop_phone", ""))
        self.shop_nif_input.setText(settings_map.get("shop_nif", ""))
        self.shop_rc_input.setText(settings_map.get("shop_rc", ""))
        self.currency_input.setText(settings_map.get("currency", "DA"))
        
        try:
            self.tva_spin.setValue(float(settings_map.get("default_tva", "19.0")))
        except ValueError:
            self.tva_spin.setValue(19.0)

        self._load_printers()

    def _save_setting(self, key, value, category="GENERAL"):
        """Upsert a single setting."""
        existing = self.db_session.query(Setting).filter(Setting.key == key).first()
        if existing:
            existing.value = value
        else:
            new_setting = Setting(key=key, value=value, category=category, data_type="STRING")
            self.db_session.add(new_setting)

    def _save_general(self):
        try:
            self._save_setting("shop_name", self.shop_name_input.text().strip())
            self._save_setting("shop_address", self.shop_address_input.text().strip())
            self._save_setting("shop_phone", self.shop_phone_input.text().strip())
            self._save_setting("shop_nif", self.shop_nif_input.text().strip())
            self._save_setting("shop_rc", self.shop_rc_input.text().strip())
            self._save_setting("currency", self.currency_input.text().strip())
            self._save_setting("default_tva", str(self.tva_spin.value()))
            self.db_session.commit()
            QMessageBox.information(self, "Succès", "Paramètres enregistrés.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _load_printers(self):
        self.printer_table.setRowCount(0)
        res = self.printer_repo.get_all()
        printers = res.get("items", []) if isinstance(res, dict) else res

        for p in printers:
            row = self.printer_table.rowCount()
            self.printer_table.insertRow(row)

            self.printer_table.setItem(row, 0, QTableWidgetItem(p.name))
            self.printer_table.setItem(row, 1, QTableWidgetItem(p.printer_type))
            self.printer_table.setItem(row, 2, QTableWidgetItem(p.connection_type))

            defaults = []
            if p.is_default_receipt:
                defaults.append("Ticket")
            if p.is_default_a4:
                defaults.append("A4")
            if p.is_default_label:
                defaults.append("Étiquette")
            self.printer_table.setItem(row, 3, QTableWidgetItem(", ".join(defaults) or "—"))

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 0, 4, 0)
            action_layout.setSpacing(4)

            del_btn = QPushButton("🗑️ Supprimer")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda checked, pr=p: self._on_delete_printer(pr))
            action_layout.addWidget(del_btn)

            self.printer_table.setCellWidget(row, 4, action_widget)

    def _on_add_printer(self):
        from ui.dialogs.printer_dialog import PrinterDialog
        dlg = PrinterDialog(self.db_session, self)
        if dlg.exec():
            self._load_printers()

    def _on_delete_printer(self, printer):
        reply = QMessageBox.question(
            self, "Supprimer", f"Voulez-vous supprimer l'imprimante {printer.name} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.printer_repo.hard_delete(printer.id)
            self.printer_repo.commit()
            self._load_printers()
