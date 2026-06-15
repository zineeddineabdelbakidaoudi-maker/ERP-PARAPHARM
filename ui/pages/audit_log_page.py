from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from app.core.database import get_session
import sqlite3
from app.config import config

class AuditLogPage(QWidget):
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

        # Title
        title = QLabel("Historique des Actions (Audit)")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2C3E50;")
        layout.addWidget(title)

        # Toolbar
        toolbar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher (Action, Utilisateur, Détails)...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_input)
        
        toolbar.addWidget(QLabel("Du:"))
        self.date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        toolbar.addWidget(self.date_from)
        
        toolbar.addWidget(QLabel("Au:"))
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        toolbar.addWidget(self.date_to)

        filter_btn = QPushButton("Filtrer")
        filter_btn.clicked.connect(lambda: self.refresh_data(self.search_input.text()))
        toolbar.addWidget(filter_btn)

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(lambda: self.refresh_data(self.search_input.text()))
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "ID", "Date & Heure", "Utilisateur", "Action", "Détails"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def refresh_data(self, query=""):
        self.table.setRowCount(0)
        config.load()
        conn = sqlite3.connect(config.db_path)
        cur = conn.cursor()
        
        start = self.date_from.date().toString("yyyy-MM-dd 00:00:00")
        end = self.date_to.date().toString("yyyy-MM-dd 23:59:59")
        
        sql = '''
            SELECT a.id, a.created_at, u.username, a.action, a.description, a.module
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.created_at BETWEEN ? AND ?
        '''
        params = [start, end]
        
        if query:
            query = f"%{query}%"
            sql += ' AND (u.username LIKE ? OR a.action LIKE ? OR a.description LIKE ?)'
            params.extend([query, query, query])
            
        sql += ' ORDER BY a.created_at DESC LIMIT 1000'
        
        cur.execute(sql, params)
        rows = cur.fetchall()
        
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(row[0])))
            self.table.setItem(r, 1, QTableWidgetItem(str(row[1])))
            self.table.setItem(r, 2, QTableWidgetItem(str(row[2] or "Système")))
            self.table.setItem(r, 3, QTableWidgetItem(f"[{row[5]}] {row[3]}"))
            self.table.setItem(r, 4, QTableWidgetItem(str(row[4] or "")))
            
        conn.close()

    def _on_search(self, text):
        self.refresh_data(text)
