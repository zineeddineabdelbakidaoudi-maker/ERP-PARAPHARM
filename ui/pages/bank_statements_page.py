from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Relevés de Comptes Page (Bank Account Statements)
Displays a combined view of deposits, withdrawals, and transfers for a selected account.
Read-only statement with date filtering, running balance, and CSV/PDF export.
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDateEdit, QFileDialog, QFrame
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor
from app.core.database import get_session
from app.models.bank import BankAccount, BankDeposit, BankWithdrawal, BankTransfer


class RelevesComptesPage(QWidget):
    """Bank account statement page — combined view of all operations."""

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

        # ── Account Selector & Date Range ─────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        toolbar.addWidget(QLabel("Compte:"))
        self.account_combo = SearchableComboBox()
        self.account_combo.setMinimumWidth(250)
        self.account_combo.addItem("— Tous les comptes —", None)
        accounts = self.db_session.query(BankAccount).filter(BankAccount.is_deleted == 0).all()
        for acct in accounts:
            self.account_combo.addItem(
                f"{acct.account_name} ({acct.bank_name}) — {acct.current_balance:,.2f} DA", acct.id
            )
        self.account_combo.currentIndexChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.account_combo)

        toolbar.addWidget(QLabel("Du:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-3))
        self.date_from.dateChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.date_from)

        toolbar.addWidget(QLabel("Au:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.date_to)

        toolbar.addStretch()

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)

        export_csv_btn = QPushButton("📊 CSV")
        export_csv_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_csv_btn)

        export_pdf_btn = QPushButton("📄 PDF")
        export_pdf_btn.clicked.connect(self._export_pdf)
        toolbar.addWidget(export_pdf_btn)

        layout.addLayout(toolbar)

        # ── Account Summary Card ─────────────────────────
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #E8F5E9, stop:1 #C8E6C9);
                border-radius: 8px; padding: 12px;
            }
        """)
        summary_layout = QHBoxLayout(self.summary_frame)

        self.lbl_account = QLabel("Sélectionnez un compte")
        self.lbl_account.setStyleSheet("font-size: 14px; font-weight: 700; color: #1B5E20;")
        summary_layout.addWidget(self.lbl_account)
        summary_layout.addStretch()

        self.lbl_deposits = QLabel("Versements: 0.00 DA")
        self.lbl_deposits.setStyleSheet("font-size: 12px; color: #2E7D32; font-weight: 600;")
        summary_layout.addWidget(self.lbl_deposits)

        self.lbl_withdrawals = QLabel("Retraits: 0.00 DA")
        self.lbl_withdrawals.setStyleSheet("font-size: 12px; color: #C62828; font-weight: 600;")
        summary_layout.addWidget(self.lbl_withdrawals)

        self.lbl_balance = QLabel("Solde: 0.00 DA")
        self.lbl_balance.setStyleSheet("font-size: 14px; color: #1B5E20; font-weight: 700;")
        summary_layout.addWidget(self.lbl_balance)

        layout.addWidget(self.summary_frame)

        # ── Statement Table ──────────────────────────────
        cols = ["Date", "Réf.", "Type", "Description", "Débit", "Crédit", "Solde"]
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

        # Bottom
        bottom = QHBoxLayout()
        self.row_count_label = QLabel("0 opérations")
        self.row_count_label.setStyleSheet("color: #757575; font-size: 12px;")
        bottom.addWidget(self.row_count_label)
        bottom.addStretch()
        layout.addLayout(bottom)

    def refresh_data(self):
        self.table.setRowCount(0)

        acct_id = self.account_combo.currentData()
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")

        # Collect all operations into a unified list
        operations = []  # (date, ref, type, description, debit, credit)

        # Deposits
        dep_query = self.db_session.query(BankDeposit).filter(
            BankDeposit.is_deleted == 0,
            BankDeposit.deposit_date >= date_from,
            BankDeposit.deposit_date <= date_to
        )
        if acct_id:
            dep_query = dep_query.filter(BankDeposit.account_id == acct_id)
        for dep in dep_query.all():
            operations.append((
                dep.deposit_date, dep.reference, "VERSEMENT",
                dep.description or dep.depositor_name or "Versement bancaire",
                0.0, dep.amount
            ))

        # Withdrawals
        wd_query = self.db_session.query(BankWithdrawal).filter(
            BankWithdrawal.is_deleted == 0,
            BankWithdrawal.withdrawal_date >= date_from,
            BankWithdrawal.withdrawal_date <= date_to
        )
        if acct_id:
            wd_query = wd_query.filter(BankWithdrawal.account_id == acct_id)
        for wd in wd_query.all():
            operations.append((
                wd.withdrawal_date, wd.reference, "RETRAIT",
                wd.description or wd.beneficiary_name or "Retrait bancaire",
                wd.amount, 0.0
            ))

        # Transfers
        tr_query = self.db_session.query(BankTransfer).filter(
            BankTransfer.is_deleted == 0,
            BankTransfer.transfer_date >= date_from,
            BankTransfer.transfer_date <= date_to
        )
        if acct_id:
            tr_query = tr_query.filter(
                (BankTransfer.source_account_id == acct_id) |
                (BankTransfer.dest_account_id == acct_id)
            )
        for tr in tr_query.all():
            if acct_id:
                if tr.source_account_id == acct_id:
                    operations.append((
                        tr.transfer_date, tr.reference, "TRANSFERT SORTANT",
                        f"Vers {tr.dest_account.account_name}" if tr.dest_account else "Transfert",
                        tr.amount + (tr.fees or 0), 0.0
                    ))
                else:
                    operations.append((
                        tr.transfer_date, tr.reference, "TRANSFERT ENTRANT",
                        f"De {tr.source_account.account_name}" if tr.source_account else "Transfert",
                        0.0, tr.amount
                    ))
            else:
                # Show both sides when showing all accounts
                operations.append((
                    tr.transfer_date, tr.reference, "TRANSFERT",
                    tr.description or "Transfert inter-comptes",
                    tr.amount, tr.amount
                ))

        # Sort by date
        operations.sort(key=lambda x: x[0])

        # Calculate running balance
        total_deposits = 0.0
        total_withdrawals = 0.0
        running_balance = 0.0

        # If single account, start from opening balance
        if acct_id:
            acct = self.db_session.query(BankAccount).get(acct_id)
            if acct:
                self.lbl_account.setText(f"📊 {acct.account_name} — {acct.bank_name}")
                # For running balance, we start from opening and compute through filtered ops
                running_balance = acct.opening_balance

        for date, ref, op_type, desc, debit, credit in operations:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(date))
            self.table.setItem(row, 1, QTableWidgetItem(ref))
            self.table.setItem(row, 2, QTableWidgetItem(op_type))
            self.table.setItem(row, 3, QTableWidgetItem(desc))

            if debit > 0:
                debit_item = QTableWidgetItem(f"-{debit:,.2f}")
                debit_item.setForeground(QColor("#C62828"))
                debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 4, debit_item)
                total_withdrawals += debit
            else:
                self.table.setItem(row, 4, QTableWidgetItem(""))

            if credit > 0:
                credit_item = QTableWidgetItem(f"+{credit:,.2f}")
                credit_item.setForeground(QColor("#2E7D32"))
                credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 5, credit_item)
                total_deposits += credit
            else:
                self.table.setItem(row, 5, QTableWidgetItem(""))

            running_balance += credit - debit
            bal_item = QTableWidgetItem(f"{running_balance:,.2f}")
            bal_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            bal_item.setForeground(QColor("#1B5E20") if running_balance >= 0 else QColor("#C62828"))
            self.table.setItem(row, 6, bal_item)

        # Update summary
        if not acct_id:
            self.lbl_account.setText("📊 Tous les comptes")
        self.lbl_deposits.setText(f"Versements: +{total_deposits:,.2f} DA")
        self.lbl_withdrawals.setText(f"Retraits: -{total_withdrawals:,.2f} DA")
        self.lbl_balance.setText(f"Solde: {running_balance:,.2f} DA")

        self.row_count_label.setText(f"{len(operations)} opérations")

    def _export_csv(self):
        import csv
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Aucune donnée à exporter.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter CSV",
            f"Releve_Bancaire_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        if not file_path:
            return
        try:
            cols = ["Date", "Réf.", "Type", "Description", "Débit", "Crédit", "Solde"]
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(cols)
                for r in range(self.table.rowCount()):
                    row_vals = [self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(7)]
                    writer.writerow(row_vals)
            QMessageBox.information(self, "Succès", f"Export CSV réussi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _export_pdf(self):
        """Export the statement as a PDF using the existing PDFExporter."""
        try:
            from app.utils.pdf_exporter import PDFExporter
        except ImportError:
            QMessageBox.warning(self, "PDF", "Le module PDFExporter n'est pas disponible.")
            return

        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Aucune donnée à exporter.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter PDF",
            f"Releve_Bancaire_{datetime.now().strftime('%Y%m%d')}.pdf",
            "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        try:
            headers = ["Date", "Réf.", "Type", "Description", "Débit", "Crédit", "Solde"]
            rows = []
            for r in range(self.table.rowCount()):
                row = [self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(7)]
                rows.append(row)

            acct_name = self.account_combo.currentText()
            title = f"Relevé de Compte — {acct_name}"
            subtitle = f"Période: {self.date_from.date().toString('dd/MM/yyyy')} au {self.date_to.date().toString('dd/MM/yyyy')}"

            PDFExporter.export_table_to_pdf(
                file_path, title, subtitle, headers, rows
            )
            QMessageBox.information(self, "Succès", f"PDF exporté:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", str(e))
