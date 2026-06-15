"""
ParaFarm ERP — Notifications Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from app.core.database import get_session

class NotificationsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Alertes & Notifications")
        self.setMinimumSize(500, 400)
        self.db_session = get_session()
        self._setup_ui()
        self._load_alerts()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("Alertes Stock & Péremptions")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget::item { padding: 12px; border-bottom: 1px solid #E0E0E0; }")
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("Fermer")
        close_btn.setProperty("variant", "secondary")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _load_alerts(self):
        from app.models.product import Product
        from app.models.stock import StockBatch
        from sqlalchemy.orm import joinedload
        from datetime import datetime, timedelta

        now = datetime.now()
        thirty_days = now + timedelta(days=30)
        
        self.list_widget.clear()

        # 1. Low stock alerts
        products = self.db_session.query(Product).options(joinedload(Product.stock)).all()
        for p in products:
            if not p.stock: continue
            if p.stock.quantity <= p.min_stock_level:
                item = QListWidgetItem(f"⚠️ Stock Critique: '{p.name}' (Reste: {p.stock.quantity:.0f}, Min: {p.min_stock_level})")
                item.setForeground(Qt.darkYellow)
                self.list_widget.addItem(item)

        # 2. Expiry alerts
        batches = self.db_session.query(StockBatch).options(joinedload(StockBatch.product)).filter(StockBatch.remaining_quantity > 0).all()
        for b in batches:
            if b.expiration_date:
                try:
                    exp_date = datetime.strptime(b.expiration_date, "%Y-%m-%d")
                    if exp_date < now:
                        item = QListWidgetItem(f"❌ PÉRIMÉ: '{b.product.name}' Lot {b.lot_number} expiré le {b.expiration_date} (Qté: {b.remaining_quantity:.0f})")
                        item.setForeground(Qt.red)
                        self.list_widget.addItem(item)
                    elif exp_date <= thirty_days:
                        item = QListWidgetItem(f"⚠️ Bientôt périmé: '{b.product.name}' Lot {b.lot_number} expire le {b.expiration_date} (Qté: {b.remaining_quantity:.0f})")
                        item.setForeground(Qt.darkYellow)
                        self.list_widget.addItem(item)
                except ValueError:
                    pass

        if self.list_widget.count() == 0:
            item = QListWidgetItem("✅ Aucune alerte pour le moment.")
            item.setForeground(Qt.darkGreen)
            item.setTextAlignment(Qt.AlignCenter)
            self.list_widget.addItem(item)
