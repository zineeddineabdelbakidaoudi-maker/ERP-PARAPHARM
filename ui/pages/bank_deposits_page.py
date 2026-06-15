from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Versements Bancaires Page (Bank Deposits)
Full CRUD for credit deposits into bank accounts.
Keyboard shortcut: Ctrl+F6
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDialog, QFormLayout, QDoubleSpinBox,
    QTextEdit, QDateEdit, QFileDialog
)
from PySide6.QtCore import Qt, QDate
from app.core.database import get_session
from app.models.bank import BankAccount, BankDeposit
from app.constants import BANK_DEPOSIT_PREFIX


class BankDepositDialog(QDialog):
    """Dialog to create or edit a bank deposit."""

    def __init__(self, db_session, user, deposit=None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.user = user
        self.deposit = deposit
        self.setWindowTitle("Modifier le Versement" if deposit else "Nouveau Versement Bancaire")
        self.setMinimumWidth(480)
        self._setup_ui()
        if deposit:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.account_combo = SearchableComboBox()
        accounts = self.db_session.query(BankAccount).filter(
            BankAccount.is_deleted == 0, BankAccount.is_active == 1
        ).all()
        for acct in accounts:
            self.account_combo.addItem(f"{acct.account_name} ({acct.bank_name})", acct.id)
        form.addRow("Compte Bancaire *", self.account_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Date du Versement *", self.date_edit)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setMaximum(999999999.99)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSuffix(" DA")
        form.addRow("Montant *", self.amount_spin)

        self.method_combo = SearchableComboBox()
        self.method_combo.addItems(["ESPECES", "CHEQUE", "VIREMENT"])
        form.addRow("Mode de Paiement", self.method_combo)

        self.cheque_input = QLineEdit()
        self.cheque_input.setPlaceholderText("N° du chèque (si applicable)")
        form.addRow("N° Chèque", self.cheque_input)

        self.depositor_input = QLineEdit()
        self.depositor_input.setPlaceholderText("Nom du déposant")
        form.addRow("Déposant", self.depositor_input)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Description / Motif du versement")
        form.addRow("Description", self.desc_input)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(50)
        form.addRow("Notes", self.notes_input)

        layout.addLayout(form)

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
        idx = self.account_combo.findData(self.deposit.account_id)
        if idx >= 0:
            self.account_combo.setCurrentIndex(idx)
        if self.deposit.deposit_date:
            d = QDate.fromString(self.deposit.deposit_date, "yyyy-MM-dd")
            self.date_edit.setDate(d)
        self.amount_spin.setValue(self.deposit.amount)
        midx = self.method_combo.findText(self.deposit.payment_method or "ESPECES")
        if midx >= 0:
            self.method_combo.setCurrentIndex(midx)
        self.cheque_input.setText(self.deposit.cheque_number or "")
        self.depositor_input.setText(self.deposit.depositor_name or "")
        self.desc_input.setText(self.deposit.description or "")
        self.notes_input.setPlainText(self.deposit.notes or "")

    def _on_save(self):
        account_id = self.account_combo.currentData()
        amount = self.amount_spin.value()
        if not account_id or amount <= 0:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un compte et saisir un montant valide.")
            return

        date_str = self.date_edit.date().toString("yyyy-MM-dd")

        if self.deposit:
            # Reverse previous amount from balance, apply new
            old_acct = self.db_session.query(BankAccount).get(self.deposit.account_id)
            if old_acct:
                old_acct.current_balance -= self.deposit.amount

            self.deposit.account_id = account_id
            self.deposit.deposit_date = date_str
            self.deposit.amount = amount
            self.deposit.payment_method = self.method_combo.currentText()
            self.deposit.cheque_number = self.cheque_input.text().strip() or None
            self.deposit.depositor_name = self.depositor_input.text().strip() or None
            self.deposit.description = self.desc_input.text().strip() or None
            self.deposit.notes = self.notes_input.toPlainText().strip() or None

            # Apply new amount to new account
            new_acct = self.db_session.query(BankAccount).get(account_id)
            if new_acct:
                new_acct.current_balance += amount
        else:
            count = self.db_session.query(BankDeposit).count()
            ref = f"{BANK_DEPOSIT_PREFIX}-{datetime.now().strftime('%Y%m%d')}-{count + 1:04d}"

            dep = BankDeposit(
                reference=ref,
                account_id=account_id,
                deposit_date=date_str,
                amount=amount,
                payment_method=self.method_combo.currentText(),
                cheque_number=self.cheque_input.text().strip() or None,
                depositor_name=self.depositor_input.text().strip() or None,
                description=self.desc_input.text().strip() or None,
                status="COMPLETED",
                recorded_by=self.user.id,
                notes=self.notes_input.toPlainText().strip() or None
            )
            self.db_session.add(dep)

            # Update account balance
            acct = self.db_session.query(BankAccount).get(account_id)
            if acct:
                acct.current_balance += amount

        self.db_session.commit()
        self.accept()


class VersementsBancairesPage(QWidget):
    """Full CRUD page for bank deposits (versements)."""

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
        self.search_input.setPlaceholderText("🔍 Rechercher versement (réf, déposant)...")
        self.search_input.setMinimumWidth(280)
        self.search_input.textChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.search_input)

        self.account_filter = SearchableComboBox()
        self.account_filter.addItem("Tous les comptes", None)
        accounts = self.db_session.query(BankAccount).filter(BankAccount.is_deleted == 0).all()
        for acct in accounts:
            self.account_filter.addItem(f"{acct.account_name}", acct.id)
        self.account_filter.currentIndexChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.account_filter)

        # Date range
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        toolbar.addWidget(QLabel("Du:"))
        toolbar.addWidget(self.date_from)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        toolbar.addWidget(QLabel("Au:"))
        toolbar.addWidget(self.date_to)

        self.date_from.dateChanged.connect(lambda _: self.refresh_data())
        self.date_to.dateChanged.connect(lambda _: self.refresh_data())

        toolbar.addStretch()

        add_btn = QPushButton("➕ Nouveau Versement")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)

        export_btn = QPushButton("📊 Exporter CSV")
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        # Table
        cols = ["Réf.", "Date", "Compte", "Montant", "Mode", "Déposant", "Description", "Statut", "Actions"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        self.table.setColumnWidth(8, 200)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

        # Bottom
        bottom = QHBoxLayout()
        self.row_count_label = QLabel("0 versements")
        self.row_count_label.setStyleSheet("color: #757575; font-size: 12px;")
        bottom.addWidget(self.row_count_label)
        bottom.addStretch()
        self.total_label = QLabel("Total: 0.00 DA")
        self.total_label.setStyleSheet("color: #1B5E20; font-size: 13px; font-weight: 700;")
        bottom.addWidget(self.total_label)
        layout.addLayout(bottom)

    def refresh_data(self):
        self.table.setRowCount(0)
        query = self.db_session.query(BankDeposit).filter(BankDeposit.is_deleted == 0)

        acct_id = self.account_filter.currentData()
        if acct_id:
            query = query.filter(BankDeposit.account_id == acct_id)

        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        query = query.filter(BankDeposit.deposit_date >= date_from, BankDeposit.deposit_date <= date_to)

        deposits = query.order_by(BankDeposit.deposit_date.desc()).all()

        search = self.search_input.text().strip().lower()
        if search:
            deposits = [d for d in deposits if search in d.reference.lower()
                        or search in (d.depositor_name or "").lower()
                        or search in (d.description or "").lower()]

        total = 0.0
        for dep in deposits:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(dep.reference))
            self.table.setItem(row, 1, QTableWidgetItem(dep.deposit_date))
            acct_name = dep.account.account_name if dep.account else "—"
            self.table.setItem(row, 2, QTableWidgetItem(acct_name))

            amt = QTableWidgetItem(f"{dep.amount:,.2f} DA")
            amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amt.setForeground(Qt.darkGreen)
            self.table.setItem(row, 3, amt)

            self.table.setItem(row, 4, QTableWidgetItem(dep.payment_method or "—"))
            self.table.setItem(row, 5, QTableWidgetItem(dep.depositor_name or "—"))
            self.table.setItem(row, 6, QTableWidgetItem(dep.description or "—"))
            self.table.setItem(row, 7, QTableWidgetItem(dep.status))

            total += dep.amount

            action_w = QWidget()
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 2, 4, 2)
            action_l.setSpacing(4)
            edit_btn = QPushButton("✏️ Modifier")
            edit_btn.setProperty("variant", "icon-edit")
            edit_btn.clicked.connect(lambda _, d=dep: self._on_edit(d))
            action_l.addWidget(edit_btn)
            del_btn = QPushButton("🗑️ Supprimer")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda _, d=dep: self._on_delete(d))
            action_l.addWidget(del_btn)
            self.table.setCellWidget(row, 8, action_w)

        self.row_count_label.setText(f"{len(deposits)} versements")
        self.total_label.setText(f"Total: {total:,.2f} DA")

    def _on_add(self):
        dlg = BankDepositDialog(self.db_session, self.user, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _on_edit(self, deposit):
        dlg = BankDepositDialog(self.db_session, self.user, deposit=deposit, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _on_delete(self, deposit):
        reply = QMessageBox.question(
            self, "Supprimer", f"Supprimer le versement {deposit.reference} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Reverse balance
            acct = self.db_session.query(BankAccount).get(deposit.account_id)
            if acct:
                acct.current_balance -= deposit.amount
            deposit.soft_delete()
            self.db_session.commit()
            self.refresh_data()

    def _export_csv(self):
        import csv
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Aucune donnée à exporter.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter CSV",
            f"Versements_Bancaires_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        if not file_path:
            return
        try:
            cols = ["Réf.", "Date", "Compte", "Montant", "Mode", "Déposant", "Description", "Statut"]
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(cols)
                for r in range(self.table.rowCount()):
                    row_vals = [self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(8)]
                    writer.writerow(row_vals)
            QMessageBox.information(self, "Succès", f"Export CSV réussi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
