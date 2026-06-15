from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Inventory Count Page (Inventaire Physique)
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QFrame, QComboBox,
    QDoubleSpinBox, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from app.core.database import get_session
from app.models.warehouse import Warehouse, InventoryCount, InventoryCountItem
from app.models.product import Product
from app.models.stock import Stock
from ui.pages.base_document_page import BaseDocumentPage, make_status_widget


class InventoryCountDialog(QDialog):
    """Dialog to create and perform a physical inventory count via QStackedWidget workflow."""
    def __init__(self, db_session, user, count=None, parent=None):
        super().__init__(parent)
        self.db_session = db_session
        self.user = user
        self.count_obj = count
        self.line_items = []
        self.setWindowTitle("Inventaire Physique")
        self.setMinimumSize(900, 650)
        self._setup_ui()
        if count:
            self._load_data()

    def _setup_ui(self):
        from PySide6.QtWidgets import QStackedWidget, QProgressBar
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMaximum(3)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        layout.addWidget(self.progress)

        self.step_label = QLabel("Étape 0 : Création de la Fiche Inventaire")
        self.step_label.setProperty("class", "sectionTitle")
        layout.addWidget(self.step_label)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # --- STEP 0: Configuration ---
        step0 = QWidget()
        s0_layout = QVBoxLayout(step0)
        form_frame = QFrame()
        form_frame.setProperty("class", "card")
        form = QFormLayout(form_frame)
        self.warehouse_combo = SearchableComboBox()
        self.warehouse_combo.addItem("— Tous les entrepôts —", None)
        for w in self.db_session.query(Warehouse).filter(Warehouse.is_active == 1).all():
            self.warehouse_combo.addItem(w.name, w.id)
        form.addRow("Entrepôt cible", self.warehouse_combo)
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        form.addRow("Notes & Observations", self.notes_input)
        s0_layout.addWidget(form_frame)
        s0_layout.addStretch()
        self.stack.addWidget(step0)

        # --- STEP 1: Saisie (Comptage) ---
        step1 = QWidget()
        s1_layout = QVBoxLayout(step1)
        load_bar = QHBoxLayout()
        load_btn = QPushButton("📦 Charger les produits du système")
        load_btn.setStyleSheet("background-color: #0D47A1; color: white;")
        load_btn.clicked.connect(self._load_all_products)
        load_bar.addWidget(load_btn)
        load_bar.addStretch()
        s1_layout.addLayout(load_bar)

        self.items_table = QTableWidget(0, 3)
        self.items_table.setHorizontalHeaderLabels(["Produit", "Stock Théorique", "Quantité Comptée (Réelle)"])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.setAlternatingRowColors(True)
        s1_layout.addWidget(self.items_table)
        self.stack.addWidget(step1)

        # --- STEP 2: Validation des Écarts ---
        step2 = QWidget()
        s2_layout = QVBoxLayout(step2)
        s2_layout.addWidget(QLabel("⚠️ <b>Analyse des écarts avant validation finale :</b>"))
        self.diff_table = QTableWidget(0, 4)
        self.diff_table.setHorizontalHeaderLabels(["Produit", "Attendu", "Compté", "Écart"])
        self.diff_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        s2_layout.addWidget(self.diff_table)
        self.diff_label = QLabel("Total des écarts : 0")
        self.diff_label.setStyleSheet("color: #D32F2F; font-weight: bold;")
        s2_layout.addWidget(self.diff_label)
        self.stack.addWidget(step2)

        # --- STEP 3: Confirmation Finale ---
        step3 = QWidget()
        s3_layout = QVBoxLayout(step3)
        s3_layout.addStretch()
        msg = QLabel("✅ <b>L'inventaire est prêt à être validé.</b><br><br>Le stock système sera écrasé et remplacé par les quantités réelles comptées.<br>Cette action génèrera un rapport d'inventaire.")
        msg.setAlignment(Qt.AlignCenter)
        s3_layout.addWidget(msg)
        s3_layout.addStretch()
        self.stack.addWidget(step3)

        # Buttons
        btns = QHBoxLayout()
        self.btn_prev = QPushButton("⬅️ Précédent")
        self.btn_prev.clicked.connect(self._prev_step)
        btns.addWidget(self.btn_prev)
        btns.addStretch()
        
        cancel = QPushButton("Annuler")
        cancel.setProperty("variant", "secondary")
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        
        self.btn_next = QPushButton("Suivant ➡️")
        self.btn_next.setStyleSheet("background-color: #2E7D32; color: white;")
        self.btn_next.clicked.connect(self._next_step)
        btns.addWidget(self.btn_next)
        
        layout.addLayout(btns)
        self._update_ui_state()

    def _load_data(self):
        for i in range(self.warehouse_combo.count()):
            if self.warehouse_combo.itemData(i) == self.count_obj.warehouse_id:
                self.warehouse_combo.setCurrentIndex(i)
                break
        if self.count_obj.notes:
            self.notes_input.setText(self.count_obj.notes)
        for item in self.count_obj.items:
            self.line_items.append({
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else "—",
                "expected": item.expected_quantity,
                "counted": item.counted_quantity,
            })
        self._refresh_table()

    def _load_all_products(self):
        self.line_items.clear()
        products = self.db_session.query(Product).order_by(Product.name).all()
        for p in products:
            stock_qty = p.stock.quantity if p.stock else 0
            self.line_items.append({
                "product_id": p.id,
                "product_name": p.name,
                "expected": stock_qty,
                "counted": stock_qty,
            })
        self._refresh_table()

    def _refresh_table(self):
        self.items_table.setRowCount(0)
        for i, item in enumerate(self.line_items):
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)

            name_item = QTableWidgetItem(item["product_name"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(row, 0, name_item)

            expected = QTableWidgetItem(f"{item['expected']:.2f}")
            expected.setFlags(expected.flags() & ~Qt.ItemIsEditable)
            self.items_table.setItem(row, 1, expected)

            counted = QTableWidgetItem(f"{item['counted']:.2f}")
            self.items_table.setItem(row, 2, counted)

    def _collect_items(self):
        for row in range(self.items_table.rowCount()):
            try:
                self.line_items[row]["counted"] = float(self.items_table.item(row, 2).text())
            except (ValueError, AttributeError):
                pass

    def _populate_diff_table(self):
        self._collect_items()
        self.diff_table.setRowCount(0)
        diff_count = 0
        for item in self.line_items:
            diff = item["counted"] - item["expected"]
            if diff != 0:
                diff_count += 1
                row = self.diff_table.rowCount()
                self.diff_table.insertRow(row)
                self.diff_table.setItem(row, 0, QTableWidgetItem(item["product_name"]))
                self.diff_table.setItem(row, 1, QTableWidgetItem(f"{item['expected']:.2f}"))
                self.diff_table.setItem(row, 2, QTableWidgetItem(f"{item['counted']:.2f}"))
                
                diff_item = QTableWidgetItem(f"{diff:+.2f}")
                diff_item.setForeground(QColor("#D32F2F") if diff < 0 else QColor("#388E3C"))
                self.diff_table.setItem(row, 3, diff_item)
                
        self.diff_label.setText(f"Total des articles avec écart : {diff_count}")

    def _update_ui_state(self):
        idx = self.stack.currentIndex()
        self.progress.setValue(idx)
        titles = [
            "Étape 0 : Création de la Fiche Inventaire",
            "Étape 1 : Saisie de l'Inventaire (Comptage)",
            "Étape 2 : Analyse des Écarts",
            "Étape 3 : Confirmation Finale"
        ]
        self.step_label.setText(titles[idx])
        self.btn_prev.setVisible(idx > 0)
        
        if idx == 3:
            self.btn_next.setText("✅ Valider l'Inventaire")
        else:
            self.btn_next.setText("Suivant ➡️")

    def _prev_step(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self._update_ui_state()

    def _next_step(self):
        idx = self.stack.currentIndex()
        
        if idx == 0:
            # Go to step 1
            if not self.line_items and self.items_table.rowCount() == 0:
                self._load_all_products()
            self.stack.setCurrentIndex(1)
            
        elif idx == 1:
            # Go to step 2 (Differences)
            self._populate_diff_table()
            self.stack.setCurrentIndex(2)
            
        elif idx == 2:
            # Go to step 3 (Confirm)
            self.stack.setCurrentIndex(3)
            
        elif idx == 3:
            # Finish!
            self._on_validate()
            
        self._update_ui_state()

    def _on_validate(self):
        try:
            # 1. Save or Update Inventory Count object
            if self.count_obj:
                self.count_obj.warehouse_id = self.warehouse_combo.currentData()
                self.count_obj.notes = self.notes_input.toPlainText()
                self.count_obj.status = "VALIDATED"
                self.count_obj.validated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for old in self.count_obj.items:
                    self.db_session.delete(old)
                self.db_session.flush()
                ic = self.count_obj
            else:
                from app.utils.numero_generator import generer_numero_inventaire
                ic = InventoryCount(
                    count_number=generer_numero_inventaire(self.db_session),
                    warehouse_id=self.warehouse_combo.currentData(),
                    status="VALIDATED",
                    notes=self.notes_input.toPlainText(),
                    created_by=self.user.id,
                    validated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                self.db_session.add(ic)
                self.db_session.flush()

            # 2. Add items and update stock
            for item in self.line_items:
                diff = item["counted"] - item["expected"]
                self.db_session.add(InventoryCountItem(
                    inventory_count_id=ic.id,
                    product_id=item["product_id"],
                    expected_quantity=item["expected"],
                    counted_quantity=item["counted"],
                    difference=diff
                ))
                # Update actual Stock table
                stock = self.db_session.query(Stock).filter(Stock.product_id == item["product_id"]).first()
                if stock:
                    stock.quantity = item["counted"]
                else:
                    new_stock = Stock(product_id=item["product_id"], quantity=item["counted"])
                    self.db_session.add(new_stock)

            self.db_session.commit()
            QMessageBox.information(self, "Succès", "L'inventaire a été validé avec succès et le stock mis à jour.")
            self.accept()
            
        except Exception as e:
            self.db_session.rollback()
            QMessageBox.critical(self, "Erreur", str(e))


class InventoryCountPage(BaseDocumentPage):
    PAGE_TITLE = "Inventaire"
    STATUS_OPTIONS = ["Tous", "IN_PROGRESS", "VALIDATED"]

    def __init__(self, user, parent=None):
        self.db_session = get_session()
        super().__init__(user, parent)

    def _get_columns(self):
        return ["N°", "Date", "Entrepôt", "Articles", "Statut", "Actions"]

    def _load_data(self, search, status_filter):
        query = self.db_session.query(InventoryCount).order_by(InventoryCount.created_at.desc())
        if status_filter:
            query = query.filter(InventoryCount.status == status_filter)
        counts = query.all()
        if search:
            q = search.lower()
            counts = [c for c in counts if q in c.count_number.lower()]
        return [{
            "id": c.id, "N°": c.count_number, "Date": c.created_at,
            "Entrepôt": c.warehouse.name if c.warehouse else "Tous",
            "Articles": str(len(c.items)),
            "status": c.status, "_obj": c,
        } for c in counts]

    def _on_add(self):
        dlg = InventoryCountDialog(self.db_session, self.user, parent=self)
        if dlg.exec(): self.refresh_data()

    def _on_edit(self, row_data):
        ic = row_data.get("_obj")
        if ic and ic.status == "VALIDATED":
            QMessageBox.warning(self, "Erreur", "Cet inventaire a déjà été validé.")
            return
        dlg = InventoryCountDialog(self.db_session, self.user, count=ic, parent=self)
        if dlg.exec(): self.refresh_data()

    def _on_delete(self, row_data):
        ic = row_data.get("_obj")
        if not ic: return
        if ic.status == "VALIDATED":
            QMessageBox.warning(self, "Erreur", "Les inventaires validés ne peuvent pas être supprimés.")
            return
        reply = QMessageBox.question(self, "Confirmer", f"Supprimer l'inventaire {ic.count_number} ?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db_session.delete(ic)
            self.db_session.commit()
            self.refresh_data()
