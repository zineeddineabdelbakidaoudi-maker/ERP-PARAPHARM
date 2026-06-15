import sys

# 1. Patch SupplierDocumentCreationDialog
file_path_br = 'ui/dialogs/supplier_document_creation_dialog.py'
with open(file_path_br, 'r', encoding='utf-8') as f:
    content_br = f.read()

# Make TVA visible for all
content_br = content_br.replace(
    '        if hasattr(self, \'tva_spin\'):\n            self.tva_spin.setVisible(is_facture)',
    '        if hasattr(self, \'tva_spin\'):\n            pass #self.tva_spin.setVisible(is_facture)'
)
content_br = content_br.replace(
    '        if hasattr(self, \'lbl_tva\'):\n            self.lbl_tva.setVisible(is_facture)',
    '        if hasattr(self, \'lbl_tva\'):\n            pass #self.lbl_tva.setVisible(is_facture)'
)

# _on_add TVA logic
content_br = content_br.replace(
    '        tva = self.tva_spin.value() if is_facture else 0.0',
    '        tva = self.tva_spin.value()'
)

content_br = content_br.replace(
    '        tva_amt = net_ht * (tva / 100.0)',
    '        tva_amt = net_ht * (tva / 100.0) if is_facture else 0.0'
)

# Update product details on save
update_code = """
        try:
            # Update product details
            for i in self.items:
                p = self.db_session.query(Product).get(i["product_id"])
                if p:
                    p.cost_price = i["pu_ht"]
                    p.selling_price = i.get("pu_vente", p.selling_price)
                    p.tax_rate = i["tva"]
                    p.ppt_price = i.get("ppt", p.ppt_price)
            self.db_session.flush()

            if is_facture:
"""

content_br = content_br.replace(
    '        try:\n            if is_facture:',
    update_code
)

with open(file_path_br, 'w', encoding='utf-8') as f:
    f.write(content_br)


# 2. Patch StockMovementDialog
file_path_stock = 'ui/dialogs/stock_movement_dialog.py'

new_stock_code = """\"\"\"
ParaFarm ERP ?" Stock Movement Dialog
Displays the movement history and batch details for a specific product.
\"\"\"
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QTabWidget, QWidget
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.models.stock import StockMovement, StockBatch


class StockMovementDialog(QDialog):
    \"\"\"View history of stock movements and lots for a product.\"\"\"

    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.product = product
        self.db_session = get_session()
        self.setWindowTitle(f"Stock - {product.name}")
        self.setMinimumSize(800, 500)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel(f"Produit: {self.product.name} (Code: {self.product.code})")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        
        # Tab 1: Historique Mouvements
        tab1 = QWidget()
        t1_layout = QVBoxLayout(tab1)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Date", "Type", "Quantité", "Raison", "Utilisateur"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        t1_layout.addWidget(self.table)
        
        # Totals
        totals_layout = QHBoxLayout()
        self.lbl_total_pa = QLabel("Valeur Totale Achat (PA): 0.00 DA")
        self.lbl_total_pa.setStyleSheet("font-weight: bold; font-size: 14px; color: #34495E;")
        self.lbl_total_pv = QLabel("Valeur Totale Vente (PV): 0.00 DA")
        self.lbl_total_pv.setStyleSheet("font-weight: bold; font-size: 14px; color: #2E86C1;")
        totals_layout.addWidget(self.lbl_total_pa)
        totals_layout.addSpacing(20)
        totals_layout.addWidget(self.lbl_total_pv)
        totals_layout.addStretch()
        t1_layout.addLayout(totals_layout)
        
        self.tabs.addTab(tab1, "Historique Mouvements")
        
        # Tab 2: Lots & Péremptions
        tab2 = QWidget()
        t2_layout = QVBoxLayout(tab2)
        self.lots_table = QTableWidget(0, 4)
        self.lots_table.setHorizontalHeaderLabels([
            "N° Lot", "Date Péremption", "Qté Restante", "Prix Achat"
        ])
        header_lots = self.lots_table.horizontalHeader()
        header_lots.setSectionResizeMode(QHeaderView.Stretch)
        self.lots_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.lots_table.verticalHeader().setVisible(False)
        self.lots_table.verticalHeader().setDefaultSectionSize(40)
        t2_layout.addWidget(self.lots_table)
        self.tabs.addTab(tab2, "Lots & Péremptions")

        layout.addWidget(self.tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Fermer")
        close_btn.setProperty("variant", "secondary")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _load_data(self):
        # 1. Load Movements
        self.table.setRowCount(0)
        
        movements = (
            self.db_session.query(StockMovement)
            .filter(StockMovement.product_id == self.product.id)
            .order_by(StockMovement.created_at.desc())
            .limit(100)
            .all()
        )

        total_in_pa = 0.0
        total_in_pv = 0.0

        for mov in movements:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(mov.created_at))
            
            type_item = QTableWidgetItem(mov.movement_type)
            if "IN" in mov.movement_type or mov.quantity > 0:
                type_item.setForeground(Qt.darkGreen)
            elif "OUT" in mov.movement_type or mov.quantity < 0:
                type_item.setForeground(Qt.darkRed)
            self.table.setItem(row, 1, type_item)

            qty_prefix = "+" if mov.quantity > 0 else ""
            qty_item = QTableWidgetItem(f"{qty_prefix}{mov.quantity:.0f}")
            if mov.quantity > 0:
                qty_item.setForeground(Qt.darkGreen)
            elif mov.quantity < 0:
                qty_item.setForeground(Qt.darkRed)
            self.table.setItem(row, 2, qty_item)

            self.table.setItem(row, 3, QTableWidgetItem(mov.notes or "---"))
            
            user_name = mov.user.full_name if hasattr(mov, 'user') and mov.user else f"ID: {mov.user_id}" if mov.user_id else "Système"
            self.table.setItem(row, 4, QTableWidgetItem(user_name))
            
            if mov.quantity > 0:
                cost = mov.unit_cost if mov.unit_cost else self.product.cost_price
                total_in_pa += (mov.quantity * cost)
                total_in_pv += (mov.quantity * self.product.selling_price)
                
        # Total represents the value of IN movements
        self.lbl_total_pa.setText(f"Valeur Totale Achat (PA Entrées): {total_in_pa:,.2f} DA".replace(",", " "))
        self.lbl_total_pv.setText(f"Valeur Totale Vente (PV Entrées): {total_in_pv:,.2f} DA".replace(",", " "))
        
        # 2. Load Lots
        self.lots_table.setRowCount(0)
        batches = (
            self.db_session.query(StockBatch)
            .filter(StockBatch.product_id == self.product.id)
            .filter(StockBatch.remaining_quantity > 0)
            .order_by(StockBatch.expiration_date.asc())
            .all()
        )
        for b in batches:
            row = self.lots_table.rowCount()
            self.lots_table.insertRow(row)
            self.lots_table.setItem(row, 0, QTableWidgetItem(b.lot_number or "N/A"))
            self.lots_table.setItem(row, 1, QTableWidgetItem(b.expiration_date or "N/A"))
            self.lots_table.setItem(row, 2, QTableWidgetItem(f"{b.remaining_quantity:.2f}"))
            cost_str = f"{b.cost_price:.2f} DA" if b.cost_price is not None else "---"
            self.lots_table.setItem(row, 3, QTableWidgetItem(cost_str))

"""

with open(file_path_stock, 'w', encoding='utf-8') as f:
    f.write(new_stock_code)

print("patched")
