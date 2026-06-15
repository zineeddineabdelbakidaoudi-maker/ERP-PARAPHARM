from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Base Document Page
Reusable base class for all document-based CRUD pages (Orders, Invoices, etc.).
Provides: toolbar (Add/Edit/Delete/Refresh/Search/Filter/Export), data grid, status badges, bottom action bar.
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QFrame, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


STATUS_COLORS = {
    "DRAFT":       ("#757575", "#F5F5F5"),    # grey
    "VALIDATED":   ("#1565C0", "#E3F2FD"),    # blue
    "INVOICED":    ("#6A1B9A", "#F3E5F5"),    # purple
    "COMPLETED":   ("#1B5E20", "#E8F5E9"),    # green
    "IN_PROGRESS": ("#E65100", "#FFF3E0"),    # orange
    "APPLIED":     ("#1B5E20", "#E8F5E9"),    # green
    "SHIPPED":     ("#1565C0", "#E3F2FD"),    # blue
    "CANCELLED":   ("#B71C1C", "#FFEBEE"),    # red
    "MODIFIED":    ("#FFFFFF", "#d35400"),    # dark orange
    # French equivalents
    "BROUILLON":   ("#FFFFFF", "#6c757d"),
    "SOUMIS":      ("#FFFFFF", "#17a2b8"),
    "VALIDE":      ("#FFFFFF", "#28a745"),
    "EN_LIVRAISON":("#FFFFFF", "#fd7e14"),
    "LIVRE":       ("#FFFFFF", "#007bff"),
    "FACTURE":     ("#FFFFFF", "#6610f2"),
    "ANNULE":      ("#FFFFFF", "#dc3545"),
}


def make_status_widget(status_text: str) -> QWidget:
    """Create a colored badge label for a document status."""
    fg, bg = STATUS_COLORS.get(status_text, ("#424242", "#EEEEEE"))
    badge = QLabel(f"  {status_text}  ")
    badge.setAlignment(Qt.AlignCenter)
    badge.setStyleSheet(f"""
        QLabel {{
            background-color: {bg};
            color: {fg};
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 700;
        }}
    """)
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.addStretch()
    layout.addWidget(badge)
    layout.addStretch()
    return container


