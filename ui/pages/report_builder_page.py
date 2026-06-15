from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Report Builder Page
"""
import json
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QDateEdit, QGroupBox, QSplitter, QListWidget,
    QMessageBox, QScrollArea, QListWidgetItem, QInputDialog
)
from PySide6.QtCore import Qt, QDate
from app.core.database import get_session
from app.models.report import SavedReport
from app.utils.pdf_exporter import PDFExporter

# Mappings of modules to their available columns
MODULE_COLUMNS = {
    "Ventes": ["N° Vente", "Date", "Client", "Total HT", "TVA", "Total TTC", "Méthode Paiement", "Statut", "Créé Par"],
    "Achats": ["N° Achat", "Date", "Fournisseur", "Total TTC", "Statut"],
    "Inventaire": ["Produit", "Catégorie", "Code-barres", "Stock Actuel", "Seuil Alerte", "Prix Achat", "Prix Vente"],
    "Clients": ["Code", "Nom", "Téléphone", "Email", "Crédit Limite", "Catégorie"],
    "Fournisseurs": ["Code", "Nom", "Téléphone", "Catégorie", "NIF", "RC"],
    "Livraisons": ["N° Livraison", "Date", "Client", "Tournée", "Statut", "Zone"]
}

class ReportBuilderPage(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.selected_module = None
        self._setup_ui()
        self._load_saved_reports()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        title = QLabel("Créateur de Rapports Personnalisés")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1B5E20;")
        layout.addWidget(title)

        splitter = QSplitter(Qt.Horizontal)
        
        # --- LEFT PANEL: Saved Reports ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        saved_lbl = QLabel("Rapports Sauvegardés")
        saved_lbl.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(saved_lbl)
        
        self.saved_list = QListWidget()
        self.saved_list.itemDoubleClicked.connect(self._on_load_report)
        left_layout.addWidget(self.saved_list)
        
        del_rep_btn = QPushButton("🗑️ Supprimer le rapport")
        del_rep_btn.setProperty("variant", "danger")
        del_rep_btn.clicked.connect(self._delete_report)
        left_layout.addWidget(del_rep_btn)
        
        splitter.addWidget(left_panel)
        splitter.setSizes([200, 800])
        
        # --- RIGHT PANEL: Builder ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Step 1: Data Source
        g1 = QGroupBox("Étape 1: Source de Données")
        g1_layout = QHBoxLayout(g1)
        g1_layout.addWidget(QLabel("Module de base :"))
        self.module_combo = SearchableComboBox()
        self.module_combo.addItems(["", "Ventes", "Achats", "Inventaire", "Clients", "Fournisseurs", "Livraisons"])
        self.module_combo.currentTextChanged.connect(self._on_module_changed)
        g1_layout.addWidget(self.module_combo)
        g1_layout.addStretch()
        right_layout.addWidget(g1)
        
        # Step 2: Columns
        g2 = QGroupBox("Étape 2: Sélection des Colonnes")
        g2_layout = QVBoxLayout(g2)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(100)
        
        self.columns_widget = QWidget()
        self.columns_layout = QHBoxLayout(self.columns_widget)
        self.columns_layout.setAlignment(Qt.AlignLeft)
        scroll.setWidget(self.columns_widget)
        g2_layout.addWidget(scroll)
        self.col_checkboxes = {}
        right_layout.addWidget(g2)
        
        # Step 3: Filters & Grouping
        g3 = QGroupBox("Étape 3: Filtres et Groupement")
        g3_layout = QHBoxLayout(g3)
        
        g3_layout.addWidget(QLabel("Du:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        g3_layout.addWidget(self.date_from)
        
        g3_layout.addWidget(QLabel("Au:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        g3_layout.addWidget(self.date_to)
        
        g3_layout.addWidget(QLabel("Statut:"))
        self.status_combo = SearchableComboBox()
        self.status_combo.addItems(["Tous", "COMPLETED", "VALIDATED", "DRAFT", "PENDING", "FAILED"])
        g3_layout.addWidget(self.status_combo)
        
        g3_layout.addWidget(QLabel("Trier par:"))
        self.sort_combo = SearchableComboBox()
        g3_layout.addWidget(self.sort_combo)
        
        right_layout.addWidget(g3)
        
        # Step 4: Preview & Export
        g4 = QGroupBox("Étape 4: Aperçu & Exportation")
        g4_layout = QVBoxLayout(g4)
        
        preview_btns = QHBoxLayout()
        preview_btn = QPushButton("👁️ Générer l'Aperçu")
        preview_btn.setProperty("variant", "primary")
        preview_btn.clicked.connect(self._generate_preview)
        preview_btns.addWidget(preview_btn)
        preview_btns.addStretch()
        
        save_btn = QPushButton("💾 Sauvegarder Modèle")
        save_btn.clicked.connect(self._save_report_model)
        preview_btns.addWidget(save_btn)
        
        export_csv = QPushButton("📊 Exporter CSV")
        export_csv.setProperty("variant", "export")
        export_csv.clicked.connect(self._export_csv)
        preview_btns.addWidget(export_csv)
        
        export_pdf = QPushButton("📄 Exporter PDF")
        export_pdf.setProperty("variant", "print")
        export_pdf.clicked.connect(self._export_pdf)
        preview_btns.addWidget(export_pdf)
        
        g4_layout.addLayout(preview_btns)
        
        self.preview_table = QTableWidget(0, 0)
        self.preview_table.verticalHeader().setDefaultSectionSize(48)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        g4_layout.addWidget(self.preview_table)
        
        right_layout.addWidget(g4)
        
        splitter.addWidget(right_panel)
        layout.addWidget(splitter)
        
        # Initial disable
        g2.setEnabled(False)
        g3.setEnabled(False)
        g4.setEnabled(False)
        self.groups = [g2, g3, g4]

    def _load_saved_reports(self):
        self.saved_list.clear()
        reports = self.db_session.query(SavedReport).filter_by(is_deleted=0).all()
        for r in reports:
            item = QListWidgetItem(f"📄 {r.name}")
            item.setData(Qt.UserRole, r.id)
            self.saved_list.addItem(item)

    def _delete_report(self):
        item = self.saved_list.currentItem()
        if not item: return
        r_id = item.data(Qt.UserRole)
        
        reply = QMessageBox.question(self, "Confirmer", "Supprimer ce rapport sauvegardé ?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            r = self.db_session.query(SavedReport).get(r_id)
            r.is_deleted = 1
            self.db_session.commit()
            self._load_saved_reports()

    def _on_module_changed(self, module_name):
        # Clear existing
        for i in reversed(range(self.columns_layout.count())):
            w = self.columns_layout.itemAt(i).widget()
            if w: w.deleteLater()
        self.col_checkboxes.clear()
        self.sort_combo.clear()
        self.sort_combo.addItem("Date / Défaut")
        
        self.selected_module = module_name
        
        if not module_name:
            for g in self.groups: g.setEnabled(False)
            return
            
        for g in self.groups: g.setEnabled(True)
        
        cols = MODULE_COLUMNS.get(module_name, [])
        for col in cols:
            cb = QCheckBox(col)
            cb.setChecked(True)
            self.columns_layout.addWidget(cb)
            self.col_checkboxes[col] = cb
            self.sort_combo.addItem(col)

    def _on_load_report(self, item):
        r_id = item.data(Qt.UserRole)
        r = self.db_session.query(SavedReport).get(r_id)
        if not r: return
        
        # Load Module
        self.module_combo.setCurrentText(r.base_module)
        
        # Load Columns
        selected_cols = r.selected_columns if r.selected_columns else []
        for col, cb in self.col_checkboxes.items():
            cb.setChecked(col in selected_cols)
            
        # Load Filters
        if r.filters:
            f = r.filters
            if "status" in f:
                self.status_combo.setCurrentText(f["status"])
                
        if r.sort_by:
            self.sort_combo.setCurrentText(r.sort_by)
            
        self._generate_preview()

    def _save_report_model(self):
        if not self.selected_module: return
        
        name, ok = QInputDialog.getText(self, "Sauvegarder Rapport", "Nom du rapport:")
        if ok and name:
            selected_cols = [col for col, cb in self.col_checkboxes.items() if cb.isChecked()]
            filters = {
                "status": self.status_combo.currentText()
            }
            
            sr = SavedReport(
                name=name,
                base_module=self.selected_module,
                selected_columns=selected_cols,
                filters=filters,
                sort_by=self.sort_combo.currentText(),
                created_by=self.user.id
            )
            self.db_session.add(sr)
            self.db_session.commit()
            self._load_saved_reports()
            QMessageBox.information(self, "Succès", "Rapport sauvegardé avec succès.")

    def _generate_preview(self):
        """Generates dynamic data for the preview grid based on DB models"""
        if not self.selected_module: return
        
        selected_cols = [col for col, cb in self.col_checkboxes.items() if cb.isChecked()]
        if not selected_cols:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner au moins une colonne.")
            return
            
        self.preview_table.setColumnCount(len(selected_cols))
        self.preview_table.setHorizontalHeaderLabels(selected_cols)
        self.preview_table.setRowCount(0)
        
        d_from = self.date_from.date().toString("yyyy-MM-dd") + " 00:00:00"
        d_to = self.date_to.date().toString("yyyy-MM-dd") + " 23:59:59"
        status_filter = self.status_combo.currentText()
        
        data = []
        
        # Mock fetching logic for preview (In a real app, we use generic queries)
        # We will use raw SQL or SQLAlchemy to fetch real data
        if self.selected_module == "Ventes":
            from app.models.sale import Sale
            q = self.db_session.query(Sale).filter(Sale.sale_date >= d_from, Sale.sale_date <= d_to)
            if status_filter != "Tous":
                q = q.filter(Sale.status == status_filter)
            for s in q.limit(100).all():
                row = []
                for c in selected_cols:
                    if c == "N° Vente": row.append(s.sale_number)
                    elif c == "Date": row.append(s.sale_date)
                    elif c == "Client": row.append(s.client.name if s.client else "—")
                    elif c == "Total HT": row.append(f"{s.subtotal:.2f}")
                    elif c == "TVA": row.append(f"{s.tax_total:.2f}")
                    elif c == "Total TTC": row.append(f"{s.total_amount:.2f}")
                    elif c == "Méthode Paiement": row.append(s.payment_method)
                    elif c == "Statut": row.append(s.status)
                    elif c == "Créé Par": row.append(s.creator.username if hasattr(s, 'creator') and s.creator else "—")
                    else: row.append("—")
                data.append(row)
                
        elif self.selected_module == "Inventaire":
            from app.models.product import Product
            q = self.db_session.query(Product).filter_by(is_deleted=0)
            for p in q.limit(100).all():
                row = []
                for c in selected_cols:
                    if c == "Produit": row.append(p.name)
                    elif c == "Catégorie": row.append(p.category.name if p.category else "—")
                    elif c == "Code-barres": row.append(p.barcode or "—")
                    elif c == "Stock Actuel": row.append(str(p.stock_quantity))
                    elif c == "Seuil Alerte": row.append(str(p.min_stock_level))
                    elif c == "Prix Achat": row.append(f"{p.cost_price:.2f}")
                    elif c == "Prix Vente": row.append(f"{p.selling_price:.2f}")
                    else: row.append("—")
                data.append(row)
                
        elif self.selected_module == "Achats":
            from app.models.purchase_order import PurchaseOrder
            q = self.db_session.query(PurchaseOrder)
            for p in q.limit(100).all():
                row = []
                for c in selected_cols:
                    if c == "N° Achat": row.append(p.order_number)
                    elif c == "Date": row.append(p.created_at[:10])
                    elif c == "Fournisseur": row.append(p.supplier.name if p.supplier else "—")
                    elif c == "Total TTC": row.append(f"{p.total_amount:.2f}")
                    elif c == "Statut": row.append(p.status)
                    else: row.append("—")
                data.append(row)
                
        # Populate Preview Table
        for row_data in data:
            row_idx = self.preview_table.rowCount()
            self.preview_table.insertRow(row_idx)
            for col_idx, val in enumerate(row_data):
                self.preview_table.setItem(row_idx, col_idx, QTableWidgetItem(str(val)))

    def _export_csv(self):
        import csv
        if self.preview_table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Générez un aperçu avant d'exporter.")
            return

        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter CSV", f"Rapport_{self.selected_module}.csv", "CSV Files (*.csv)")
        if not file_path: return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                headers = [self.preview_table.horizontalHeaderItem(c).text() for c in range(self.preview_table.columnCount())]
                writer.writerow(headers)
                for r in range(self.preview_table.rowCount()):
                    row_vals = []
                    for c in range(len(headers)):
                        item = self.preview_table.item(r, c)
                        row_vals.append(item.text() if item else "")
                    writer.writerow(row_vals)
            QMessageBox.information(self, "Succès", f"Export CSV réussi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def _export_pdf(self):
        if self.preview_table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Générez un aperçu avant d'exporter.")
            return

        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Exporter PDF", f"Rapport_{self.selected_module}.pdf", "PDF Files (*.pdf)")
        if not file_path: return

        try:
            headers = [self.preview_table.horizontalHeaderItem(c).text() for c in range(self.preview_table.columnCount())]
            data = []
            for row in range(self.preview_table.rowCount()):
                row_data = [self.preview_table.item(row, col).text() if self.preview_table.item(row, col) else "" for col in range(self.preview_table.columnCount())]
                data.append(row_data)

            filters = f"Période: {self.date_from.date().toString('yyyy-MM-dd')} au {self.date_to.date().toString('yyyy-MM-dd')} | Statut: {self.status_combo.currentText()}"
            
            PDFExporter.export_table_to_pdf(
                file_path=file_path,
                title=f"Rapport Personnalisé: {self.selected_module}",
                headers=headers,
                data=data,
                filters=filters
            )
            QMessageBox.information(self, "Succès", f"Export PDF réussi:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
