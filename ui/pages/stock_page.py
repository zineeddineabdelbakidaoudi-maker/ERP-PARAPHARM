"""
ParaFarm ERP — Stock Management Page
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QCheckBox
)
from PySide6.QtCore import Qt
from app.core.database import get_session
from app.repositories.product_repository import ProductRepository
from ui.dialogs.stock_adjust_dialog import StockAdjustDialog
from ui.dialogs.stock_movement_dialog import StockMovementDialog
from app.core.event_bus import get_event_bus
from ui.pages.base_document_page import make_status_widget


class StockPage(QWidget):

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.product_repo = ProductRepository(self.db_session)
        self._setup_ui()
        self.refresh_data()
        
        get_event_bus().stock_updated.connect(lambda _: self.refresh_data())

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # --- Stats Cards ---
        self.stats_layout = QHBoxLayout()
        self.card_total = self._create_stat_card("Total Articles", "0", "#2196F3")
        self.card_rupture = self._create_stat_card("En Rupture", "0", "#F44336")
        self.card_alerte = self._create_stat_card("En Alerte", "0", "#FF9800")
        self.card_valeur_pa = self._create_stat_card("Valeur Totale (PA)", "0.00 DA", "#4CAF50")
        self.card_valeur_pv = self._create_stat_card("Valeur Totale (PV)", "0.00 DA", "#9C27B0")
        self.stats_layout.addWidget(self.card_total)
        self.stats_layout.addWidget(self.card_rupture)
        self.stats_layout.addWidget(self.card_alerte)
        self.stats_layout.addWidget(self.card_valeur_pa)
        self.stats_layout.addWidget(self.card_valeur_pv)
        layout.addLayout(self.stats_layout)

        # Toolbar
        toolbar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher un produit...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)
        
        self.low_stock_check = QCheckBox("Afficher uniquement ruptures et alertes")
        self.low_stock_check.stateChanged.connect(self._on_filter_change)
        toolbar.addWidget(self.low_stock_check)

        toolbar.addStretch()

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(lambda: self.refresh_data(self.search_input.text()))
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Code", "Désignation", "Famille", "Qté", "PA Moyen", "Valeur Stock", "Statut", "Actions"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 220)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def _create_stat_card(self, title, initial_value, color):
        from PySide6.QtWidgets import QFrame
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                border-left: 5px solid {color};
            }}
        """)
        v = QVBoxLayout(card)
        t = QLabel(title)
        t.setStyleSheet("color: #757575; font-size: 12px; font-weight: bold;")
        v.addWidget(t)
        val = QLabel(initial_value)
        val.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        v.addWidget(val)
        card.value_label = val  # reference to update it later
        return card

    def refresh_data(self, query: str = ""):
        self.table.setRowCount(0)
        self.db_session.expire_all()
        res = self.product_repo.search(query, limit=100) if query else self.product_repo.get_all()
        products = res.get("items", []) if isinstance(res, dict) else res
        show_low_only = self.low_stock_check.isChecked()

        total_articles = len(products)
        en_rupture = 0
        en_alerte = 0
        valeur_pa = 0.0
        valeur_pv = 0.0

        for p in products:
            stock_qty = p.stock.quantity if p.stock else 0.0
            is_rupture = stock_qty <= 0
            is_alerte = stock_qty <= p.min_stock_level and not is_rupture
            
            pa = p.cost_price or 0.0
            pv = p.selling_price or 0.0
            val_stock_pa = stock_qty * pa if stock_qty > 0 else 0.0
            val_stock_pv = stock_qty * pv if stock_qty > 0 else 0.0

            if is_rupture: en_rupture += 1
            if is_alerte: en_alerte += 1
            valeur_pa += val_stock_pa
            valeur_pv += val_stock_pv

            if show_low_only and not (is_rupture or is_alerte):
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(p.code))
            self.table.setItem(row, 1, QTableWidgetItem(p.name))
            self.table.setItem(row, 2, QTableWidgetItem(p.category.name if p.category else "—"))
            
            qty_item = QTableWidgetItem(f"{stock_qty:.2f}")
            if is_rupture: qty_item.setForeground(Qt.red)
            elif is_alerte: qty_item.setForeground(Qt.darkYellow)
            self.table.setItem(row, 3, qty_item)
            
            self.table.setItem(row, 4, QTableWidgetItem(f"{pa:,.2f} DA"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{val_stock_pa:,.2f} DA"))
            
            if is_rupture:
                status_widget = make_status_widget("ANNULE") # Red badge
                status_widget.findChild(QLabel).setText("  🔴 RUPTURE  ")
            elif is_alerte:
                status_widget = make_status_widget("DRAFT") # Orange/Yellow badge
                status_widget.findChild(QLabel).setStyleSheet("background-color: #FFC107; color: black; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: 700;")
                status_widget.findChild(QLabel).setText("  🟠 ALERTE  ")
            else:
                status_widget = make_status_widget("COMPLETED") # Green badge
                status_widget.findChild(QLabel).setText("  🟢 NORMAL  ")
                
            self.table.setCellWidget(row, 6, status_widget)

            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 0, 4, 0)
            action_layout.setSpacing(4)
            
            adjust_btn = QPushButton("⚙️ Ajuster")
            adjust_btn.setProperty("variant", "icon-edit")
            adjust_btn.clicked.connect(lambda checked, prod=p: self._on_adjust_stock(prod))
            action_layout.addWidget(adjust_btn)
            
            history_btn = QPushButton("👁️ Historique")
            history_btn.setProperty("variant", "icon-view")
            history_btn.clicked.connect(lambda checked, prod=p: self._on_view_history(prod))
            action_layout.addWidget(history_btn)
            
            self.table.setCellWidget(row, 7, action_widget)

        self.card_total.value_label.setText(str(total_articles))
        self.card_rupture.value_label.setText(str(en_rupture))
        self.card_alerte.value_label.setText(str(en_alerte))
        self.card_valeur_pa.value_label.setText(f"{valeur_pa:,.2f} DA")
        self.card_valeur_pv.value_label.setText(f"{valeur_pv:,.2f} DA")

    def _on_search(self, text):
        self.refresh_data(text)
        
    def _on_filter_change(self):
        self.refresh_data(self.search_input.text())

    def _on_adjust_stock(self, product):
        dialog = StockAdjustDialog(self.user, product=product, parent=self)
        if dialog.exec():
            self.refresh_data(self.search_input.text())

    def _on_view_history(self, product):
        dialog = StockMovementDialog(product=product, parent=self)
        dialog.exec()
