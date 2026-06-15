# -*- coding: utf-8 -*-
import json
import csv
import tempfile
import os
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QSpinBox, QFrame, QFileDialog, QLineEdit, QDialog, QFormLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from app.core.database import get_session
from app.models.invoice import Invoice
from app.models.client import Client
from app.models.purchase import Purchase
from app.models.debt import Debt
from app.models.fiscal import ExonerationTVA
from app.utils.pdf_exporter import FiscalPDFExporter

def format_money(val):
    try:
        return f"{float(val):,.2f} DA".replace(",", " ")
    except:
        return "0.00 DA"

class BaseFiscalPage(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(16)
        
    def create_header(self, title_text):
        header = QHBoxLayout()
        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.main_layout.addLayout(header)
        
    def create_table(self, columns):
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        return table
        
    def export_csv(self, table, default_name):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter CSV", f"{default_name}.csv", "Fichiers CSV (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
                    writer.writerow(headers)
                    for row in range(table.rowCount()):
                        row_data = []
                        for col in range(table.columnCount()):
                            item = table.item(row, col)
                            row_data.append(item.text() if item else "")
                        writer.writerow(row_data)
                QMessageBox.information(self, "Succès", "Export CSV réussi.")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de l'export CSV : {e}")

class Etat104Page(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("État 104 — Registre des Ventes")
        
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Période :"))
        self.month_combo = QComboBox()
        self.month_combo.addItems([f"{i:02d}" for i in range(1, 13)])
        self.month_combo.setCurrentText(f"{datetime.now().month:02d}")
        toolbar.addWidget(self.month_combo)
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(datetime.now().year)
        toolbar.addWidget(self.year_spin)
        
        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.clicked.connect(self.load_data)
        toolbar.addWidget(btn_refresh)
        
        toolbar.addStretch()
        
        btn_pdf = QPushButton("📄 Exporter PDF")
        btn_pdf.clicked.connect(self.export_pdf)
        toolbar.addWidget(btn_pdf)
        
        btn_csv = QPushButton("📊 Exporter CSV")
        btn_csv.clicked.connect(lambda: self.export_csv(self.table, "Etat104"))
        toolbar.addWidget(btn_csv)
        
        self.main_layout.addLayout(toolbar)
        
        self.table = self.create_table(["Désignation", "Base Imposable HT", "Taux TVA", "Montant TVA", "Observations"])
        self.main_layout.addWidget(self.table)
        self.load_data()

    def load_data(self):
        m = self.month_combo.currentText()
        y = str(self.year_spin.value())
        prefix = f"{y}-{m}"
        
        invs = self.db_session.query(Invoice).filter(
            Invoice.created_at.like(f"{prefix}%"),
            Invoice.status != 'CANCELLED'
        ).all()
        from app.models.credit_note import CreditNote
        cns = self.db_session.query(CreditNote).filter(
            CreditNote.created_at.like(f"{prefix}%"),
            CreditNote.status != 'CANCELLED'
        ).all()
        
        ht_19 = ht_9 = ht_exo = avoirs = tva_19 = tva_9 = 0.0
        
        for inv in invs:
            if inv.subtotal < 0:
                avoirs += inv.subtotal
            else:
                for item in inv.items:
                    tr = item.tax_rate
                    tht = item.quantity * item.unit_price / (1 + tr/100.0)
                    ttva = tht * (tr/100.0)
                    
                    if tr == 19.0:
                        ht_19 += tht
                        tva_19 += ttva
                    elif tr == 9.0:
                        ht_9 += tht
                        tva_9 += ttva
                    else:
                        ht_exo += tht
                        
        self.table.setRowCount(0)
        def add_row(desig, base, taux, tva, obs="", color=None):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(desig))
            self.table.setItem(r, 1, QTableWidgetItem(format_money(base)))
            self.table.setItem(r, 2, QTableWidgetItem(taux))
            self.table.setItem(r, 3, QTableWidgetItem(format_money(tva)))
            self.table.setItem(r, 4, QTableWidgetItem(obs))
            if color:
                for c in range(5):
                    self.table.item(r, c).setForeground(QBrush(QColor(color)))
        
        add_row("Ventes locales soumises à TVA 19%", ht_19, "19%", tva_19)
        add_row("Ventes locales soumises à TVA 9%", ht_9, "9%", tva_9)
        add_row("Ventes exonérées de TVA", ht_exo, "0%", 0)
        add_row("Avoirs émis (Déduction)", avoirs, "", 0, "Avoirs", "#B71C1C")
        
        ca_brut = ht_19 + ht_9 + ht_exo + avoirs
        add_row("TOTAL CA Brut", ca_brut, "", tva_19 + tva_9, "", "#1B5E20")
        
        for c in range(5):
            self.table.item(4, c).setFont(QFont("Segoe UI", 10, QFont.Bold))

    def export_pdf(self):
        headers = []
        for j in range(self.table.columnCount()):
            headers.append(self.table.horizontalHeaderItem(j).text())
            
        data = []
        for i in range(self.table.rowCount()):
            row = []
            for j in range(self.table.columnCount()):
                item = self.table.item(i, j)
                row.append(item.text() if item else "")
            data.append(row)
            
        pdf_path = os.path.join(tempfile.gettempdir(), f"etat_104_{self.month_combo.currentText()}_{self.year_spin.value()}.pdf")
        period_str = f"{self.month_combo.currentText()} / {self.year_spin.value()}"
        
        try:
            from app.config import config
            co = {
                "name": config.company_name,
                "address": config.company_address,
                "nif": config.company_nif,
                "nis": config.company_nis,
                "rc": config.company_rc,
                "ai": config.company_ai,
            }
            FiscalPDFExporter.export_etat_104_pdf(pdf_path, period_str, data, company_info=co)
            import win32api
            win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de l'impression: {str(e)}")

class Annexe5Page(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Annexe 5 — Détail des Factures")
        
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Période :"))
        self.trimestre_combo = QComboBox()
        self.trimestre_combo.addItems(['Trimestre 1', 'Trimestre 2', 'Trimestre 3', 'Trimestre 4', 'Année Entière'])
        toolbar.addWidget(self.trimestre_combo)
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(datetime.now().year)
        toolbar.addWidget(self.year_spin)
        
        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.clicked.connect(self.load_data)
        toolbar.addWidget(btn_refresh)
        
        toolbar.addStretch()
        btn_pdf = QPushButton("📄 Exporter PDF")
        btn_pdf.clicked.connect(self.export_pdf)
        toolbar.addWidget(btn_pdf)
        self.main_layout.addLayout(toolbar)
        
        self.table = self.create_table(["N° Facture", "Date", "NIF Client", "Nom Client", "Montant HT", "TVA", "Montant TTC", "RC Client"])
        self.main_layout.addWidget(self.table)
        self.load_data()

    def load_data(self):
        y = self.year_spin.value()
        trim_idx = self.trimestre_combo.currentIndex()
        if trim_idx == 4:
            prefix_start = f"{y}-01-01"
            prefix_end = f"{y}-12-31"
        else:
            m_start = trim_idx * 3 + 1
            m_end = m_start + 2
            import calendar
            last_day = calendar.monthrange(y, m_end)[1]
            prefix_start = f"{y}-{m_start:02d}-01"
            prefix_end = f"{y}-{m_end:02d}-{last_day}"
        
        invs = self.db_session.query(Invoice).filter(
            Invoice.created_at >= prefix_start,
            Invoice.created_at <= prefix_end + ' 23:59:59',
            Invoice.status != 'CANCELLED'
        ).all()
        from app.models.credit_note import CreditNote
        cns = self.db_session.query(CreditNote).filter(
            CreditNote.created_at >= prefix_start,
            CreditNote.created_at <= prefix_end + ' 23:59:59',
            CreditNote.status != 'CANCELLED'
        ).all()
        
        self.table.setRowCount(0)
        tot_ht = tot_tva = tot_ttc = 0.0
        
        for inv in invs:
            r = self.table.rowCount()
            self.table.insertRow(r)
            cli = inv.client
            nif = cli.tax_id if cli else "⚠️ NIF Manquant"
            if not nif: nif = "⚠️ NIF Manquant"
            nom = cli.name if cli else "Client Comptoir"
            rc = cli.commercial_register if cli else ""
            
            ht = inv.subtotal
            tva = inv.tax_total
            ttc = inv.total_amount
            
            tot_ht += ht
            tot_tva += tva
            tot_ttc += ttc
            
            self.table.setItem(r, 0, QTableWidgetItem(inv.invoice_number))
            self.table.setItem(r, 1, QTableWidgetItem(inv.created_at[:10]))
            self.table.setItem(r, 2, QTableWidgetItem(nif))
            self.table.setItem(r, 3, QTableWidgetItem(nom))
            self.table.setItem(r, 4, QTableWidgetItem(format_money(ht)))
            self.table.setItem(r, 5, QTableWidgetItem(format_money(tva)))
            self.table.setItem(r, 6, QTableWidgetItem(format_money(ttc)))
            self.table.setItem(r, 7, QTableWidgetItem(rc))
            
        for cn in cns:
            r = self.table.rowCount()
            self.table.insertRow(r)
            cli = cn.client
            nif = cli.tax_id if cli else "⚠️ NIF Manquant"
            if not nif: nif = "⚠️ NIF Manquant"
            nom = cli.name if cli else "Client Comptoir"
            rc = cli.commercial_register if cli else ""
            
            ht = cn.total_amount / 1.19
            tva = cn.total_amount - ht
            ttc = cn.total_amount
            
            tot_ht -= ht
            tot_tva -= tva
            tot_ttc -= ttc
            
            self.table.setItem(r, 0, QTableWidgetItem(cn.note_number))
            self.table.setItem(r, 1, QTableWidgetItem(cn.created_at[:10]))
            self.table.setItem(r, 2, QTableWidgetItem(nif))
            self.table.setItem(r, 3, QTableWidgetItem(nom))
            self.table.setItem(r, 4, QTableWidgetItem(format_money(-ht)))
            self.table.setItem(r, 5, QTableWidgetItem(format_money(-tva)))
            self.table.setItem(r, 6, QTableWidgetItem(format_money(-ttc)))
            self.table.setItem(r, 7, QTableWidgetItem(rc))
            for c in range(8):
                self.table.item(r, c).setForeground(QBrush(QColor("#B71C1C")))
                    
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem("TOTAL"))
        self.table.setItem(r, 4, QTableWidgetItem(format_money(tot_ht)))
        self.table.setItem(r, 5, QTableWidgetItem(format_money(tot_tva)))
        self.table.setItem(r, 6, QTableWidgetItem(format_money(tot_ttc)))
        for c in [0, 4, 5, 6]:
            self.table.item(r, c).setFont(QFont("Segoe UI", 10, QFont.Bold))

    def export_pdf(self):
        data = []
        for i in range(self.table.rowCount()):
            row = []
            for j in range(self.table.columnCount()):
                item = self.table.item(i, j)
                row.append(item.text() if item else "")
            data.append(row)
            
        pdf_path = os.path.join(tempfile.gettempdir(), f"annexe_5_{self.trimestre_combo.currentText()}_{self.year_spin.value()}.pdf")
        period_str = f"{self.trimestre_combo.currentText()} / {self.year_spin.value()}"
        try:
            from app.config import config
            co = {
                "name": config.company_name,
                "address": config.company_address,
                "nif": config.company_nif,
                "nis": config.company_nis,
                "rc": config.company_rc,
                "ai": config.company_ai,
            }
            FiscalPDFExporter.export_annexe_5_pdf(pdf_path, period_str, data, company_info=co)
            import win32api
            win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

class DeclarationG50Page(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Déclaration Mensuelle (G50)")
        
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Trimestre :"))
        self.trimestre_combo = QComboBox()
        self.trimestre_combo.addItems(['Trimestre 1', 'Trimestre 2', 'Trimestre 3', 'Trimestre 4'])
        toolbar.addWidget(self.trimestre_combo)
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(datetime.now().year)
        toolbar.addWidget(self.year_spin)
        
        btn_refresh = QPushButton("🔄 Calculer")
        btn_refresh.clicked.connect(self.load_data)
        toolbar.addWidget(btn_refresh)
        
        toolbar.addStretch()
        btn_pdf = QPushButton("📄 Exporter G50 PDF")
        btn_pdf.clicked.connect(self.export_pdf)
        toolbar.addWidget(btn_pdf)
        self.main_layout.addLayout(toolbar)
        
        self.table = self.create_table(["Désignation", "Montant (DA)"])
        self.main_layout.addWidget(self.table)
        self.g50_data = {}
        self.load_data()

    def load_data(self):
        y = self.year_spin.value()
        trim_idx = self.trimestre_combo.currentIndex()
        m_start = trim_idx * 3 + 1
        m_end = m_start + 2
        import calendar
        last_day = calendar.monthrange(y, m_end)[1]
        prefix_start = f"{y}-{m_start:02d}-01"
        prefix_end = f"{y}-{m_end:02d}-{last_day}"
        
        invs = self.db_session.query(Invoice).filter(
            Invoice.created_at >= prefix_start,
            Invoice.created_at <= prefix_end + ' 23:59:59',
            Invoice.status != 'CANCELLED'
        ).all()
        from app.models.credit_note import CreditNote
        cns = self.db_session.query(CreditNote).filter(
            CreditNote.created_at >= prefix_start,
            CreditNote.created_at <= prefix_end + ' 23:59:59',
            CreditNote.status != 'CANCELLED'
        ).all()
        
        purchases = self.db_session.query(Purchase).filter(
            Purchase.created_at >= prefix_start,
            Purchase.created_at <= prefix_end + ' 23:59:59',
            Purchase.status != 'CANCELLED'
        ).all()
        from app.models.delivery import Delivery
        deliveries = self.db_session.query(Delivery).filter(
            Delivery.type == 'RECEIPT',
            Delivery.created_at >= prefix_start,
            Delivery.created_at <= prefix_end + ' 23:59:59',
            Delivery.status != 'CANCELLED'
        ).all()
        
        ca_ht = 0.0
        exo_ht = 0.0
        tva_19 = 0.0
        tva_9 = 0.0
        for inv in invs:
            ca_ht += inv.subtotal
            for item in inv.items:
                tr = item.tax_rate
                if tr == 0: exo_ht += (item.quantity * item.unit_price)
                ttva = (item.quantity * item.unit_price / (1 + tr/100.0)) * (tr/100.0)
                if tr == 19.0: tva_19 += ttva
                elif tr == 9.0: tva_9 += ttva
                
        tva_deduc = sum(p.tax_total for p in purchases)
        for d in deliveries:
            for item in d.items:
                tva_deduc += (item.quantity * item.unit_price) * (getattr(item.product, 'tax_rate', 19.0) or 19.0)/100.0
        
        tap = (ca_ht - exo_ht) * 0.02
        tva_coll = tva_19 + tva_9
        credit_tva = max(0, tva_deduc - tva_coll)
        tva_nette = max(0, tva_coll - tva_deduc)
        total_g50 = tap + tva_nette
        
        self.g50_data = {
            'ca_ht': format_money(ca_ht),
            'tap': format_money(tap),
            'tva_19': format_money(tva_19),
            'tva_9': format_money(tva_9),
            'tva_coll': format_money(tva_coll),
            'tva_deduc': format_money(tva_deduc),
            'tva_nette': format_money(tva_nette),
            'credit_tva': format_money(credit_tva),
            'total': format_money(total_g50)
            }
        
        self.table.setRowCount(0)
        for k, lbl in [('ca_ht', "Chiffre d'Affaires Imposable (HT)"), ('tap', 'TAP (2%)'), 
                       ('tva_19', 'TVA Collectée (19%)'), ('tva_9', 'TVA Collectée (9%)'), 
                       ('tva_deduc', 'TVA Déductible (Achats)'), ('tva_nette', 'TVA Nette à Payer'), 
                       ('credit_tva', 'Crédit de TVA (à reporter)'), 
                       ('total', 'TOTAL G50 À PAYER')]:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(lbl))
            self.table.setItem(r, 1, QTableWidgetItem(self.g50_data.get(k, "0.00")))
            if k == 'total':
                self.table.item(r, 0).setFont(QFont("Segoe UI", 10, QFont.Bold))
                self.table.item(r, 1).setFont(QFont("Segoe UI", 10, QFont.Bold))

    def export_pdf(self):
        pdf_path = os.path.join(tempfile.gettempdir(), f"g50_{self.trimestre_combo.currentText()}_{self.year_spin.value()}.pdf")
        period_str = f"{self.trimestre_combo.currentText()} / {self.year_spin.value()}"
        try:
            from app.config import config
            co = {
                "name": config.company_name,
                "address": config.company_address,
                "nif": config.company_nif,
                "nis": config.company_nis,
                "rc": config.company_rc,
                "ai": config.company_ai,
            }
            FiscalPDFExporter.export_g50_pdf(pdf_path, period_str, self.g50_data, company_info=co)
            import win32api
            win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

class DeclarationG12Page(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Déclaration Annuelle (G12 - IFU)")
        
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Année :"))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(datetime.now().year)
        toolbar.addWidget(self.year_spin)
        
        toolbar.addWidget(QLabel("Acomptes G50 versés :"))
        self.acomptes_input = QLineEdit("0.00")
        self.acomptes_input.setFixedWidth(100)
        self.acomptes_input.textChanged.connect(self.load_data)
        toolbar.addWidget(self.acomptes_input)
        
        btn_refresh = QPushButton("🔄 Calculer")
        btn_refresh.clicked.connect(self.load_data)
        toolbar.addWidget(btn_refresh)
        
        toolbar.addStretch()
        btn_pdf = QPushButton("📄 Exporter G12 PDF")
        btn_pdf.clicked.connect(self.export_pdf)
        toolbar.addWidget(btn_pdf)
        self.main_layout.addLayout(toolbar)
        
        self.table = self.create_table(["Désignation", "Montant (DA)"])
        self.main_layout.addWidget(self.table)
        self.g12_data = {}
        self.load_data()

    def load_data(self):
        y = str(self.year_spin.value())
        invs = self.db_session.query(Invoice).filter(
            Invoice.created_at.like(f"{y}-%"),
            Invoice.status != 'CANCELLED'
        ).all()
        
        ca_brut = 0.0
        deduc = 0.0
        for inv in invs:
            if inv.subtotal < 0:
                deduc += abs(inv.subtotal)
            else:
                ca_brut += inv.subtotal
                
        ca_net = ca_brut - deduc
        ifu = ca_net * 0.05
        try:
            acomptes = float(self.acomptes_input.text().replace(',', '.'))
        except: acomptes = 0.0
        solde = max(0, ifu - acomptes)
        
        self.g12_data = {
            'ca_brut': format_money(ca_brut),
            'deductions': format_money(deduc),
            'ca_net': format_money(ca_net),
            'ifu_calc': format_money(ifu),
            'acomptes': format_money(acomptes),
            'solde': format_money(solde)
            }
        
        self.table.setRowCount(0)
        for k, lbl in [('ca_brut', 'CA Brut HT'), ('deductions', 'Avoirs / Déductions'), 
                       ('ca_net', 'CA Net Imposable'), ('ifu_calc', 'IFU (5%)'), 
                       ('acomptes', 'Acomptes Versés'), ('solde', 'SOLDE À PAYER')]:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(lbl))
            self.table.setItem(r, 1, QTableWidgetItem(self.g12_data[k]))
            if k in ['ca_net', 'solde']:
                self.table.item(r, 0).setFont(QFont("Segoe UI", 10, QFont.Bold))
                self.table.item(r, 1).setFont(QFont("Segoe UI", 10, QFont.Bold))

    def export_pdf(self):
        pdf_path = os.path.join(tempfile.gettempdir(), f"g12_{self.year_spin.value()}.pdf")
        try:
            from app.config import config
            co = {
                "name": config.company_name,
                "address": config.company_address,
                "nif": config.company_nif,
                "nis": config.company_nis,
                "rc": config.company_rc,
                "ai": config.company_ai,
            }
            FiscalPDFExporter.export_g12_pdf(pdf_path, str(self.year_spin.value()), self.g12_data, company_info=co)
            import win32api
            win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

class DeclarationG12ComplementairePage(DeclarationG12Page):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.main_layout.takeAt(0).widget().setText("G12 Complémentaire")
        
        form = QFormLayout()
        self.motif_input = QLineEdit()
        self.periode_input = QLineEdit()
        self.diff_input = QLineEdit("0.00")
        form.addRow("Motif de rectification :", self.motif_input)
        form.addRow("Période rectifiée :", self.periode_input)
        form.addRow("Différentiel IFU (DA) :", self.diff_input)
        
        f_widget = QWidget()
        f_widget.setLayout(form)
        self.main_layout.insertWidget(2, f_widget)

    def export_pdf(self):
        self.g12_data['motif'] = self.motif_input.text()
        self.g12_data['periode_rect'] = self.periode_input.text()
        self.g12_data['diff'] = f"{float(self.diff_input.text() or 0):,.2f} DA".replace(",", " ")
        
        pdf_path = os.path.join(tempfile.gettempdir(), f"g12_comp_{self.year_spin.value()}.pdf")
        try:
            from app.config import config
            co = {
                "name": config.company_name,
                "address": config.company_address,
                "nif": config.company_nif,
                "nis": config.company_nis,
                "rc": config.company_rc,
                "ai": config.company_ai,
            }
            FiscalPDFExporter.export_g12_pdf(pdf_path, str(self.year_spin.value()), self.g12_data, is_comp=True, company_info=co)
            import win32api
            win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

class DemandesExonerationTVAPage(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Exonérations TVA")
        
        toolbar = QHBoxLayout()
        btn_add = QPushButton("➕ Ajouter Exonération")
        btn_add.clicked.connect(self._add_exo)
        toolbar.addWidget(btn_add)
        toolbar.addStretch()
        self.main_layout.addLayout(toolbar)
        
        self.table = self.create_table(["Client", "NIF", "Motif", "N° Décision", "Date Début", "Date Fin", "Montant Plafonné", "Consommé HT"])
        self.main_layout.addWidget(self.table)
        self.load_data()

    def _add_exo(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Ajouter Exonération")
        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        
        cb_client = QComboBox()
        for c in self.db_session.query(Client).all():
            cb_client.addItem(c.name, c.id)
            
        inp_motif = QLineEdit()
        inp_num = QLineEdit()
        inp_date = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        inp_date_fin = QLineEdit(datetime.now().strftime("%Y-12-31"))
        inp_plafond = QLineEdit("0.00")
        inp_montant = QLineEdit("0.00")
        
        form.addRow("Client :", cb_client)
        form.addRow("Motif :", inp_motif)
        form.addRow("N° Décision :", inp_num)
        form.addRow("Date Début :", inp_date)
        form.addRow("Date Fin :", inp_date_fin)
        form.addRow("Montant Plafonné :", inp_plafond)
        form.addRow("Consommé HT :", inp_montant)
        layout.addLayout(form)
        
        btn_box = QHBoxLayout()
        btn_save = QPushButton("Enregistrer")
        btn_save.clicked.connect(dlg.accept)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)
        
        if dlg.exec():
            exo = ExonerationTVA(
                client_id=cb_client.currentData(),
                motif=inp_motif.text(),
                num_decision=inp_num.text(),
                date_decision=inp_date.text(),
                date_fin=inp_date_fin.text(),
                montant_plafonne=float(inp_plafond.text() or 0),
                montant_ht=float(inp_montant.text() or 0),
                periode=datetime.now().strftime("%Y")
            )
            self.db_session.add(exo)
            self.db_session.commit()
            self.load_data()

    def load_data(self):
        self.table.setRowCount(0)
        for exo in self.db_session.query(ExonerationTVA).all():
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(exo.client.name))
            self.table.setItem(r, 1, QTableWidgetItem(exo.client.tax_id or ""))
            self.table.setItem(r, 2, QTableWidgetItem(exo.motif))
            self.table.setItem(r, 3, QTableWidgetItem(exo.num_decision))
            self.table.setItem(r, 4, QTableWidgetItem(exo.date_decision))
            self.table.setItem(r, 5, QTableWidgetItem(exo.date_fin))
            self.table.setItem(r, 6, QTableWidgetItem(format_money(exo.montant_plafonne)))
            self.table.setItem(r, 7, QTableWidgetItem(format_money(exo.montant_ht)))

class ChiffreAffaireFiscalPage(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Chiffre d'Affaire Fiscal")
        
        toolbar = QHBoxLayout()
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(datetime.now().year)
        self.year_spin.valueChanged.connect(self.load_data)
        toolbar.addWidget(QLabel("Année :"))
        toolbar.addWidget(self.year_spin)
        toolbar.addStretch()
        self.main_layout.addLayout(toolbar)
        
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.main_layout.addWidget(self.canvas)
        
        self.table = self.create_table(["Mois", "Ventes HT", "Avoirs", "CA Net", "TVA Collectée", "TAP (2%)", "IFU estimé (5%)"])
        self.main_layout.addWidget(self.table)
        self.load_data()

    def load_data(self):
        y = str(self.year_spin.value())
        y_prev = str(self.year_spin.value() - 1)
        self.table.setRowCount(0)
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        months = []
        ca_nets_current = []
        ca_nets_prev = []
        
        for i in range(1, 13):
            m = f"{i:02d}"
            
            # Current year
            prefix = f"{y}-{m}"
            invs = self.db_session.query(Invoice).filter(
                Invoice.created_at.like(f"{prefix}%"),
                Invoice.status != 'CANCELLED'
            ).all()
            
            ht = avoirs = tva = 0.0
            for inv in invs:
                if inv.subtotal < 0: avoirs += inv.subtotal
                else:
                    ht += inv.subtotal
                    tva += inv.tax_total
                    
            net_current = ht + avoirs
            tap = net_current * 0.02
            ifu = net_current * 0.05
            
            months.append(m)
            ca_nets_current.append(net_current)
            
            # Previous year
            prefix_prev = f"{y_prev}-{m}"
            invs_prev = self.db_session.query(Invoice).filter(
                Invoice.created_at.like(f"{prefix_prev}%"),
                Invoice.status != 'CANCELLED'
            ).all()
            ht_p = avoirs_p = 0.0
            for inv in invs_prev:
                if inv.subtotal < 0: avoirs_p += inv.subtotal
                else: ht_p += inv.subtotal
            net_prev = ht_p + avoirs_p
            ca_nets_prev.append(net_prev)
            
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(f"{m}/{y}"))
            self.table.setItem(r, 1, QTableWidgetItem(format_money(ht)))
            self.table.setItem(r, 2, QTableWidgetItem(format_money(avoirs)))
            self.table.setItem(r, 3, QTableWidgetItem(format_money(net_current)))
            self.table.setItem(r, 4, QTableWidgetItem(format_money(tva)))
            self.table.setItem(r, 5, QTableWidgetItem(format_money(tap)))
            self.table.setItem(r, 6, QTableWidgetItem(format_money(ifu)))
            
        import numpy as np
        x = np.arange(len(months))
        width = 0.35
        
        ax.bar(x - width/2, ca_nets_prev, width, label=y_prev, color='#90CAF9')
        ax.bar(x + width/2, ca_nets_current, width, label=y, color='#1565C0')
        
        ax.set_ylabel("CA Net HT (DA)")
        ax.set_title(f"Évolution CA {y_prev} vs {y}")
        ax.set_xticks(x)
        ax.set_xticklabels(months)
        ax.legend()
        self.figure.tight_layout()
        self.canvas.draw()

class FicheClientFiscalPage(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Fiche Client Fiscale")
        
        toolbar = QHBoxLayout()
        self.client_combo = QComboBox()
        self.client_combo.currentIndexChanged.connect(self.load_data)
        toolbar.addWidget(QLabel("Client :"))
        toolbar.addWidget(self.client_combo)
        toolbar.addStretch()
        
        btn_pdf = QPushButton("📄 Fiche PDF")
        btn_pdf.clicked.connect(self.export_pdf)
        toolbar.addWidget(btn_pdf)
        self.main_layout.addLayout(toolbar)
        
        self.table = self.create_table(["N° Facture", "Date", "Montant HT", "TVA", "Montant TTC", "Statut"])
        self.main_layout.addWidget(self.table)
        
        for c in self.db_session.query(Client).order_by(Client.name).all():
            self.client_combo.addItem(c.name, c.id)

    def load_data(self):
        client_id = self.client_combo.currentData()
        if not client_id: return
        
        self.table.setRowCount(0)
        invs = self.db_session.query(Invoice).filter(Invoice.client_id == client_id).all()
        from app.models.credit_note import CreditNote
        cns = self.db_session.query(CreditNote).filter(CreditNote.client_id == client_id).all()
        
        total_ttc = total_ht = total_tva = 0.0
        for inv in invs:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(inv.invoice_number))
            self.table.setItem(r, 1, QTableWidgetItem(inv.created_at[:10]))
            self.table.setItem(r, 2, QTableWidgetItem(format_money(inv.subtotal)))
            self.table.setItem(r, 3, QTableWidgetItem(format_money(inv.tax_total)))
            self.table.setItem(r, 4, QTableWidgetItem(format_money(inv.total_amount)))
            self.table.setItem(r, 5, QTableWidgetItem(inv.status))
            
            total_ht += inv.subtotal
            total_tva += inv.tax_total
            total_ttc += inv.total_amount
            
        for cn in cns:
            r = self.table.rowCount()
            self.table.insertRow(r)
            
            ht = cn.total_amount / 1.19
            tva = cn.total_amount - ht
            ttc = cn.total_amount
            
            total_ht -= ht
            total_tva -= tva
            total_ttc -= ttc
            
            self.table.setItem(r, 0, QTableWidgetItem(cn.note_number))
            self.table.setItem(r, 1, QTableWidgetItem(cn.created_at[:10]))
            self.table.setItem(r, 2, QTableWidgetItem(format_money(-ht)))
            self.table.setItem(r, 3, QTableWidgetItem(format_money(-tva)))
            self.table.setItem(r, 4, QTableWidgetItem(format_money(-ttc)))
            self.table.setItem(r, 5, QTableWidgetItem(cn.status))
            for col in range(6):
                self.table.item(r, col).setForeground(QBrush(QColor('#D32F2F')))
            
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem("TOTAL :"))
        self.table.setItem(r, 2, QTableWidgetItem(format_money(total_ht)))
        self.table.setItem(r, 3, QTableWidgetItem(format_money(total_tva)))
        self.table.setItem(r, 4, QTableWidgetItem(format_money(total_ttc)))
        for c in [0, 2, 3, 4]:
            self.table.item(r, c).setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.table.item(r, c).setForeground(QBrush(QColor("#1565C0")))

    def export_pdf(self):
        from app.utils.pdf_exporter import PDFExporter
        # Using existing generic exporter
        headers = ["N° Facture", "Date", "Montant HT", "TVA", "Montant TTC", "Statut"]
        data = []
        for i in range(self.table.rowCount()):
            row = []
            for j in range(self.table.columnCount()):
                it = self.table.item(i, j)
                row.append(it.text() if it else "")
            data.append(row)
            
        pdf_path = os.path.join(tempfile.gettempdir(), f"fiche_{self.client_combo.currentText()}.pdf")
        PDFExporter.export_table_to_pdf(pdf_path, f"Fiche Fiscale : {self.client_combo.currentText()}", headers, data)
        import win32api
        win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)