class BaseDocumentPage(QWidget):
    """
    Abstract base for document-type pages.
    Subclasses must implement:
      - _get_columns() -> list[str]
      - _load_data(search, status_filter) -> list[dict]
      - _on_add()
      - _on_edit(row_data)
      - _on_delete(row_data)
    """

    PAGE_TITLE = "Documents"
    STATUS_OPTIONS = ["Tous", "DRAFT", "VALIDATED", "COMPLETED", "CANCELLED"]

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        from app.core.database import get_session
        self.db_session = get_session()
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # ── Toolbar ──────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher...")
        self.search_input.setMinimumWidth(250)
        self.search_input.textChanged.connect(lambda text: self.refresh_data())
        toolbar.addWidget(self.search_input)

        self.status_filter = SearchableComboBox()
        self.status_filter.addItems(self.STATUS_OPTIONS)
        self.status_filter.setMinimumWidth(140)
        self.status_filter.currentTextChanged.connect(lambda text: self.refresh_data())
        toolbar.addWidget(self.status_filter)

        toolbar.addStretch()

        add_btn = QPushButton("➕ Ajouter")
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.setProperty("variant", "refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)

        export_btn = QPushButton("📊 Exporter CSV")
        export_btn.setProperty("variant", "export")
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        # ── Data Table ───────────────────────────────────────
        self.instruction_label = QLabel("💡 Clic-droit sur une ligne pour modifier ou supprimer")
        self.instruction_label.setStyleSheet("color: #757575; font-style: italic;")
        layout.addWidget(self.instruction_label)

        self._col_names = ["☑"] + self._get_columns()
        self.table = QTableWidget(0, len(self._col_names))
        
        for i, col_name in enumerate(self._col_names):
            h_item = QTableWidgetItem(col_name)
            if col_name == "☑":
                h_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                h_item.setCheckState(Qt.Unchecked)
            self.table.setHorizontalHeaderItem(i, h_item)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 40)
        
        # Give Actions column a fixed width
        if "Actions" in self._col_names:
            action_idx = self._col_names.index("Actions")
            header.setSectionResizeMode(action_idx, QHeaderView.Fixed)
            self.table.setColumnWidth(action_idx, 420)
            
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        
        # Context menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        
        header.sectionClicked.connect(self._on_header_clicked)
        
        layout.addWidget(self.table)

        # ── Bottom Action Bar ────────────────────────────────
        bottom = QHBoxLayout()
        self.row_count_label = QLabel("0 enregistrements")
        self.row_count_label.setStyleSheet("color: #757575; font-size: 12px;")
        bottom.addWidget(self.row_count_label)
        bottom.addStretch()
        layout.addLayout(bottom)

    def _on_header_clicked(self, logicalIndex):
        if logicalIndex == 0:
            h_item = self.table.horizontalHeaderItem(0)
            state = Qt.Checked if h_item.checkState() == Qt.Unchecked else Qt.Unchecked
            h_item.setCheckState(state)
            
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item:
                    item.setCheckState(state)

    # ── Abstract methods (subclass MUST override) ────────────
    def _get_columns(self) -> list:
        return ["N°", "Date", "Statut", "Total", "Actions"]

    def _load_data(self, search: str, status_filter: str) -> list:
        return []

    def _on_add(self):
        pass

    def _on_edit(self, row_data):
        pass

    def _on_delete(self, row_data):
        pass

    # ── Shared logic ─────────────────────────────────────────
    def refresh_data(self):
        search = self.search_input.text().strip()
        status = self.status_filter.currentText()
        if status == "Tous":
            status = ""

        data = self._load_data(search, status)
        self.table.setRowCount(0)

        if not data:
            self.table.insertRow(0)
            empty = QTableWidgetItem("Aucune donnée trouvée")
            empty.setTextAlignment(Qt.AlignCenter)
            empty.setForeground(Qt.gray)
            mid = len(self._col_names) // 2
            self.table.setItem(0, mid, empty)
            self.row_count_label.setText("0 enregistrements")
            return

        self._row_map = {}
        for row_data in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self._row_map[row] = row_data

            for col, key in enumerate(self._col_names):
                if key == "☑":
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    item.setCheckState(Qt.Unchecked)
                    self.table.setItem(row, col, item)
                elif key == "Actions":
                    self._add_action_buttons(row, col, row_data)
                elif key == "Statut":
                    self.table.setCellWidget(row, col, make_status_widget(row_data.get("status", "")))
                else:
                    val = row_data.get(key, "")
                    item = QTableWidgetItem(str(val))
                    item.setData(Qt.UserRole, row_data)
                    self.table.setItem(row, col, item)

        self.row_count_label.setText(f"{self.table.rowCount()} enregistrements")

    def _on_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        row = item.row()
        row_data = self._row_map.get(row)
        if not row_data: return

        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction
        
        menu = QMenu(self)
        
        edit_action = QAction("✏️ Modifier", self)
        edit_action.triggered.connect(lambda: self._on_edit(row_data))
        menu.addAction(edit_action)
        
        del_action = QAction("🗑️ Supprimer", self)
        del_action.triggered.connect(lambda: self._on_delete(row_data))
        menu.addAction(del_action)
        
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _add_action_buttons(self, row, col, row_data):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        record_id = row_data.get("id")

        if hasattr(self, "open_detail"):
            btn_voir = QPushButton("👁 Voir")
            btn_voir.setFixedWidth(70)
            btn_voir.setStyleSheet("background: #17a2b8; color: white; border-radius: 3px; padding: 2px 6px;")
            btn_voir.clicked.connect(lambda checked, r_id=record_id: self.open_detail(r_id))
            layout.addWidget(btn_voir)

        if hasattr(self, "print_document"):
            btn_print = QPushButton("🖨 Imprimer")
            btn_print.setFixedWidth(90)
            btn_print.setStyleSheet("background: #6c757d; color: white; border-radius: 3px; padding: 2px 6px;")
            btn_print.clicked.connect(lambda checked, r_id=record_id: self.print_document(r_id))
            layout.addWidget(btn_print)

        self.table.setCellWidget(row, col, widget)

    def _export_csv(self):
        import csv
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Aucune donnée à exporter.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter CSV",
            f"Export_{self.PAGE_TITLE}_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                valid_cols = [c for c in self._col_names if c not in ("Actions", "☑")]
                writer.writerow(valid_cols)
                
                for r in range(self.table.rowCount()):
                    row_vals = []
                    for c in range(len(self._col_names)):
                        col_name = self._col_names[c]
                        if col_name in ("Actions", "☑"):
                            continue
                        item = self.table.item(r, c)
                        if item:
                            row_vals.append(item.text())
                        else:
                            # Might be a widget (like status badge)
                            w = self.table.cellWidget(r, c)
                            if w:
                                # try to extract text from QLabel inside
                                lbl = w.findChild(QLabel)
                                row_vals.append(lbl.text().strip() if lbl else "")
                            else:
                                row_vals.append("")
                    writer.writerow(row_vals)
            QMessageBox.information(self, "Succès", f"Export CSV réussi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
