from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from app.core.database import get_session
from app.models.client import Client
from app.models.debt import Debt
import os
from PySide6.QtWidgets import QFileDialog
from app.utils.pdf_exporter import PDFExporter

class EtatCreancePage(QWidget):
    PAGE_TITLE = "État de Créance"
    
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Recherche par Client...")
        self.search_input.textChanged.connect(self.refresh_data)
        toolbar.addWidget(self.search_input)
        
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_from.setCalendarPopup(True)
        self.date_from.dateChanged.connect(self.refresh_data)
        toolbar.addWidget(QLabel("Du:"))
        toolbar.addWidget(self.date_from)
        
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.dateChanged.connect(self.refresh_data)
        toolbar.addWidget(QLabel("Au:"))
        toolbar.addWidget(self.date_to)
        
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)
        
        export_btn = QPushButton("📄 Exporter PDF")
        export_btn.setProperty("variant", "primary")
        export_btn.clicked.connect(self._export_pdf)
        toolbar.addWidget(export_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Code Client", "Nom Client", "Dette Totale (Période)", "Reste à Payer (Global)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Summary
        self.summary_lbl = QLabel("Total des créances : 0.00 DA")
        self.summary_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.summary_lbl)

    def refresh_data(self):
        self.table.setRowCount(0)
        query = self.search_input.text().strip().lower()
        d_from = self.date_from.date().toString("yyyy-MM-dd")
        d_to = self.date_to.date().toString("yyyy-MM-dd")
        
        clients = self.db_session.query(Client).filter_by(is_deleted=0).all()
        
        total_global = 0.0
        
        for c in clients:
            if query and query not in c.name.lower() and query not in c.client_code.lower():
                continue
                
            # Calc debts in period
            debts_period = self.db_session.query(Debt).filter(
                Debt.entity_type == "CLIENT",
                Debt.entity_id == c.id,
                Debt.created_at >= d_from + " 00:00:00",
                Debt.created_at <= d_to + " 23:59:59"
            ).all()
            
            period_amount = sum(d.total_amount for d in debts_period)
            
            # Global remaining
            all_debts = self.db_session.query(Debt).filter(
                Debt.entity_type == "CLIENT", Debt.entity_id == c.id
            ).all()
            global_remaining = sum(d.remaining_amount for d in all_debts)
            
            if period_amount == 0 and global_remaining == 0:
                continue
                
            total_global += global_remaining
                
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(c.code))
            self.table.setItem(row, 1, QTableWidgetItem(c.name))
            self.table.setItem(row, 2, QTableWidgetItem(f"{period_amount:,.2f} DA"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{global_remaining:,.2f} DA"))
            
        self.summary_lbl.setText(f"Total des créances (Global) : {total_global:,.2f} DA")

    def _export_pdf(self):
        d = QFileDialog.getSaveFileName(self, "Enregistrer État des Créances", "Etat_Creance.pdf", "PDF (*.pdf)")
        if not d[0]: return
        
        headers = ["Code Client", "Nom Client", "Dette Totale (Période)", "Reste à Payer (Global)"]
        data = []
        for i in range(self.table.rowCount()):
            data.append([
                self.table.item(i, 0).text(),
                self.table.item(i, 1).text(),
                self.table.item(i, 2).text(),
                self.table.item(i, 3).text()
            ])
            
        period_str = f"Du {self.date_from.date().toString('dd/MM/yyyy')} au {self.date_to.date().toString('dd/MM/yyyy')}"
        title = f"État des Créances Clients\n{period_str}"
        
        try:
            PDFExporter.export_table_to_pdf(d[0], title, headers, data)
            os.startfile(d[0])
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible de générer le PDF:\\n{e}")
