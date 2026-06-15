from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Comptes Bancaires Page
Full CRUD for BankAccount: create, edit, delete, search, filter, export.
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDialog, QFormLayout, QDoubleSpinBox,
    QTextEdit, QFrame, QFileDialog
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.bank import BankAccount
from app.constants import BANK_ACCOUNT_PREFIX


class BankAccountDialog(QDialog):
    """Dialog to create or edit a bank account."""

    def __init__(self, db_session, user, account=None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.user = user
        self.account = account
        self.setWindowTitle("Modifier le Compte" if account else "Nouveau Compte Bancaire")
        self.setMinimumWidth(480)
        self._setup_ui()
        if account:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex: Compte Courant Principal")
        form.addRow("Nom du Compte *", self.name_input)

        self.bank_input = QLineEdit()
        self.bank_input.setPlaceholderText("Ex: CPA, BNA, BEA, Société Générale...")
        form.addRow("Banque *", self.bank_input)

        self.number_input = QLineEdit()
        self.number_input.setPlaceholderText("N° RIB / Compte")
        form.addRow("N° Compte / RIB", self.number_input)

        self.iban_input = QLineEdit()
        self.iban_input.setPlaceholderText("DZ...")
        form.addRow("IBAN", self.iban_input)

        self.swift_input = QLineEdit()
        form.addRow("SWIFT / BIC", self.swift_input)

        self.agency_input = QLineEdit()
        self.agency_input.setPlaceholderText("Agence bancaire")
        form.addRow("Agence", self.agency_input)

        self.type_combo = SearchableComboBox()
        self.type_combo.addItems(["COURANT", "EPARGNE", "DEVISE"])
        form.addRow("Type de Compte", self.type_combo)

        self.balance_spin = QDoubleSpinBox()
        self.balance_spin.setMaximum(999999999.99)
        self.balance_spin.setDecimals(2)
        self.balance_spin.setSuffix(" DA")
        form.addRow("Solde d'Ouverture", self.balance_spin)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        form.addRow("Notes", self.notes_input)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _load_data(self):
        self.name_input.setText(self.account.account_name)
        self.bank_input.setText(self.account.bank_name)
        self.number_input.setText(self.account.account_number or "")
        self.iban_input.setText(self.account.iban or "")
        self.swift_input.setText(self.account.swift_bic or "")
        self.agency_input.setText(self.account.agency or "")
        idx = self.type_combo.findText(self.account.account_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        self.balance_spin.setValue(self.account.current_balance)
        self.notes_input.setPlainText(self.account.notes or "")

    def _on_save(self):
        name = self.name_input.text().strip()
        bank = self.bank_input.text().strip()
        if not name or not bank:
            QMessageBox.warning(self, "Erreur", "Le nom du compte et de la banque sont obligatoires.")
            return

        if self.account:
            self.account.account_name = name
            self.account.bank_name = bank
            self.account.account_number = self.number_input.text().strip() or None
            self.account.iban = self.iban_input.text().strip() or None
            self.account.swift_bic = self.swift_input.text().strip() or None
            self.account.agency = self.agency_input.text().strip() or None
            self.account.account_type = self.type_combo.currentText()
            self.account.current_balance = self.balance_spin.value()
            self.account.notes = self.notes_input.toPlainText().strip() or None
        else:
            # Generate unique code
            count = self.db_session.query(BankAccount).count()
            code = f"{BANK_ACCOUNT_PREFIX}-{count + 1:05d}"

            new_account = BankAccount(
                code=code,
                account_name=name,
                bank_name=bank,
                account_number=self.number_input.text().strip() or None,
                iban=self.iban_input.text().strip() or None,
                swift_bic=self.swift_input.text().strip() or None,
                agency=self.agency_input.text().strip() or None,
                account_type=self.type_combo.currentText(),
                opening_balance=self.balance_spin.value(),
                current_balance=self.balance_spin.value(),
                notes=self.notes_input.toPlainText().strip() or None,
                is_active=1
            )
            self.db_session.add(new_account)

        self.db_session.commit()
        self.accept()


class ComptesBancairesPage(QWidget):
    """Full CRUD page for managing bank accounts."""

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher un compte bancaire...")
        self.search_input.setMinimumWidth(280)
        self.search_input.textChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.search_input)

        self.type_filter = SearchableComboBox()
        self.type_filter.addItems(["Tous", "COURANT", "EPARGNE", "DEVISE"])
        self.type_filter.setMinimumWidth(130)
        self.type_filter.currentTextChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.type_filter)

        toolbar.addStretch()

        add_btn = QPushButton("➕ Nouveau Compte")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)

        export_btn = QPushButton("📊 Exporter CSV")
        export_btn.setProperty("variant", "export")
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        # Table
        cols = ["Code", "Nom du Compte", "Banque", "N° Compte", "Type", "Solde Actuel", "Agence", "Actions"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 200)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

        # Bottom bar
        bottom = QHBoxLayout()
        self.row_count_label = QLabel("0 comptes")
        self.row_count_label.setStyleSheet("color: #757575; font-size: 12px;")
        bottom.addWidget(self.row_count_label)
        bottom.addStretch()

        self.total_label = QLabel("Solde Total: 0.00 DA")
        self.total_label.setStyleSheet("color: #1B5E20; font-size: 13px; font-weight: 700;")
        bottom.addWidget(self.total_label)
        layout.addLayout(bottom)

    def refresh_data(self):
        self.table.setRowCount(0)
        query = self.db_session.query(BankAccount).filter(BankAccount.is_deleted == 0)

        search = self.search_input.text().strip().lower()
        type_filter = self.type_filter.currentText()

        if type_filter != "Tous":
            query = query.filter(BankAccount.account_type == type_filter)

        accounts = query.order_by(BankAccount.created_at.desc()).all()

        if search:
            accounts = [a for a in accounts if search in a.account_name.lower()
                        or search in a.bank_name.lower()
                        or search in (a.code or "").lower()]

        total_balance = 0.0
        for acct in accounts:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(acct.code))
            self.table.setItem(row, 1, QTableWidgetItem(acct.account_name))
            self.table.setItem(row, 2, QTableWidgetItem(acct.bank_name))
            self.table.setItem(row, 3, QTableWidgetItem(acct.account_number or "—"))
            self.table.setItem(row, 4, QTableWidgetItem(acct.account_type))

            balance_item = QTableWidgetItem(f"{acct.current_balance:,.2f} DA")
            balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if acct.current_balance < 0:
                balance_item.setForeground(Qt.red)
            else:
                balance_item.setForeground(Qt.darkGreen)
            self.table.setItem(row, 5, balance_item)
            self.table.setItem(row, 6, QTableWidgetItem(acct.agency or "—"))

            total_balance += acct.current_balance

            # Action buttons
            action_w = QWidget()
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 2, 4, 2)
            action_l.setSpacing(4)

            edit_btn = QPushButton("✏️ Modifier")
            edit_btn.setProperty("variant", "icon-edit")
            edit_btn.clicked.connect(lambda _, a=acct: self._on_edit(a))
            action_l.addWidget(edit_btn)

            del_btn = QPushButton("🗑️ Supprimer")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda _, a=acct: self._on_delete(a))
            action_l.addWidget(del_btn)

            self.table.setCellWidget(row, 7, action_w)

        self.row_count_label.setText(f"{len(accounts)} comptes")
        self.total_label.setText(f"Solde Total: {total_balance:,.2f} DA")

    def _on_add(self):
        dlg = BankAccountDialog(self.db_session, self.user, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _on_edit(self, account):
        dlg = BankAccountDialog(self.db_session, self.user, account=account, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _on_delete(self, account):
        reply = QMessageBox.question(
            self, "Supprimer", f"Supprimer le compte {account.account_name} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            account.soft_delete()
            self.db_session.commit()
            self.refresh_data()

    def _export_csv(self):
        import csv
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Aucune donnée à exporter.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter CSV",
            f"Comptes_Bancaires_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        if not file_path:
            return
        try:
            cols = ["Code", "Nom du Compte", "Banque", "N° Compte", "Type", "Solde Actuel", "Agence"]
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(cols)
                for r in range(self.table.rowCount()):
                    row_vals = [self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(7)]
                    writer.writerow(row_vals)
            QMessageBox.information(self, "Succès", f"Export CSV réussi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
