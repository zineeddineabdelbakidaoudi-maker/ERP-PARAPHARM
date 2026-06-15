# -*- coding: utf-8 -*-
"""
ParaFarm ERP — Supplier Account Profile Dialog (Fiche Fournisseur)
Completely built to match the layout and features described in SECTION 9.
Redesigned to a Supplier Dashboard with unified transaction table.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame, QTableWidget, QTableWidgetItem, 
    QHeaderView, QMessageBox, QWidget, QDateEdit, QAbstractItemView, QSplitter,
    QScrollArea, QComboBox
)
from PySide6.QtPrintSupport import QPrinterInfo
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont, QBrush, QKeySequence
from PySide6.QtGui import QShortcut

from app.core.database import get_session
from app.models.supplier import Supplier
from app.models.purchase import Purchase
from app.models.debt import Debt, Payment
from app.models.supplier_return import SupplierReturn
from app.utils.pdf_exporter import PDFExporter
from ui.utils.widgets import SearchableComboBox
from ui.dialogs.view_purchase_dialog import ViewPurchaseDialog


class SupplierFicheDialog(QDialog):
    def __init__(self, user, supplier=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.selected_supplier = supplier
        initial_supplier = supplier

        self.setWindowTitle("Tableau de Bord Fournisseur (Fiche Fournisseur)")
        self.setMinimumSize(1200, 800)
        self.setWindowState(Qt.WindowMaximized)
        self.setStyleSheet("""
            QDialog { background-color: #F4F6F8; }
            QLabel { color: #2C3E50; }
            QLineEdit, QDateEdit { border: 1px solid #BDC3C7; border-radius: 4px; padding: 4px; background-color: #FFFFFF; }
            QTableWidget { background-color: #FFFFFF; border: 1px solid #BDC3C7; gridline-color: #ECF0F1; }
            QHeaderView::section { background-color: #ECF0F1; color: #2C3E50; font-weight: bold; border: 1px solid #BDC3C7; padding: 4px; }
            QFrame#card { background-color: #FFFFFF; border-radius: 6px; border: 1px solid #E0E0E0; }
            QPushButton#btnAction { background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 6px; padding: 10px; font-weight: bold; color: #34495E; text-align: left; }
            QPushButton#btnAction:hover { background-color: #F0F3F4; border: 1px solid #3498DB; }
            
            QPushButton#btnGrid { background-color: #FFFFFF; border: 1px solid #BDC3C7; border-radius: 6px; padding: 6px; font-weight: bold; color: #34495E; text-align: left; font-size: 11px; min-height: 24px; }
            QPushButton#btnGrid:hover { background-color: #F0F3F4; border: 1px solid #3498DB; }
            
            QPushButton#btnPrint { background-color: #34495E; color: white; font-weight: bold; border-radius: 4px; padding: 8px; }
            QPushButton#btnPrint:hover { background-color: #2C3E50; }
        """)

        self._setup_ui()
        self._load_suppliers()
        
        if initial_supplier:
            self.selected_supplier = initial_supplier
            for i in range(self.supplier_combo.count()):
                if self.supplier_combo.itemData(i) == self.selected_supplier.id:
                    self.supplier_combo.currentIndexChanged.disconnect(self._on_supplier_changed)
                    self.supplier_combo.setCurrentIndex(i)
                    self.supplier_combo.currentIndexChanged.connect(self._on_supplier_changed)
                    break
        
        self._update_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ── HEADER ROW ─────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setObjectName("card")
        header_frame.setMaximumHeight(100)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)

        # Supplier Selection
        supp_sel_lay = QVBoxLayout()
        supp_sel_lay.addWidget(QLabel("<b>Sélectionner un Fournisseur :</b>"))
        
        sel_h = QHBoxLayout()
        self.btn_picker = QPushButton("...")
        self.btn_picker.setFixedSize(30, 30)
        self.btn_picker.clicked.connect(self._open_picker)
        sel_h.addWidget(self.btn_picker)
        
        self.supplier_combo = SearchableComboBox()
        self.supplier_combo.setMinimumWidth(300)
        self.supplier_combo.currentIndexChanged.connect(self._on_supplier_changed)
        sel_h.addWidget(self.supplier_combo)
        supp_sel_lay.addLayout(sel_h)
        
        header_layout.addLayout(supp_sel_lay)
        header_layout.addStretch()

        # Supplier Stats Summary
        self.lbl_stats = QLabel("Sélectionnez un fournisseur pour voir les totaux.")
        self.lbl_stats.setStyleSheet("font-size: 14px; font-weight: bold; color: #2C3E50;")
        header_layout.addWidget(self.lbl_stats)
        
        main_layout.addWidget(header_frame)

        # ── MAIN SPLITTER (Table + Sidebar) ─────────────────────
        splitter = QSplitter(Qt.Horizontal)
        
        # LEFT: Transactions Table & Filters
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        filter_h = QHBoxLayout()
        filter_h.addWidget(QLabel("Du :"))
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(-3))
        self.date_start.dateChanged.connect(self._update_data)
        filter_h.addWidget(self.date_start)
        
        filter_h.addWidget(QLabel("Au :"))
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.dateChanged.connect(self._update_data)
        filter_h.addWidget(self.date_end)
        
        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.clicked.connect(self._update_data)
        filter_h.addWidget(btn_refresh)
        filter_h.addStretch()
        
        left_layout.addLayout(filter_h)
        
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Type", "Référence", "Date", "Montant Total", "Payé / Réglé", "Reste", "Statut"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        left_layout.addWidget(self.table)
        
        splitter.addWidget(left_widget)

        # RIGHT: Action Dashboard Sidebar
        right_widget = QFrame()
        right_widget.setObjectName("card")
        right_widget.setFixedWidth(280)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(10)
        
        right_layout.addWidget(QLabel("<b>Actions sur le document</b>"))
        
        self.btn_view_doc = QPushButton("👁️ Voir les détails")
        self.btn_view_doc.setObjectName("btnAction")
        self.btn_view_doc.clicked.connect(self._view_selected_document)
        right_layout.addWidget(self.btn_view_doc)
        
        self.btn_edit_doc = QPushButton("✏️ Modifier / Editer")
        self.btn_edit_doc.setObjectName("btnAction")
        self.btn_edit_doc.clicked.connect(self._edit_selected_document)
        right_layout.addWidget(self.btn_edit_doc)
        
        self.btn_print_doc = QPushButton("🖨️ Imprimer Document")
        self.btn_print_doc.setObjectName("btnAction")
        self.btn_print_doc.clicked.connect(self._print_selected_document)
        right_layout.addWidget(self.btn_print_doc)
        
        right_layout.addSpacing(15)
        
        right_layout.addWidget(QLabel("<b>Nouvelles Opérations</b>"))
        
        # Grid for compact buttons
        ops_grid = QGridLayout()
        ops_grid.setSpacing(8)
        
        self.btn_create_achat = QPushButton("Créer Achat/Réception")
        self.btn_create_achat.setObjectName("btnGrid")
        self.btn_create_achat.setMinimumHeight(30)
        self.btn_create_achat.clicked.connect(self._create_achat)
        ops_grid.addWidget(self.btn_create_achat, 0, 0, 1, 2)
        
        self.btn_create_bc = QPushButton("Créer Bon Commande Fournisseur")
        self.btn_create_bc.setObjectName("btnGrid")
        self.btn_create_bc.setMinimumHeight(30)
        self.btn_create_bc.clicked.connect(self._create_bc)
        ops_grid.addWidget(self.btn_create_bc, 1, 0, 1, 2)
        
        self.btn_create_versement = QPushButton("Créer Versement")
        self.btn_create_versement.setObjectName("btnGrid")
        self.btn_create_versement.setMinimumHeight(30)
        self.btn_create_versement.clicked.connect(self._create_versement)
        ops_grid.addWidget(self.btn_create_versement, 2, 0)
        
        self.btn_create_cheque = QPushButton("Créer Chèque")
        self.btn_create_cheque.setObjectName("btnGrid")
        self.btn_create_cheque.setMinimumHeight(30)
        self.btn_create_cheque.clicked.connect(self._create_cheque)
        ops_grid.addWidget(self.btn_create_cheque, 2, 1)
        
        self.btn_create_retour = QPushButton("Créer Retour Fournisseur")
        self.btn_create_retour.setObjectName("btnGrid")
        self.btn_create_retour.setMinimumHeight(30)
        self.btn_create_retour.clicked.connect(self._create_retour)
        ops_grid.addWidget(self.btn_create_retour, 3, 0, 1, 2)
        
        self.btn_edit_supplier = QPushButton("Modifier Fournisseur")
        self.btn_edit_supplier.setObjectName("btnGrid")
        self.btn_edit_supplier.setMinimumHeight(30)
        self.btn_edit_supplier.clicked.connect(self._edit_supplier)
        ops_grid.addWidget(self.btn_edit_supplier, 4, 0, 1, 2)
        
        right_layout.addLayout(ops_grid)
        
        right_layout.addSpacing(15)
        
        right_layout.addWidget(QLabel("<b>Impressions & Exports</b>"))
        
        self.btn_f_prod = QPushButton("🖨️ Fiche Par Produits (PDF)")
        self.btn_f_prod.setObjectName("btnPrint")
        self.btn_f_prod.clicked.connect(lambda: self._export_fiche("produits"))
        right_layout.addWidget(self.btn_f_prod)
        
        self.btn_f_bons = QPushButton("🖨️ Fiche Par Bons (PDF)")
        self.btn_f_bons.setObjectName("btnPrint")
        self.btn_f_bons.clicked.connect(lambda: self._export_fiche("bons"))
        right_layout.addWidget(self.btn_f_bons)
        
        self.btn_etat104 = QPushButton("🖨️ État 104")
        self.btn_etat104.setObjectName("btnPrint")
        self.btn_etat104.clicked.connect(self._export_etat104)
        right_layout.addWidget(self.btn_etat104)
        
        self.btn_fiche_exp = QPushButton("🖨️ Fiche d'Expédition")
        self.btn_fiche_exp.setObjectName("btnPrint")
        self.btn_fiche_exp.setStyleSheet("background-color: #E65100;") # orange to stand out
        self.btn_fiche_exp.clicked.connect(self._print_fiche_expedition)
        right_layout.addWidget(self.btn_fiche_exp)
        
        right_layout.addStretch() # Push everything up to prevent squishing
        
        # --- PRINTER SELECTION ---
        printer_layout = QHBoxLayout()
        printer_layout.addWidget(QLabel("Imprimante :"))
        self.printer_combo = QComboBox()
        self.printer_combo.addItem("Default System Printer")
        self.printer_combo.setFixedWidth(200)
        
        try:
            printers = [p.printerName() for p in QPrinterInfo.availablePrinters()]
            if printers:
                self.printer_combo.clear()
                self.printer_combo.addItems(printers)
                default_p = QPrinterInfo.defaultPrinterName()
                if default_p:
                    self.printer_combo.setCurrentText(default_p)
        except Exception:
            pass
            
        printer_layout.addWidget(self.printer_combo)
        
        self.refresh_printer_btn = QPushButton("🔄")
        self.refresh_printer_btn.setFixedSize(32, 32)
        self.refresh_printer_btn.setStyleSheet("background-color: #E0E0E0; color: black; border: 1px solid #CCC;")
        self.refresh_printer_btn.clicked.connect(self._refresh_printers)
        printer_layout.addWidget(self.refresh_printer_btn)
        
        right_layout.addLayout(printer_layout)
        
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        main_layout.addWidget(splitter)

    def _load_suppliers(self):
        self.supplier_combo.blockSignals(True)
        self.supplier_combo.clear()
        self.supplier_combo.addItem("Sélectionnez un fournisseur...", None)
        suppliers = self.db_session.query(Supplier).filter(Supplier.is_deleted == 0, Supplier.is_active == 1).order_by(Supplier.name).all()
        for s in suppliers:
            self.supplier_combo.addItem(f"{s.name} - {s.code}", s.id)
        self.supplier_combo.blockSignals(False)

    def _open_picker(self):
        from ui.dialogs.supplier_picker_dialog import SupplierPickerDialog
        dlg = SupplierPickerDialog(self.user, self)
        if dlg.exec() == QDialog.Accepted and dlg.selected_supplier:
            for i in range(self.supplier_combo.count()):
                if self.supplier_combo.itemData(i) == dlg.selected_supplier.id:
                    self.supplier_combo.setCurrentIndex(i)
                    break

    def _on_supplier_changed(self):
        idx = self.supplier_combo.currentIndex()
        if idx > 0:
            sid = self.supplier_combo.itemData(idx)
            self.selected_supplier = self.db_session.query(Supplier).get(sid)
        else:
            self.selected_supplier = None
        self._update_data()

    def _update_data(self):
        self.table.setRowCount(0)
        
        if not self.selected_supplier:
            self.lbl_stats.setText("Sélectionnez un fournisseur pour voir les totaux.")
            return

        start_dt = self.date_start.date().toString("yyyy-MM-dd") + " 00:00:00"
        end_dt = self.date_end.date().toString("yyyy-MM-dd") + " 23:59:59"

        # Fetch debts (all transactions)
        debts = self.db_session.query(Debt).filter(
            Debt.entity_type == "SUPPLIER",
            Debt.entity_id == self.selected_supplier.id,
            Debt.is_deleted == 0,
            Debt.created_at.between(start_dt, end_dt)
        ).order_by(Debt.created_at.desc()).all()
        
        from app.models.supplier_invoice import SupplierInvoice
        invoices = self.db_session.query(SupplierInvoice).filter(
            SupplierInvoice.supplier_id == self.selected_supplier.id,
            SupplierInvoice.is_deleted == 0,
            SupplierInvoice.created_at.between(start_dt, end_dt)
        ).order_by(SupplierInvoice.created_at.desc()).all()
        
        transactions = []
        for d in debts:
            transactions.append({"date": d.created_at, "type": "DEBT", "obj": d})
        for inv in invoices:
            transactions.append({"date": inv.created_at, "type": "INV", "obj": inv})
            
        transactions.sort(key=lambda x: x["date"], reverse=True)

        tot_dette = 0.0
        tot_avoir = 0.0
        
        for tx in transactions:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            if tx["type"] == "DEBT":
                d = tx["obj"]
                type_str = d.reference_type
                ref = str(d.reference_id)
                date_str = d.created_at[:10]
                montant = d.total_amount
                paye = d.paid_amount
                reste = d.remaining_amount
                
                if d.reference_type == "PURCHASE":
                    type_str = "Bon de Réception (BR)"
                    purchase = self.db_session.query(Purchase).get(d.reference_id)
                    if purchase: ref = purchase.purchase_number
                elif d.reference_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                    type_str = "Retour (Avoir)"
                    ret = self.db_session.query(SupplierReturn).get(d.reference_id)
                    if ret: 
                        ref = ret.return_number
                        montant = ret.total_amount
                elif d.reference_type == "VERSEMENT":
                    type_str = "Versement"
                    ref = f"VRS-{d.id}"
                
                role_type = d.reference_type
                role_id = d.reference_id
                
            else:
                inv = tx["obj"]
                type_str = "Facture Fournisseur"
                ref = inv.invoice_number or inv.our_reference or str(inv.id)
                date_str = inv.created_at[:10]
                montant = inv.total_ttc
                paye = 0.0
                reste = inv.total_ttc
                
                role_type = "SUPPLIER_INVOICE"
                role_id = inv.id
                
            # Set items
            item_type = QTableWidgetItem(type_str)
            item_type.setData(Qt.UserRole, (role_type, role_id))
            self.table.setItem(row, 0, item_type)
            
            self.table.setItem(row, 1, QTableWidgetItem(ref))
            self.table.setItem(row, 2, QTableWidgetItem(date_str))
            
            m_item = QTableWidgetItem(f"{abs(montant):.2f}")
            m_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, m_item)
            
            p_item = QTableWidgetItem(f"{abs(paye):.2f}")
            p_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 4, p_item)
            
            r_item = QTableWidgetItem(f"{abs(reste):.2f}")
            r_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if reste > 0 and role_type not in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                r_item.setForeground(QBrush(QColor("#C0392B")))
            self.table.setItem(row, 5, r_item)
            
            status = "Soldé" if abs(reste) < 0.01 else "Non Soldé"
            if role_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"]: status = "Avoir"
            elif role_type == "VERSEMENT": status = "Validé"
            s_item = QTableWidgetItem(status)
            if status == "Soldé": s_item.setForeground(QBrush(QColor("#27AE60")))
            self.table.setItem(row, 6, s_item)

        # Update stats
        all_debts = self.db_session.query(Debt).filter(
            Debt.entity_type == "SUPPLIER",
            Debt.entity_id == self.selected_supplier.id,
            Debt.is_deleted == 0
        ).all()
        for d in all_debts:
            if d.remaining_amount > 0:
                tot_dette += d.remaining_amount
            elif d.remaining_amount < 0:
                tot_avoir += abs(d.remaining_amount)

        net = tot_dette - tot_avoir
        if net > 0:
            self.lbl_stats.setText(f"Dette Totale : <span style='color:red;'>{net:,.2f} DA</span>".replace(",", " "))
        else:
            self.lbl_stats.setText(f"Avoir Total : <span style='color:blue;'>{abs(net):,.2f} DA</span>".replace(",", " "))

    def _on_row_double_clicked(self, item):
        self._view_selected_document()

    def _get_selected_doc_info(self):
        row = self.table.currentRow()
        if row < 0: return None, None
        return self.table.item(row, 0).data(Qt.UserRole)

    def _view_selected_document(self):
        doc_type, doc_id = self._get_selected_doc_info()
        if not doc_type: return
        
        try:
            if doc_type == "PURCHASE":
                dlg = ViewPurchaseDialog(doc_id, parent=self)
                dlg.exec()
            elif doc_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                from ui.pages.supplier_returns_page import SupplierReturnDialog
                ret = self.db_session.query(SupplierReturn).get(doc_id)
                if ret:
                    dlg = SupplierReturnDialog(self.db_session, self.user, ret=ret, parent=self)
                    dlg.exec()
            elif doc_type == "PURCHASE_ORDER":
                from ui.pages.purchase_orders_page import PurchaseOrderDialog
                from app.models.purchase_order import PurchaseOrder
                order = self.db_session.query(PurchaseOrder).get(doc_id)
                if order:
                    dlg = PurchaseOrderDialog(self.db_session, self.user, po=order, parent=self)
                    dlg.exec()
            elif doc_type == "SUPPLIER_INVOICE":
                from ui.dialogs.supplier_invoice_dialog import SupplierInvoiceDialog
                from app.models.supplier_invoice import SupplierInvoice
                inv = self.db_session.query(SupplierInvoice).get(doc_id)
                if inv:
                    dlg = SupplierInvoiceDialog(self.user, invoice=inv, parent=self)
                    dlg.exec()
            elif doc_type == "VERSEMENT":
                QMessageBox.information(self, "Versement", f"Versement ID: {doc_id}. Détails dans l'historique des paiements.")
            else:
                QMessageBox.information(self, "Info", "Vue non implémentée pour ce type de document.")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de l'ouverture du document: {str(e)}")

    def _edit_selected_document(self):
        doc_type, doc_id = self._get_selected_doc_info()
        if not doc_type or not doc_id: return
        
        try:
            if doc_type == "PURCHASE":
                QMessageBox.information(self, "Info", "L'édition d'un BR existant n'est pas supportée via le popup.")
            elif doc_type == "PURCHASE_ORDER":
                from ui.pages.purchase_orders_page import PurchaseOrderDialog
                from app.models.purchase_order import PurchaseOrder
                order = self.db_session.query(PurchaseOrder).get(doc_id)
                if order:
                    dlg = PurchaseOrderDialog(self.db_session, self.user, po=order, parent=self)
                    if dlg.exec():
                        self._update_data()
            elif doc_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                from ui.pages.supplier_returns_page import SupplierReturnDialog
                ret = self.db_session.query(SupplierReturn).get(doc_id)
                if ret:
                    if ret.status != "DRAFT":
                        QMessageBox.warning(self, "Attention", "Seuls les retours brouillon peuvent être modifiés.")
                        return
                    dlg = SupplierReturnDialog(self.db_session, self.user, ret=ret, parent=self)
                    if dlg.exec():
                        self._update_data()
            else:
                QMessageBox.information(self, "Info", "Edition non implémentée pour ce type.")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible d'éditer le document: {str(e)}")

    def _refresh_printers(self):
        try:
            printers = [p.printerName() for p in QPrinterInfo.availablePrinters()]
            if printers:
                self.printer_combo.clear()
                self.printer_combo.addItems(printers)
                default_p = QPrinterInfo.defaultPrinterName()
                if default_p:
                    self.printer_combo.setCurrentText(default_p)
                QMessageBox.information(self, "Imprimantes", "Liste des imprimantes actualisée avec succès.")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Impossible d'actualiser les imprimantes: {str(e)}")

    def _print_selected_document(self):
        doc_type, doc_id = self._get_selected_doc_info()
        if not doc_type or not doc_id:
            QMessageBox.warning(self, "Sélection requise", "Veuillez sélectionner un document dans le tableau.")
            return
            
        import os
        import tempfile
        import win32api
        
        printer_name = self.printer_combo.currentText()
        if not printer_name:
            QMessageBox.warning(self, "Imprimante", "Veuillez sélectionner une imprimante.")
            return

        temp_pdf = os.path.join(tempfile.gettempdir(), f"print_supplier_{doc_type}_{doc_id}.pdf")
        
        try:
            co_info = {"name": "ParaFarm ERP"}
            if doc_type == "PURCHASE":
                purchase = self.db_session.query(Purchase).get(doc_id)
                if not purchase: return
                QMessageBox.information(self, "Info", "Veuillez ouvrir le document pour l'imprimer.")
                return
            elif doc_type == "SUPPLIER_INVOICE":
                from app.utils.pdf_exporter import PDFExporter
                PDFExporter.export_supplier_invoice_to_pdf(temp_pdf, self.db_session, doc_id)
                win32api.ShellExecute(0, "print", temp_pdf, f'/d:"{printer_name}"', ".", 0)
                QMessageBox.information(self, "Succès", "Impression de la facture lancée.")
            else:
                QMessageBox.information(self, "Info", "Impression directe non prise en charge pour ce type de document, veuillez l'ouvrir.")
                return
        except Exception as e:
            QMessageBox.warning(self, "Erreur d'impression", f"Impossible d'imprimer : {str(e)}")

    def _export_fiche(self, fiche_type):
        if not self.selected_supplier:
            QMessageBox.warning(self, "Attention", "Veuillez d'abord sélectionner un fournisseur.")
            return

        from app.utils.pdf_exporter import PDFExporter
        from PySide6.QtWidgets import QFileDialog
        import os

        # Format default filename
        name_clean = "".join(c for c in self.selected_supplier.name if c.isalnum() or c in " _-").strip()
        default_name = f"Fiche_Fournisseur_{name_clean}_{fiche_type}.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Exporter Fiche en PDF", default_name, "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        try:
            start_d = self.date_start.date().toString("yyyy-MM-dd")
            end_d = self.date_end.date().toString("yyyy-MM-dd")
            
            PDFExporter.export_fiche_to_pdf(
                file_path=file_path,
                db_session=self.db_session,
                entity_id=self.selected_supplier.id,
                entity_type="SUPPLIER",
                start_date=start_d,
                end_date=end_d,
                is_landscape=False,
                fiche_type=fiche_type,
                cumulate=False,
                show_ref=True
            )

            reply = QMessageBox.question(
                self, "Succès",
                f"Fiche PDF générée avec succès :\\n{file_path}\\n\\nVoulez-vous l'ouvrir ?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                os.startfile(file_path)

        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export PDF :\\n{str(e)}")

    def _print_fiche_expedition(self):
        doc_type, doc_id = self._get_selected_doc_info()
        if not doc_type or not doc_id:
            QMessageBox.warning(self, "Sélection requise", "Veuillez sélectionner un document dans le tableau.")
            return
            
        if doc_type != "PURCHASE":
            QMessageBox.warning(self, "Action invalide", "La fiche d'expédition ne peut être générée qu'à partir d'un Bon de Réception (BR).")
            return
            
        try:
            import os
            from PySide6.QtWidgets import QFileDialog
            from app.utils.pdf_exporter import PDFExporter
            
            d = QFileDialog.getSaveFileName(self, "Enregistrer Fiche d'Expédition", 
                f"Fiche_Expedition_BR_{doc_id}.pdf", "PDF (*.pdf)")
            if d[0]:
                PDFExporter.export_fiche_expedition_to_pdf(
                    d[0], self.db_session, [doc_id]
                )
                QMessageBox.information(self, "Succès", "Fiche d'expédition générée avec succès.")
                os.startfile(d[0])
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", f"Impossible de générer le PDF:\\n{e}")

    def _export_etat104(self):
        if not self.selected_supplier: return
        try:
            import os
            from PySide6.QtWidgets import QFileDialog
            from app.utils.pdf_exporter import PDFExporter
            
            d = QFileDialog.getSaveFileName(self, "Enregistrer Etat 104", 
                f"Etat_104_{self.selected_supplier.name}.pdf", "PDF (*.pdf)")
            if d[0]:
                PDFExporter.export_etat104_to_pdf(
                    d[0], self.db_session, self.selected_supplier.id,
                    self.date_start.date().toString("yyyy-MM-dd"),
                    self.date_end.date().toString("yyyy-MM-dd")
                )
                QMessageBox.information(self, "Succès", "Fichier PDF généré avec succès.")
                os.startfile(d[0])
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", f"Impossible de générer le PDF:\\n{e}")

    def _create_achat(self):
        try:
            from ui.dialogs.purchase_dialog import PurchaseDialog
            dlg = PurchaseDialog(self.user, parent=self)
            if dlg.exec():
                self._update_data()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de l'ouverture du BR : {str(e)}")

    def _create_bc(self):
        try:
            from ui.pages.purchase_orders_page import PurchaseOrderDialog
            dlg = PurchaseOrderDialog(self.db_session, self.user, parent=self)
            if dlg.exec():
                self._update_data()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de l'ouverture de la Commande : {str(e)}")

    def _create_retour(self):
        try:
            from ui.pages.supplier_returns_page import SupplierReturnDialog
            dlg = SupplierReturnDialog(self.db_session, self.user, parent=self)
            # Try to pre-select supplier
            if self.selected_supplier:
                for i in range(dlg.supplier_combo.count()):
                    if dlg.supplier_combo.itemData(i) == self.selected_supplier.id:
                        dlg.supplier_combo.setCurrentIndex(i)
                        break
            if dlg.exec():
                self._update_data()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de la création du retour : {str(e)}")

    def _create_versement(self):
        if not self.selected_supplier:
            QMessageBox.warning(self, "Info", "Veuillez d'abord sélectionner un fournisseur.")
            return
        from ui.dialogs.supplier_payment_dialog import SupplierPaymentDialog
        dlg = SupplierPaymentDialog(self.user, self)
        for idx in range(dlg.supplier_combo.count()):
            if dlg.supplier_combo.itemData(idx) == self.selected_supplier.id:
                dlg.supplier_combo.setCurrentIndex(idx)
                break
        if dlg.exec():
            self._update_data()

    def _create_cheque(self):
        if not self.selected_supplier:
            QMessageBox.warning(self, "Info", "Veuillez d'abord sélectionner un fournisseur.")
            return
        from ui.dialogs.supplier_payment_dialog import SupplierPaymentDialog
        dlg = SupplierPaymentDialog(self.user, self)
        if hasattr(dlg, 'cheque_checkbox'):
            dlg.cheque_checkbox.setChecked(True)
        for idx in range(dlg.supplier_combo.count()):
            if dlg.supplier_combo.itemData(idx) == self.selected_supplier.id:
                dlg.supplier_combo.setCurrentIndex(idx)
                break
        if dlg.exec():
            self._update_data()

    def _edit_supplier(self):
        if not self.selected_supplier:
            QMessageBox.warning(self, "Info", "Veuillez d'abord sélectionner un fournisseur.")
            return
        from ui.dialogs.supplier_dialog import SupplierDialog
        dlg = SupplierDialog(self.user, self.selected_supplier, self)
        if dlg.exec():
            self._load_suppliers()
            self._update_data()
