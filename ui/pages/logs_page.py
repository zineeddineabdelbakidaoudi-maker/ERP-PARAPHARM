from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Audit Log / Journal Page
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from app.core.database import get_session
from app.models.setting import AuditLog
from app.models.user import User


class LogsPage(QWidget):

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

        # Toolbar
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher dans le journal...")
        self.search_input.setMinimumWidth(250)
        self.search_input.textChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.search_input)

        self.module_filter = SearchableComboBox()
        self.module_filter.addItem("Tous les Modules", "")
        self.module_filter.addItems(["PRODUCT", "SALE", "PURCHASE", "STOCK", "CLIENT", "SUPPLIER", "USER", "SETTING"])
        self.module_filter.currentIndexChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.module_filter)

        toolbar.addWidget(QLabel("Du:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        toolbar.addWidget(self.date_from)

        toolbar.addWidget(QLabel("Au:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        toolbar.addWidget(self.date_to)

        refresh_btn = QPushButton("Actualiser")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Date", "Utilisateur", "Module", "Action", "Description", "Entité"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

    def refresh_data(self):
        self.table.setRowCount(0)

        d_from = self.date_from.date().toString("yyyy-MM-dd") + " 00:00:00"
        d_to = self.date_to.date().toString("yyyy-MM-dd") + " 23:59:59"
        query = self.search_input.text().strip().lower()
        module_filter = self.module_filter.currentData()

        q = (
            self.db_session.query(AuditLog)
            .filter(AuditLog.created_at >= d_from, AuditLog.created_at <= d_to)
        )

        if module_filter:
            q = q.filter(AuditLog.module == module_filter)

        logs = q.order_by(AuditLog.created_at.desc()).limit(500).all()

        # Build a user cache
        users = self.db_session.query(User).all()
        user_map = {u.id: u.full_name for u in users}

        for log in logs:
            desc = log.description or ""
            if query and query not in desc.lower() and query not in (log.action or "").lower():
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(log.created_at))
            user_name = user_map.get(log.user_id, "Système")
            self.table.setItem(row, 1, QTableWidgetItem(user_name))
            self.table.setItem(row, 2, QTableWidgetItem(log.module))
            self.table.setItem(row, 3, QTableWidgetItem(log.action))
            self.table.setItem(row, 4, QTableWidgetItem(desc))

            entity = f"{log.entity_type}#{log.entity_id}" if log.entity_type else "—"
            self.table.setItem(row, 5, QTableWidgetItem(entity))
