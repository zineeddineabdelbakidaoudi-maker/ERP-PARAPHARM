# -*- coding: utf-8 -*-
"""
ParaFarm ERP — Client Account Profile Dialog (Fiche Client)
Completely built to match the layout and features described in SECTION 10.
Redesigned to a Client Dashboard with unified transaction table.
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
from app.models.client import Client
from app.models.sale import Sale
from app.models.invoice import Invoice
from app.models.debt import Debt, Payment
from app.models.credit_note import CreditNote
from app.utils.pdf_exporter import PDFExporter
from ui.utils.widgets import SearchableComboBox
from ui.dialogs.view_sale_dialog import ViewSaleDialog


class ClientFicheDialog(QDialog):
    def __init__(self, user, client=None, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.selected_client = client
        initial_client = client

        self.setWindowTitle("Tableau de Bord Client (Fiche Client)")
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
        self._load_clients()
        
        if initial_client:
            self.selected_client = initial_client
            for i in range(self.client_combo.count()):
                if self.client_combo.itemData(i) == self.selected_client.id:
                    self.client_combo.currentIndexChanged.disconnect(self._on_client_changed)
                    self.client_combo.setCurrentIndex(i)
                    self.client_combo.currentIndexChanged.connect(self._on_client_changed)
                    break
        
        self._update_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ── HEADER ROW ─────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setObjectName("card")
        header_frame.setMaximumHeight(100) # FIX: prevent it from expanding vertically
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)

        # Client Selection
        client_sel_lay = QVBoxLayout()
        client_sel_lay.addWidget(QLabel("<b>Sélectionner un Client :</b>"))
        
        sel_h = QHBoxLayout()
        self.btn_picker = QPushButton("...")
        self.btn_picker.setFixedSize(30, 30)
        self.btn_picker.clicked.connect(self._open_picker)
        sel_h.addWidget(self.btn_picker)
        
        self.client_combo = SearchableComboBox()
        self.client_combo.setMinimumWidth(300)
        self.client_combo.currentIndexChanged.connect(self._on_client_changed)
        sel_h.addWidget(self.client_combo)
        client_sel_lay.addLayout(sel_h)
        
        header_layout.addLayout(client_sel_lay)
        header_layout.addStretch()

        # Client Stats Summary
        self.lbl_stats = QLabel("Sélectionnez un client pour voir les totaux.")
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
        
        self.btn_create_doc = QPushButton("Créer Document (BL/Facture)")
        self.btn_create_doc.setObjectName("btnGrid")
        self.btn_create_doc.setMinimumHeight(30)
        self.btn_create_doc.clicked.connect(self._create_document)
        ops_grid.addWidget(self.btn_create_doc, 0, 0, 1, 2)
        
        self.btn_create_bc = QPushButton("Créer Bon Comm.")
        self.btn_create_bc.setObjectName("btnGrid")
        self.btn_create_bc.setMinimumHeight(30)
        self.btn_create_bc.clicked.connect(self._create_bc)
        ops_grid.addWidget(self.btn_create_bc, 1, 0)
        
        self.btn_create_avoir = QPushButton("Créer Avoir Client")
        self.btn_create_avoir.setObjectName("btnGrid")
        self.btn_create_avoir.setMinimumHeight(30)
        self.btn_create_avoir.clicked.connect(self._create_avoir)
        ops_grid.addWidget(self.btn_create_avoir, 1, 1)
        
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
        
        self.btn_edit_client = QPushButton("Modifier Client")
        self.btn_edit_client.setObjectName("btnGrid")
        self.btn_edit_client.setMinimumHeight(30)
        self.btn_edit_client.clicked.connect(self._edit_client)
        ops_grid.addWidget(self.btn_edit_client, 3, 0, 1, 2)
        
        right_layout.addLayout(ops_grid)
        
        right_layout.addSpacing(15)
        
        right_layout.addWidget(QLabel("<b>Impressions & Exports</b>"))
        
        self.btn_etat_creances = QPushButton("🖨️ Etat des Créances (PDF)")
        self.btn_etat_creances.setObjectName("btnPrint")
        self.btn_etat_creances.clicked.connect(self._export_etat_creances)
        right_layout.addWidget(self.btn_etat_creances)
        
        self.btn_etat104 = QPushButton("🖨️ Imprimer Etat 104")
        self.btn_etat104.setObjectName("btnPrint")
        self.btn_etat104.clicked.connect(self._export_etat104)
        right_layout.addWidget(self.btn_etat104)
        
        self.btn_annexe = QPushButton("🖨️ Imprimer Annexe")
        self.btn_annexe.setObjectName("btnPrint")
        self.btn_annexe.hide()
        right_layout.addWidget(self.btn_annexe)
        
        self.btn_fiche_exp = QPushButton("🖨️ Imprimer Fiche d'Expédition")
        self.btn_fiche_exp.setObjectName("btnPrint")
        self.btn_fiche_exp.setStyleSheet("background-color: #F39C12;") # orange to stand out
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

    def _load_clients(self):
        self.client_combo.blockSignals(True)
        self.client_combo.clear()
        self.client_combo.addItem("Sélectionnez un client...", None)
        clients = self.db_session.query(Client).filter(Client.is_deleted == 0).order_by(Client.name).all()
        for c in clients:
            self.client_combo.addItem(f"{c.name} - {c.code}", c.id)
        self.client_combo.blockSignals(False)

    def _open_picker(self):
        from ui.dialogs.client_picker_dialog import ClientPickerDialog
        dlg = ClientPickerDialog(self.user, self)
        if dlg.exec() == QDialog.Accepted and dlg.selected_client:
            for i in range(self.client_combo.count()):
                if self.client_combo.itemData(i) == dlg.selected_client.id:
                    self.client_combo.setCurrentIndex(i)
                    break

    def _on_client_changed(self):
        idx = self.client_combo.currentIndex()
        if idx > 0:
            cid = self.client_combo.itemData(idx)
            self.selected_client = self.db_session.query(Client).get(cid)
        else:
            self.selected_client = None
        self._update_data()

    def _update_data(self):
        self.table.setRowCount(0)
        
        if not self.selected_client:
            self.lbl_stats.setText("Sélectionnez un client pour voir les totaux.")
            return

        start_dt = self.date_start.date().toString("yyyy-MM-dd") + " 00:00:00"
        end_dt = self.date_end.date().toString("yyyy-MM-dd") + " 23:59:59"

        # Fetch debts (all transactions)
        debts = self.db_session.query(Debt).filter(
            Debt.entity_type == "CLIENT",
            Debt.entity_id == self.selected_client.id,
            Debt.is_deleted == 0,
            Debt.created_at.between(start_dt, end_dt)
        ).order_by(Debt.created_at.desc()).all()

        tot_dette = 0.0
        tot_avoir = 0.0
        
        for d in debts:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            type_str = d.reference_type
            ref = str(d.reference_id)
            date_str = d.created_at[:10]
            montant = d.total_amount
            paye = d.paid_amount
            reste = d.remaining_amount
            
            if d.reference_type == "SALE":
                type_str = "Bon de Livraison (BL)"
                sale = self.db_session.query(Sale).get(d.reference_id)
                if sale: ref = sale.sale_number
            elif d.reference_type == "SALE_INVOICE":
                type_str = "Facture"
                inv = self.db_session.query(Invoice).get(d.reference_id)
                if inv: ref = inv.invoice_number
            elif d.reference_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                type_str = "Retour (Avoir)"
                cn = self.db_session.query(CreditNote).get(d.reference_id)
                if cn: 
                    ref = cn.note_number or f"BR{cn.id}"
                    montant = cn.total_amount
            elif d.reference_type == "VERSEMENT":
                type_str = "Versement"
                ref = f"VRS-{d.id}"
                
            # Set items
            # Hidden role for document routing
            item_type = QTableWidgetItem(type_str)
            item_type.setData(Qt.UserRole, (d.reference_type, d.reference_id))
            self.table.setItem(row, 0, item_type)
            
            self.table.setItem(row, 1, QTableWidgetItem(ref))
            self.table.setItem(row, 2, QTableWidgetItem(date_str))
            
            m_item = QTableWidgetItem(f"{montant:.2f}")
            m_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3, m_item)
            
            p_item = QTableWidgetItem(f"{paye:.2f}")
            p_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 4, p_item)
            
            r_item = QTableWidgetItem(f"{reste:.2f}")
            r_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if reste > 0 and d.reference_type not in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                r_item.setForeground(QBrush(QColor("#C0392B")))
            self.table.setItem(row, 5, r_item)
            
            status = "Soldé" if abs(reste) < 0.01 else "Non Soldé"
            if d.reference_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"]: status = "Avoir"
            elif d.reference_type == "VERSEMENT": status = "Validé"
            s_item = QTableWidgetItem(status)
            if status == "Soldé": s_item.setForeground(QBrush(QColor("#27AE60")))
            self.table.setItem(row, 6, s_item)

        # Update stats
        all_debts = self.db_session.query(Debt).filter(
            Debt.entity_type == "CLIENT",
            Debt.entity_id == self.selected_client.id,
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
            if doc_type == "SALE":
                from ui.dialogs.view_sale_dialog import ViewSaleDialog
                dlg = ViewSaleDialog(doc_id, parent=self)
                dlg.exec()
            elif doc_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                from ui.pages.credit_notes_page import CreditNoteDialog
                from app.models.credit_note import CreditNote
                cn = self.db_session.query(CreditNote).get(doc_id)
                if cn:
                    self.db_session.refresh(cn)
                    dlg = CreditNoteDialog(self.db_session, self.user, note=cn, parent=self)
                    dlg.exec()
            elif doc_type == "SALE_ORDER":
                from ui.pages.preparations_page import PreparationDialog
                from app.models.customer_order import CustomerOrder
                order = self.db_session.query(CustomerOrder).get(doc_id)
                if order:
                    dlg = OrderDialog(self.db_session, self.user, order=order, parent=self)
                    dlg.exec()
            elif doc_type == "SALE_INVOICE":
                from ui.pages.invoices_page import InvoiceDialog
                from app.models.invoice import Invoice
                inv = self.db_session.query(Invoice).get(doc_id)
                if inv:
                    dlg = InvoiceDialog(self.db_session, self.user, invoice=inv, parent=self)
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
            if doc_type == "SALE":
                QMessageBox.information(self, "Info", "L'édition d'un BL existant n'est pas encore supportée via le popup.")
            elif doc_type == "SALE_ORDER":
                from ui.pages.preparations_page import PreparationDialog
                from app.models.customer_order import CustomerOrder
                order = self.db_session.query(CustomerOrder).get(doc_id)
                if order:
                    dlg = OrderDialog(self.db_session, self.user, order=order, parent=self)
                    if dlg.exec():
                        self._update_data()
            elif doc_type == "SALE_INVOICE":
                from ui.pages.invoices_page import InvoiceDialog
                from app.models.invoice import Invoice
                inv = self.db_session.query(Invoice).get(doc_id)
                if inv:
                    dlg = InvoiceDialog(self.db_session, self.user, invoice=inv, parent=self)
                    if dlg.exec():
                        self._update_data()
            elif doc_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                from ui.pages.credit_notes_page import CreditNoteDialog
                from app.models.credit_note import CreditNote
                cn = self.db_session.query(CreditNote).get(doc_id)
                if cn:
                    dlg = CreditNoteDialog(self.db_session, self.user, note=cn, parent=self)
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

        temp_pdf = os.path.join(tempfile.gettempdir(), f"print_{doc_type}_{doc_id}.pdf")
        
        try:
            co_info = {"name": "ParaFarm ERP"} # Mock company info
            if doc_type == "SALE":
                from app.models.sale import Sale
                sale = self.db_session.query(Sale).get(doc_id)
                if not sale: return
                PDFExporter.export_sale_to_pdf(temp_pdf, sale, sale.items, company_info=co_info)
            elif doc_type == "SALE_ORDER":
                from app.models.customer_order import CustomerOrder
                order = self.db_session.query(CustomerOrder).get(doc_id)
                if not order: return
                PDFExporter.export_order_to_pdf(temp_pdf, order, order.items, company_info=co_info)
            elif doc_type == "SALE_INVOICE":
                from app.models.invoice import Invoice
                inv = self.db_session.query(Invoice).get(doc_id)
                if not inv: return
                PDFExporter.export_invoice_to_pdf(temp_pdf, inv, inv.items, company_info=co_info)
            elif doc_type in ["SUPPLIER_RETURN", "CREDIT_NOTE"]:
                from app.models.credit_note import CreditNote
                from app.utils.pdf_exporter import PDFExporter
                cn = self.db_session.query(CreditNote).get(doc_id)
                if not cn: return
                PDFExporter.export_credit_note_to_pdf(temp_pdf, cn, cn.items, company_info=co_info)
            else:
                QMessageBox.information(self, "Info", "Impression non prise en charge pour ce type de document.")
                return
                
            # Send to printer safely
            if printer_name == "Default System Printer":
                win32api.ShellExecute(0, "print", temp_pdf, None, ".", 0)
            else:
                try:
                    win32api.ShellExecute(0, "printto", temp_pdf, f'"{printer_name}"', ".", 0)
                except Exception:
                    # Fallback to default print
                    win32api.ShellExecute(0, "print", temp_pdf, None, ".", 0)
                    
            QMessageBox.information(self, "Impression", f"Le document a été envoyé à l'imprimante : {printer_name}")
            
        except Exception as e:
            QMessageBox.warning(self, "Erreur d'impression", f"Impossible d'imprimer : {str(e)}")

    def _export_etat_creances(self):
        if not self.selected_client: return
        try:
            import os
            from PySide6.QtWidgets import QFileDialog
            from app.utils.pdf_exporter import PDFExporter
            
            d = QFileDialog.getSaveFileName(self, "Enregistrer Etat des Créances", 
                f"Etat_Creances_{self.selected_client.name}.pdf", "PDF (*.pdf)")
            if d[0]:
                PDFExporter.export_etat_creances_to_pdf(
                    d[0], self.db_session, self.selected_client.id,
                    self.date_start.date().toString("yyyy-MM-dd"),
                    self.date_end.date().toString("yyyy-MM-dd")
                )
                QMessageBox.information(self, "Succès", "Fichier PDF généré avec succès.")
                os.startfile(d[0])
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", f"Impossible de générer le PDF:\\n{e}")

    def _print_fiche_expedition(self):
        doc_type, doc_id = self._get_selected_doc_info()
        if not doc_type or not doc_id:
            QMessageBox.warning(self, "Sélection requise", "Veuillez sélectionner un document dans le tableau.")
            return
            
        if doc_type != "SALE":
            QMessageBox.warning(self, "Action invalide", "La fiche d'expédition ne peut être générée qu'à partir d'un Bon de Livraison.")
            return
            
        try:
            import os
            from PySide6.QtWidgets import QFileDialog
            from app.utils.pdf_exporter import PDFExporter
            
            d = QFileDialog.getSaveFileName(self, "Enregistrer Fiche d'Expédition", 
                f"Fiche_Expedition_BL_{doc_id}.pdf", "PDF (*.pdf)")
            if d[0]:
                PDFExporter.export_fiche_expedition_to_pdf(
                    d[0], self.db_session, [doc_id]
                )
                QMessageBox.information(self, "Succès", "Fiche d'expédition générée avec succès.")
                os.startfile(d[0])
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", f"Impossible de générer le PDF:\\n{e}")

    def _export_etat104(self):
        if not self.selected_client: return
        try:
            import os
            from PySide6.QtWidgets import QFileDialog
            from app.utils.pdf_exporter import PDFExporter
            
            d = QFileDialog.getSaveFileName(self, "Enregistrer Etat 104", 
                f"Etat_104_{self.selected_client.name}.pdf", "PDF (*.pdf)")
            if d[0]:
                PDFExporter.export_etat104_to_pdf(
                    d[0], self.db_session, self.selected_client.id,
                    self.date_start.date().toString("yyyy-MM-dd"),
                    self.date_end.date().toString("yyyy-MM-dd")
                )
                QMessageBox.information(self, "Succès", "Fichier PDF généré avec succès.")
                os.startfile(d[0])
        except Exception as e:
            QMessageBox.critical(self, "Erreur PDF", f"Impossible de générer le PDF:\\n{e}")

    def _navigate_to_page(self, page_key):
        parent = self.parentWidget()
        while parent:
            if hasattr(parent, '_navigate_to'):
                parent._navigate_to(page_key)
                self.accept()
                return True
            parent = parent.parentWidget()
        return False

    def _create_document(self):
        try:
            if not self.selected_client:
                QMessageBox.warning(self, "Info", "Veuillez d'abord sélectionner un client.")
                return
            from ui.dialogs.client_document_creation_dialog import ClientDocumentCreationDialog
            dlg = ClientDocumentCreationDialog(self.user, self.selected_client, parent=self)
            if dlg.exec():
                self._update_data()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de l'ouverture du document : {str(e)}")

    def _create_bc(self):
        try:
            from ui.pages.preparations_page import PreparationDialog
            dlg = PreparationDialog(self.db_session, self.user, parent=self)
            if dlg.exec():
                self._update_data()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", f"Erreur lors de l'ouverture de la Commande : {str(e)}")

    def _create_avoir(self):
        try:
            from ui.pages.credit_notes_page import CreditNoteDialog
            dlg = CreditNoteDialog(self.db_session, self.user, parent=self)
            if dlg.exec():
                self._update_data()
        except Exception as e:
            QMessageBox.information(self, "Action", "L'édition de l'avoir se fait via la page Avoirs Client.")

    def _create_versement(self):
        if not self.selected_client:
            QMessageBox.warning(self, "Info", "Veuillez d'abord sélectionner un client.")
            return
        from ui.dialogs.client_payment_dialog import ClientPaymentDialog
        dlg = ClientPaymentDialog(self.user, self)
        for idx in range(dlg.client_combo.count()):
            if dlg.client_combo.itemData(idx) == self.selected_client.id:
                dlg.client_combo.setCurrentIndex(idx)
                break
        if dlg.exec():
            self._update_data()

    def _create_cheque(self):
        if not self.selected_client:
            QMessageBox.warning(self, "Info", "Veuillez d'abord sélectionner un client.")
            return
        from ui.dialogs.client_payment_dialog import ClientPaymentDialog
        dlg = ClientPaymentDialog(self.user, self)
        dlg.cheque_checkbox.setChecked(True)
        for idx in range(dlg.client_combo.count()):
            if dlg.client_combo.itemData(idx) == self.selected_client.id:
                dlg.client_combo.setCurrentIndex(idx)
                break
        if dlg.exec():
            self._update_data()

    def _edit_client(self):
        if not self.selected_client:
            QMessageBox.warning(self, "Info", "Veuillez d'abord sélectionner un client.")
            return
        from ui.dialogs.client_dialog import ClientDialog
        dlg = ClientDialog(self.user, self.selected_client, self)
        if dlg.exec():
            self._load_clients()
            self._update_data()

    def _not_implemented(self):
        QMessageBox.information(self, "Info", "Cette fonctionnalité n'est pas encore implémentée.")
