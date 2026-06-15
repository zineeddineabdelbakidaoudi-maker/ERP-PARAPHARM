from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.delivery import Delivery
import os
from PySide6.QtWidgets import QFileDialog
from app.utils.pdf_exporter import PDFExporter

class DechargePage(QWidget):
    PAGE_TITLE = "Décharges (Preuves de Livraison)"
    
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
        self.search_input.setPlaceholderText("Recherche par N° BL ou Client...")
        self.search_input.textChanged.connect(self.refresh_data)
        toolbar.addWidget(self.search_input)
        
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Setup Form
        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("Nom du livreur:"))
        self.driver_input = QLineEdit()
        form_layout.addWidget(self.driver_input)
        
        self.generate_btn = QPushButton("🖨️ Générer Décharge")
        self.generate_btn.setProperty("variant", "success")
        self.generate_btn.clicked.connect(self._generate_decharge)
        form_layout.addWidget(self.generate_btn)
        
        layout.addLayout(form_layout)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Sel.", "N° BL", "Date", "Client", "Montant Total", "Statut"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

    def refresh_data(self):
        self.table.setRowCount(0)
        query = self.search_input.text().strip().lower()
        
        # We can generate decharge for IN_PROGRESS or COMPLETED deliveries, or even PENDING
        deliveries = self.db_session.query(Delivery).order_by(Delivery.created_at.desc()).limit(100).all()
        
        for d in deliveries:
            if query:
                cname = d.client.name.lower() if d.client else ""
                if query not in d.delivery_number.lower() and query not in cname:
                    continue
                    
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            chk = QCheckBox()
            chk.setProperty("delivery_id", d.id)
            w = QWidget()
            l = QHBoxLayout(w)
            l.addWidget(chk)
            l.setAlignment(Qt.AlignCenter)
            l.setContentsMargins(0,0,0,0)
            self.table.setCellWidget(row, 0, w)
            
            self.table.setItem(row, 1, QTableWidgetItem(d.delivery_number))
            self.table.setItem(row, 2, QTableWidgetItem(d.created_at[:10] if d.created_at else ""))
            self.table.setItem(row, 3, QTableWidgetItem(d.client.name if d.client else "—"))
            amt = d.sale.total_amount if d.sale else sum(i.quantity * (i.product.selling_price if i.product else 0) for i in d.items)
            self.table.setItem(row, 4, QTableWidgetItem(f"{amt:,.2f} DA"))
            self.table.setItem(row, 5, QTableWidgetItem(d.status))

    def _generate_decharge(self):
        delivery_ids = []
        for row in range(self.table.rowCount()):
            w = self.table.cellWidget(row, 0)
            chk = w.findChild(QCheckBox)
            if chk and chk.isChecked():
                delivery_ids.append(chk.property("delivery_id"))
                
        if not delivery_ids:
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner au moins un BL pour la décharge.")
            return
            
        driver_name = self.driver_input.text().strip() or "—"
        
        try:
            d = QFileDialog.getSaveFileName(self, "Enregistrer Décharge", 
                f"Decharge_Livraison_{len(delivery_ids)}_BLs.pdf", "PDF (*.pdf)")
            if d[0]:
                PDFExporter.export_decharge_to_pdf(
                    d[0], self.db_session, delivery_ids, driver_name=driver_name
                )
                QMessageBox.information(self, "Succès", "Décharge générée avec succès.")
                os.startfile(d[0])
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", f"Impossible de générer le PDF:\\n{e}")
