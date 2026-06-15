from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Transferts Inter-Comptes Page (Inter-Account Transfers)
Full CRUD for transfers between two bank accounts.
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
from app.models.bank import BankAccount, BankTransfer
from app.constants import BANK_TRANSFER_PREFIX


class BankTransferDialog(QDialog):
    def __init__(self, db_session, user, transfer=None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.user = user
        self.transfer = transfer
        self.setWindowTitle("Modifier le Transfert" if transfer else "Nouveau Transfert Inter-Comptes")
        self.setMinimumWidth(480)
        self._setup_ui()
        if transfer:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        accounts = self.db_session.query(BankAccount).filter(
            BankAccount.is_deleted == 0, BankAccount.is_active == 1
        ).all()

        self.source_combo = SearchableComboBox()
        self.dest_combo = SearchableComboBox()
        for acct in accounts:
            label = f"{acct.account_name} ({acct.bank_name}) — {acct.current_balance:,.2f} DA"
            self.source_combo.addItem(label, acct.id)
            self.dest_combo.addItem(label, acct.id)
        form.addRow("Compte Source *", self.source_combo)
        form.addRow("Compte Destination *", self.dest_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Date du Transfert *", self.date_edit)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setMaximum(999999999.99)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSuffix(" DA")
        form.addRow("Montant *", self.amount_spin)

        self.fees_spin = QDoubleSpinBox()
        self.fees_spin.setMaximum(999999.99)
        self.fees_spin.setDecimals(2)
        self.fees_spin.setSuffix(" DA")
        form.addRow("Frais de Transfert", self.fees_spin)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Description / Motif du transfert")
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
        idx_s = self.source_combo.findData(self.transfer.source_account_id)
        idx_d = self.dest_combo.findData(self.transfer.dest_account_id)
        if idx_s >= 0:
            self.source_combo.setCurrentIndex(idx_s)
        if idx_d >= 0:
            self.dest_combo.setCurrentIndex(idx_d)
        if self.transfer.transfer_date:
            d = QDate.fromString(self.transfer.transfer_date, "yyyy-MM-dd")
            self.date_edit.setDate(d)
        self.amount_spin.setValue(self.transfer.amount)
        self.fees_spin.setValue(self.transfer.fees or 0.0)
        self.desc_input.setText(self.transfer.description or "")
        self.notes_input.setPlainText(self.transfer.notes or "")

    def _on_save(self):
        src_id = self.source_combo.currentData()
        dst_id = self.dest_combo.currentData()
        amount = self.amount_spin.value()

        if not src_id or not dst_id:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner les deux comptes.")
            return
        if src_id == dst_id:
            QMessageBox.warning(self, "Erreur", "Le compte source et destination doivent être différents.")
            return
        if amount <= 0:
            QMessageBox.warning(self, "Erreur", "Le montant doit être supérieur à 0.")
            return

        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        fees = self.fees_spin.value()

        if self.transfer:
            # Reverse old balances
            old_src = self.db_session.query(BankAccount).get(self.transfer.source_account_id)
            old_dst = self.db_session.query(BankAccount).get(self.transfer.dest_account_id)
            if old_src:
                old_src.current_balance += self.transfer.amount + (self.transfer.fees or 0)
            if old_dst:
                old_dst.current_balance -= self.transfer.amount

            self.transfer.source_account_id = src_id
            self.transfer.dest_account_id = dst_id
            self.transfer.transfer_date = date_str
            self.transfer.amount = amount
            self.transfer.fees = fees
            self.transfer.description = self.desc_input.text().strip() or None
            self.transfer.notes = self.notes_input.toPlainText().strip() or None

            # Apply new balances
            new_src = self.db_session.query(BankAccount).get(src_id)
            new_dst = self.db_session.query(BankAccount).get(dst_id)
            if new_src:
                new_src.current_balance -= (amount + fees)
            if new_dst:
                new_dst.current_balance += amount
        else:
            count = self.db_session.query(BankTransfer).count()
            ref = f"{BANK_TRANSFER_PREFIX}-{datetime.now().strftime('%Y%m%d')}-{count + 1:04d}"

            tr = BankTransfer(
                reference=ref,
                source_account_id=src_id,
                dest_account_id=dst_id,
                transfer_date=date_str,
                amount=amount,
                fees=fees,
                description=self.desc_input.text().strip() or None,
                status="COMPLETED",
                recorded_by=self.user.id,
                notes=self.notes_input.toPlainText().strip() or None
            )
            self.db_session.add(tr)

            src_acct = self.db_session.query(BankAccount).get(src_id)
            dst_acct = self.db_session.query(BankAccount).get(dst_id)
            if src_acct:
                src_acct.current_balance -= (amount + fees)
            if dst_acct:
                dst_acct.current_balance += amount

        self.db_session.commit()
        self.accept()


class TransfertInterComptesPage(QWidget):
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

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher transfert (réf, description)...")
        self.search_input.setMinimumWidth(280)
        self.search_input.textChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.search_input)

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

        add_btn = QPushButton("➕ Nouveau Transfert")
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

        cols = ["Réf.", "Date", "Compte Source", "Compte Dest.", "Montant", "Frais", "Description", "Statut", "Actions"]
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

        bottom = QHBoxLayout()
        self.row_count_label = QLabel("0 transferts")
        self.row_count_label.setStyleSheet("color: #757575; font-size: 12px;")
        bottom.addWidget(self.row_count_label)
        bottom.addStretch()
        self.total_label = QLabel("Total: 0.00 DA")
        self.total_label.setStyleSheet("color: #1565C0; font-size: 13px; font-weight: 700;")
        bottom.addWidget(self.total_label)
        layout.addLayout(bottom)

    def refresh_data(self):
        self.table.setRowCount(0)
        query = self.db_session.query(BankTransfer).filter(BankTransfer.is_deleted == 0)

        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        query = query.filter(BankTransfer.transfer_date >= date_from, BankTransfer.transfer_date <= date_to)

        transfers = query.order_by(BankTransfer.transfer_date.desc()).all()

        search = self.search_input.text().strip().lower()
        if search:
            transfers = [t for t in transfers if search in t.reference.lower()
                         or search in (t.description or "").lower()]

        total = 0.0
        for tr in transfers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(tr.reference))
            self.table.setItem(row, 1, QTableWidgetItem(tr.transfer_date))
            src_name = tr.source_account.account_name if tr.source_account else "—"
            dst_name = tr.dest_account.account_name if tr.dest_account else "—"
            self.table.setItem(row, 2, QTableWidgetItem(src_name))
            self.table.setItem(row, 3, QTableWidgetItem(dst_name))

            amt = QTableWidgetItem(f"{tr.amount:,.2f} DA")
            amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amt.setForeground(Qt.darkBlue)
            self.table.setItem(row, 4, amt)

            fees = QTableWidgetItem(f"{tr.fees:,.2f} DA" if tr.fees else "0.00 DA")
            fees.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 5, fees)

            self.table.setItem(row, 6, QTableWidgetItem(tr.description or "—"))
            self.table.setItem(row, 7, QTableWidgetItem(tr.status))
            total += tr.amount

            action_w = QWidget()
            action_l = QHBoxLayout(action_w)
            action_l.setContentsMargins(4, 2, 4, 2)
            action_l.setSpacing(4)
            edit_btn = QPushButton("✏️ Modifier")
            edit_btn.setProperty("variant", "icon-edit")
            edit_btn.clicked.connect(lambda _, t=tr: self._on_edit(t))
            action_l.addWidget(edit_btn)
            del_btn = QPushButton("🗑️ Supprimer")
            del_btn.setProperty("variant", "icon-delete")
            del_btn.clicked.connect(lambda _, t=tr: self._on_delete(t))
            action_l.addWidget(del_btn)
            self.table.setCellWidget(row, 8, action_w)

        self.row_count_label.setText(f"{len(transfers)} transferts")
        self.total_label.setText(f"Total: {total:,.2f} DA")

    def _on_add(self):
        dlg = BankTransferDialog(self.db_session, self.user, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _on_edit(self, transfer):
        dlg = BankTransferDialog(self.db_session, self.user, transfer=transfer, parent=self)
        if dlg.exec():
            self.refresh_data()

    def _on_delete(self, transfer):
        reply = QMessageBox.question(
            self, "Supprimer", f"Supprimer le transfert {transfer.reference} ?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            src = self.db_session.query(BankAccount).get(transfer.source_account_id)
            dst = self.db_session.query(BankAccount).get(transfer.dest_account_id)
            if src:
                src.current_balance += transfer.amount + (transfer.fees or 0)
            if dst:
                dst.current_balance -= transfer.amount
            transfer.soft_delete()
            self.db_session.commit()
            self.refresh_data()

    def _export_csv(self):
        import csv
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Aucune donnée à exporter.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter CSV",
            f"Transferts_InterComptes_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        if not file_path:
            return
        try:
            cols = ["Réf.", "Date", "Source", "Destination", "Montant", "Frais", "Description", "Statut"]
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(cols)
                for r in range(self.table.rowCount()):
                    row_vals = [self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(8)]
                    writer.writerow(row_vals)
            QMessageBox.information(self, "Succès", f"Export CSV réussi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
