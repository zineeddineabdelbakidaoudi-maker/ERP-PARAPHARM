from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.supplier_invoice import SupplierInvoice
from ui.dialogs.supplier_invoice_dialog import SupplierInvoiceDialog

class FacturesFournisseurPage(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par n° de facture ou fournisseur...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)
        
        toolbar.addStretch()

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(lambda: self.refresh_data(self.search_input.text()))
        toolbar.addWidget(refresh_btn)

        add_btn = QPushButton("➕ Nouvelle Facture Fourn.")
        add_btn.clicked.connect(self._on_new)
        toolbar.addWidget(add_btn)
        
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "N° Facture Fourn.", "Notre Réf.", "Fournisseur", "Date", "Montant HT", "TVA", "TTC", "Statut", "Actions"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        
        # Stats Panel
        stats_layout = QHBoxLayout()
        self.lbl_purchases = QLabel("TOTAL ACHATS (HT): 0.00 DA")
        self.lbl_purchases.setStyleSheet("font-weight: bold; color: #2C3E50; font-size: 14px;")
        stats_layout.addWidget(self.lbl_purchases)
        
        stats_layout.addSpacing(20)
        
        self.lbl_tva = QLabel("TOTAL TVA: 0.00 DA")
        self.lbl_tva.setStyleSheet("font-weight: bold; color: #E67E22; font-size: 14px;")
        stats_layout.addWidget(self.lbl_tva)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

    def refresh_data(self, query: str = ""):
        self.table.setRowCount(0)
        
        # Fetch data
        q = self.db_session.query(SupplierInvoice).filter_by(is_deleted=0)
        invoices = q.order_by(SupplierInvoice.id.desc()).all()
        
        if query:
            query = query.lower()
            invoices = [inv for inv in invoices if query in (inv.invoice_number or "").lower() or query in (inv.supplier.name.lower() if inv.supplier else "")]

        total_ht = 0.0
        total_tva = 0.0
        for inv in invoices:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(inv.invoice_number or "—"))
            self.table.setItem(row, 1, QTableWidgetItem(inv.our_reference or "—"))
            self.table.setItem(row, 2, QTableWidgetItem(inv.supplier.name if inv.supplier else "—"))
            self.table.setItem(row, 3, QTableWidgetItem(inv.invoice_date))
            self.table.setItem(row, 4, QTableWidgetItem(f"{inv.total_ht:.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{inv.total_tva:.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(f"{inv.total_ttc:.2f}"))
            
            status = "Validée" if inv.status == "VALIDATED" else "Brouillon"
            self.table.setItem(row, 7, QTableWidgetItem(status))
            
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            
            view_btn = QPushButton("👁️")
            view_btn.clicked.connect(lambda checked, i=inv: self._on_view(i))
            action_layout.addWidget(view_btn)
            
            print_btn = QPushButton("🖨️")
            print_btn.clicked.connect(lambda checked, i=inv: self._on_print(i))
            action_layout.addWidget(print_btn)
            
            self.table.setCellWidget(row, 8, action_widget)
            
            total_ht += inv.total_ht
            total_tva += inv.total_tva
            
        self.lbl_purchases.setText(f"TOTAL ACHATS (HT): {total_ht:,.2f} DA".replace(",", " "))
        self.lbl_tva.setText(f"TOTAL TVA: {total_tva:,.2f} DA".replace(",", " "))

    def _on_search(self, text):
        self.refresh_data(text)

    def _on_new(self):
        dlg = SupplierInvoiceDialog(self.user, parent=self)
        if dlg.exec():
            self.refresh_data(self.search_input.text())
            
    def _on_view(self, invoice):
        dlg = SupplierInvoiceDialog(self.user, invoice=invoice, parent=self)
        dlg.exec()
        self.refresh_data(self.search_input.text())

    def _on_print(self, invoice):
        from app.utils.pdf_exporter import FiscalPDFExporter
        from PySide6.QtWidgets import QFileDialog
        import os
        d = QFileDialog.getSaveFileName(self, "Enregistrer Facture", 
            f"Facture_{invoice.invoice_number or invoice.id}.pdf", "PDF (*.pdf)")
        if d[0]:
            try:
                FiscalPDFExporter.export_supplier_invoice_to_pdf(d[0], self.db_session, invoice.id)
                QMessageBox.information(self, "Succès", "Facture imprimée/exportée avec succès.")
                os.startfile(d[0])
            except Exception as e:
                QMessageBox.critical(self, "Erreur PDF", f"Impossible de générer le PDF:\\n{e}")