class RappelConvocationClientsPage(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Rappels Clients")
        
        btn_refresh = QPushButton("🔄 Actualiser")
        btn_refresh.clicked.connect(self.load_data)
        self.main_layout.addWidget(btn_refresh)
        
        self.table = self.create_table(["Client", "NIF", "N° Factures en retard", "Montant dû", "Jours retard", "Actions"])
        self.main_layout.addWidget(self.table)
        self.debts_data = []
        self.load_data()

    def load_data(self):
        self.table.setRowCount(0)
        self.debts_data.clear()
        
        debts = self.db_session.query(Debt).filter(
            Debt.entity_type == "CLIENT",
            Debt.remaining_amount > 0,
            Debt.status != "WRITTEN_OFF",
            Debt.is_deleted == 0
        ).all()
        
        client_debts = {}
        for d in debts:
            cid = d.entity_id
            if cid not in client_debts:
                client_debts[cid] = {'amount': 0.0, 'count': 0, 'oldest_date': d.created_at}
            client_debts[cid]['amount'] += d.remaining_amount
            client_debts[cid]['count'] += 1
            if d.created_at < client_debts[cid]['oldest_date']:
                client_debts[cid]['oldest_date'] = d.created_at
                
        now = datetime.now()
        for cid, info in client_debts.items():
            c = self.db_session.query(Client).get(cid)
            if not c: continue
            
            d_obj = datetime.strptime(info['oldest_date'][:10], "%Y-%m-%d")
            jours = (now - d_obj).days
            
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(c.name))
            self.table.setItem(r, 1, QTableWidgetItem(c.tax_id or ""))
            self.table.setItem(r, 2, QTableWidgetItem(str(info['count'])))
            self.table.setItem(r, 3, QTableWidgetItem(format_money(info['amount'])))
            self.table.setItem(r, 4, QTableWidgetItem(f"{jours} j"))
            
            # Color coding
            color = "#000000"
            bg = "#FFFFFF"
            if jours > 60: bg = "#FFEBEE"; color = "#B71C1C"
            elif jours > 30: bg = "#FFF3E0"; color = "#E65100"
            else: bg = "#F1F8E9"; color = "#33691E"
            
            for col in range(5):
                self.table.item(r, col).setBackground(QBrush(QColor(bg)))
                self.table.item(r, col).setForeground(QBrush(QColor(color)))
                
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0,0,0,0)
            btn_print = QPushButton("📄 Imprimer")
            btn_print.clicked.connect(lambda ch, client_name=c.name, amt=info['amount']: self.print_rappel(client_name, amt))
            btn_done = QPushButton("✅ Marquer Envoyé")
            btn_done.clicked.connect(lambda ch, cid=cid: self.mark_sent(cid))
            btn_layout.addWidget(btn_print)
            btn_layout.addWidget(btn_done)
            w = QWidget()
            w.setLayout(btn_layout)
            self.table.setCellWidget(r, 5, w)
            
    def mark_sent(self, cid):
        c = self.db_session.query(Client).get(cid)
        if c:
            from datetime import datetime
            c.last_reminder_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.db_session.commit()
            QMessageBox.information(self, "Succès", "Rappel marqué comme envoyé.")
            self.load_data()

    def print_rappel(self, client_name, amount):
        pdf_path = os.path.join(tempfile.gettempdir(), f"rappel_{client_name}.pdf")
        fake_factures = [["Multiples", "---", format_money(amount), format_money(amount), "---"]]
        try:
            FiscalPDFExporter.export_rappel_client_pdf(pdf_path, client_name, fake_factures, amount)
            import win32api
            win32api.ShellExecute(0, "open", pdf_path, None, ".", 1)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

class JournalVentesFactureesPage(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Journal des Ventes Facturées")
class FacturesAvoirPage(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Factures d'Avoir")
class FacturesComplementairePage(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Factures Complémentaires")
class FacturesAchatPage(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Factures d'Achat")
class PrixFacturationPage(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Prix de Facturation")
class AttachementsPage(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Attachements")
class BordereauEnvoiPage(BaseFiscalPage):
    def __init__(self, user, parent=None):
        super().__init__(user, parent)
        self.create_header("Bordereau d'Envoi")
