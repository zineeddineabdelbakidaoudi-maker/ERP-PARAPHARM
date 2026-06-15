"""
ParaFarm ERP — Options Module Pages
Error/alarm log, deleted operations history, audit trail, document counters,
appointments/tasks, scanned documents, activation key, company info.
"""
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QComboBox, QDateEdit, QFileDialog, QFrame,
    QTextEdit, QFormLayout, QDialog, QSpinBox, QCalendarWidget,
    QCheckBox, QGroupBox
)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QColor
from app.core.database import get_session
from app.models.setting import AuditLog, Setting


class BaseOptionsPage(QWidget):
    """Reusable base for options/audit pages."""
    PAGE_TITLE = "Options"
    COLUMNS = ["Date", "Type", "Description"]

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"⚙️ {self.PAGE_TITLE}")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1B5E20;")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher...")
        self.search_input.setMinimumWidth(250)
        self.search_input.textChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(self.search_input)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.dateChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(QLabel("Du:"))
        toolbar.addWidget(self.date_from)

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(lambda _: self.refresh_data())
        toolbar.addWidget(QLabel("Au:"))
        toolbar.addWidget(self.date_to)

        toolbar.addStretch()

        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self.refresh_data)
        toolbar.addWidget(refresh_btn)

        export_btn = QPushButton("📊 CSV")
        export_btn.clicked.connect(self._export_csv)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

        bottom = QHBoxLayout()
        self.lbl_count = QLabel("0 enregistrements")
        self.lbl_count.setStyleSheet("color: #757575; font-size: 12px;")
        bottom.addWidget(self.lbl_count)
        bottom.addStretch()
        layout.addLayout(bottom)

    def _get_data(self):
        return []

    def refresh_data(self):
        self.table.setRowCount(0)
        data = self._get_data()
        search = self.search_input.text().strip().lower()
        if search:
            data = [d for d in data if any(search in str(v).lower() for v in d.values())]
        for row_data in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, key in enumerate(self.COLUMNS):
                val = row_data.get(key, "")
                item = QTableWidgetItem(str(val))
                self.table.setItem(row, col, item)
        self.lbl_count.setText(f"{len(data)} enregistrements")

    def _export_csv(self):
        import csv
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "Aucune donnée.")
            return
        fp, _ = QFileDialog.getSaveFileName(self, "CSV", f"{self.PAGE_TITLE}_{datetime.now():%Y%m%d}.csv", "CSV (*.csv)")
        if not fp:
            return
        try:
            with open(fp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(self.COLUMNS)
                for r in range(self.table.rowCount()):
                    w.writerow([self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(len(self.COLUMNS))])
            QMessageBox.information(self, "Succès", f"Exporté: {fp}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))


# ── Specific Options Pages ────────────────────────────────────

class ErreursAlarmesPage(BaseOptionsPage):
    PAGE_TITLE = "Erreurs & Alarmes"
    COLUMNS = ["Date/Heure", "Niveau", "Module", "Message", "Utilisateur"]

    def _get_data(self):
        # Read from log files
        import os
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
        log_dir = os.path.normpath(log_dir)
        result = []
        if os.path.exists(log_dir):
            for fn in sorted(os.listdir(log_dir), reverse=True)[:5]:
                fp = os.path.join(log_dir, fn)
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f.readlines()[-100:]:
                            if "ERROR" in line or "WARNING" in line or "CRITICAL" in line:
                                parts = line.strip().split(" — ", 1)
                                timestamp = parts[0][:19] if len(parts) > 0 else "—"
                                level = "ERROR" if "ERROR" in line else ("WARNING" if "WARNING" in line else "CRITICAL")
                                msg = parts[1] if len(parts) > 1 else line.strip()
                                result.append({
                                    "Date/Heure": timestamp, "Niveau": level,
                                    "Module": "System", "Message": msg[:120],
                                    "Utilisateur": "—"
                                })
                except Exception:
                    pass
        return result[-50:]  # Last 50


class HistoriqueModificationsPage(BaseOptionsPage):
    PAGE_TITLE = "Historique des Modifications (Audit Trail)"
    COLUMNS = ["Date/Heure", "Utilisateur", "Action", "Module", "Détails"]

    def _get_data(self):
        from app.models.user import User
        d_from = self.date_from.date().toString("yyyy-MM-dd")
        d_to = self.date_to.date().toString("yyyy-MM-dd") + " 23:59:59"
        logs = self.db_session.query(AuditLog).filter(
            AuditLog.created_at >= d_from, AuditLog.created_at <= d_to
        ).order_by(AuditLog.created_at.desc()).limit(500).all()
        user_map = {u.id: u.full_name for u in self.db_session.query(User).all()}
        result = []
        for log in logs:
            result.append({
                "Date/Heure": log.created_at,
                "Utilisateur": user_map.get(log.user_id, "Système"),
                "Action": log.action, "Module": log.module,
                "Détails": log.description or "—"
            })
        return result


class HistoriqueOperationsSupprimees(BaseOptionsPage):
    PAGE_TITLE = "Historique des Opérations Supprimées"
    COLUMNS = ["Date Suppression", "Type", "Référence", "Montant", "Supprimé Par"]

    def _get_data(self):
        from app.models.user import User
        logs = self.db_session.query(AuditLog).filter(
            AuditLog.action == "DELETE"
        ).order_by(AuditLog.created_at.desc()).limit(200).all()
        user_map = {u.id: u.full_name for u in self.db_session.query(User).all()}
        return [{"Date Suppression": l.created_at, "Type": l.module,
                 "Référence": l.description or "—", "Montant": "—",
                 "Supprimé Par": user_map.get(l.user_id, "Système")} for l in logs]


class HistoriqueVentesClientsSupprimees(BaseOptionsPage):
    PAGE_TITLE = "Historique BL Clients Supprimés"
    COLUMNS = ["Date Suppression", "N° BL", "Client", "Montant", "Supprimé Par"]

    def _get_data(self):
        from app.models.delivery import Delivery
        deleted = self.db_session.query(Delivery).filter(Delivery.is_deleted == 1).all()
        return [{"Date Suppression": d.deleted_at or "—", "N° BL": d.delivery_number,
                 "Client": d.client.name if d.client else "—",
                 "Montant": "—",
                 "Supprimé Par": "—"} for d in deleted]


class HistoriqueVentesComptoirSupprimees(BaseOptionsPage):
    PAGE_TITLE = "Historique Ventes Comptoir Supprimées"
    COLUMNS = ["Date Suppression", "N° Vente", "Montant", "Mode Paiement", "Supprimé Par"]

    def _get_data(self):
        from app.models.sale import Sale
        deleted = self.db_session.query(Sale).filter(Sale.status == "VOIDED").all()
        return [{"Date Suppression": s.updated_at or "—", "N° Vente": s.sale_number,
                 "Montant": f"{s.total_amount:,.2f}", "Mode Paiement": s.payment_method or "—",
                 "Supprimé Par": "—"} for s in deleted]


class HistoriqueAchatsSupprimesPage(BaseOptionsPage):
    PAGE_TITLE = "Historique Achats Supprimés"
    COLUMNS = ["Date Suppression", "N° Achat", "Fournisseur", "Montant", "Supprimé Par"]

    def _get_data(self):
        from app.models.purchase import Purchase
        deleted = self.db_session.query(Purchase).filter(Purchase.is_deleted == 1).all()
        return [{"Date Suppression": p.deleted_at or "—", "N° Achat": p.purchase_number,
                 "Fournisseur": p.supplier.name if p.supplier else "—",
                 "Montant": f"{p.total_amount:,.2f}", "Supprimé Par": "—"} for p in deleted]


class CompteurNumerosBonsPage(QWidget):
    """Document number counter manager — configure numbering sequences."""
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("🔢 Compteur de Numéros de Bons")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1B5E20;")
        layout.addWidget(title)

        desc = QLabel("Configurez les séquences de numérotation pour chaque type de document.")
        desc.setStyleSheet("color: #757575;")
        layout.addWidget(desc)

        # Counter table
        counters = [
            ("BL — Bon de Livraison", "LVR", "delivery"),
            ("BR — Bon de Réception", "ACH", "purchase"),
            ("FA — Facture de Vente", "FAC", "invoice"),
            ("BC — Bon de Commande", "CMD", "purchase_order"),
            ("AV — Avoir Client", "AVR", "credit_note"),
            ("VRS — Versement Bancaire", "VRS", "bank_deposit"),
            ("RET — Retrait Bancaire", "RET", "bank_withdrawal"),
            ("TRF — Transfert", "TRF", "bank_transfer"),
        ]

        self.table = QTableWidget(len(counters), 4)
        self.table.setHorizontalHeaderLabels(["Document", "Préfixe", "Prochain N°", "Actions"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 120)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)

        for i, (name, prefix, _) in enumerate(counters):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(prefix))
            self.table.setItem(i, 2, QTableWidgetItem("Auto"))

            btn = QPushButton("🔄 Réinitialiser")
            btn.setToolTip("Réinitialiser le compteur")
            btn.clicked.connect(lambda _, n=name: QMessageBox.information(
                self, "Info", f"Le compteur '{n}' utilise l'auto-incrémentation de la base de données."
            ))
            self.table.setCellWidget(i, 3, btn)

        layout.addWidget(self.table)
        layout.addStretch()


class RendezVousTachesPage(QWidget):
    """Appointments and tasks manager (calendar-style)."""
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self._tasks = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("📅 Rendez-Vous & Tâches Planifiées")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1B5E20;")
        layout.addWidget(title)

        top = QHBoxLayout()
        # Calendar
        self.calendar = QCalendarWidget()
        self.calendar.setMaximumWidth(350)
        self.calendar.selectionChanged.connect(self._on_date_selected)
        top.addWidget(self.calendar)

        # Task list for selected day
        right = QVBoxLayout()
        self.day_label = QLabel(f"Tâches du {QDate.currentDate().toString('dd/MM/yyyy')}")
        self.day_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        right.addWidget(self.day_label)

        add_btn = QPushButton("➕ Nouvelle Tâche")
        add_btn.clicked.connect(self._add_task)
        right.addWidget(add_btn)

        self.task_table = QTableWidget(0, 4)
        self.task_table.setHorizontalHeaderLabels(["Heure", "Titre", "Priorité", "Actions"])
        h = self.task_table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.Fixed)
        self.task_table.setColumnWidth(3, 80)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.verticalHeader().setDefaultSectionSize(48)
        right.addWidget(self.task_table)

        top.addLayout(right)
        layout.addLayout(top)

    def _on_date_selected(self):
        date = self.calendar.selectedDate().toString("dd/MM/yyyy")
        self.day_label.setText(f"Tâches du {date}")
        self._refresh_tasks()

    def _refresh_tasks(self):
        self.task_table.setRowCount(0)
        date_str = self.calendar.selectedDate().toString("yyyy-MM-dd")
        day_tasks = [t for t in self._tasks if t["date"] == date_str]
        for t in day_tasks:
            row = self.task_table.rowCount()
            self.task_table.insertRow(row)
            self.task_table.setItem(row, 0, QTableWidgetItem(t["time"]))
            self.task_table.setItem(row, 1, QTableWidgetItem(t["title"]))
            self.task_table.setItem(row, 2, QTableWidgetItem(t["priority"]))
            del_btn = QPushButton("🗑️")
            del_btn.clicked.connect(lambda _, task=t: self._delete_task(task))
            self.task_table.setCellWidget(row, 3, del_btn)

    def _add_task(self):
        from PySide6.QtWidgets import QInputDialog, QTimeEdit
        title, ok = QInputDialog.getText(self, "Tâche", "Titre de la tâche:")
        if ok and title:
            self._tasks.append({
                "date": self.calendar.selectedDate().toString("yyyy-MM-dd"),
                "time": datetime.now().strftime("%H:%M"),
                "title": title,
                "priority": "Normal"
            })
            self._refresh_tasks()

    def _delete_task(self, task):
        if task in self._tasks:
            self._tasks.remove(task)
            self._refresh_tasks()


class AlarmeRendezVousTachesPage(BaseOptionsPage):
    PAGE_TITLE = "Alarmes & Rappels"
    COLUMNS = ["Date/Heure", "Type", "Description", "Priorité", "Statut"]

    def _get_data(self):
        """Show automated alerts: stock expiry, low stock, unpaid debts."""
        from app.models.product import Product
        from app.models.stock import Stock
        from app.models.debt import Debt
        result = []
        now_str = datetime.now().strftime("%Y-%m-%d")
        # Stock alerts - low stock
        try:
            products = self.db_session.query(Product).filter(Product.is_deleted == 0).all()
            for p in products:
                stk = self.db_session.query(Stock).filter(Stock.product_id == p.id).first()
                qty = stk.quantity if stk else 0
                threshold = p.min_stock_level if hasattr(p, 'min_stock_level') and p.min_stock_level else 5
                if qty <= 0:
                    result.append({"Date/Heure": now_str, "Type": "🔴 Rupture Stock",
                        "Description": f"{p.name} — Stock: {qty}", "Priorité": "Critique", "Statut": "Active"})
                elif qty <= threshold:
                    result.append({"Date/Heure": now_str, "Type": "🟡 Stock Faible",
                        "Description": f"{p.name} — Stock: {qty} (seuil: {threshold})", "Priorité": "Haute", "Statut": "Active"})
        except Exception:
            pass
        # Overdue debts
        try:
            debts = self.db_session.query(Debt).filter(
                Debt.status.in_(["PENDING", "PARTIAL"]), Debt.is_deleted == 0
            ).all()
            for d in debts:
                if d.due_date:
                    try:
                        due = datetime.strptime(d.due_date, "%Y-%m-%d")
                        days = (datetime.now() - due).days
                        if days > 30:
                            result.append({"Date/Heure": d.due_date, "Type": "🔴 Créance Impayée",
                                "Description": f"Entité #{d.entity_id} — {d.remaining_amount:,.2f} DA ({days}j retard)",
                                "Priorité": "Critique", "Statut": "En retard"})
                    except Exception:
                        pass
        except Exception:
            pass
        return result


class DocumentsScannésPage(QWidget):
    """Document scanner / file attachment manager."""
    PAGE_TITLE = "Documents Scannés"

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._docs = []  # List of (path, type, linked_doc, date)
        self._setup_ui()
        self._load_docs()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("📄 Documents Scannés & Pièces Jointes")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1B5E20;")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("📎 Ajouter Fichier")
        add_btn.clicked.connect(self._add_file)
        toolbar.addWidget(add_btn)
        toolbar.addStretch()
        self.lbl_count = QLabel("0 documents")
        self.lbl_count.setStyleSheet("color: #757575;")
        toolbar.addWidget(self.lbl_count)
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Date", "Nom du Fichier", "Type", "Document Lié", "Actions"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        h.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 120)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.table)

    def _load_docs(self):
        import os, json
        docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "scanned_docs")
        self._docs_dir = os.path.normpath(docs_dir)
        meta_file = os.path.join(self._docs_dir, "_index.json")
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    self._docs = json.load(f)
            except Exception:
                self._docs = []
        self._refresh_table()

    def _save_index(self):
        import os, json
        os.makedirs(self._docs_dir, exist_ok=True)
        meta_file = os.path.join(self._docs_dir, "_index.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(self._docs, f, ensure_ascii=False, indent=2)

    def _refresh_table(self):
        self.table.setRowCount(0)
        for doc in self._docs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(doc.get("date", "—")))
            self.table.setItem(row, 1, QTableWidgetItem(doc.get("filename", "—")))
            self.table.setItem(row, 2, QTableWidgetItem(doc.get("type", "Autre")))
            self.table.setItem(row, 3, QTableWidgetItem(doc.get("linked", "—")))
            open_btn = QPushButton("📂 Ouvrir")
            open_btn.clicked.connect(lambda _, d=doc: self._open_file(d))
            self.table.setCellWidget(row, 4, open_btn)
        self.lbl_count.setText(f"{len(self._docs)} documents")

    def _add_file(self):
        import os, shutil
        fp, _ = QFileDialog.getOpenFileName(self, "Sélectionner un fichier", "", "Tous (*.*);; PDF (*.pdf);; Images (*.png *.jpg *.jpeg)")
        if not fp:
            return
        os.makedirs(self._docs_dir, exist_ok=True)
        filename = os.path.basename(fp)
        dest = os.path.join(self._docs_dir, filename)
        try:
            shutil.copy2(fp, dest)
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return
        self._docs.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "filename": filename,
            "path": dest,
            "type": "PDF" if filename.lower().endswith(".pdf") else "Image",
            "linked": "—"
        })
        self._save_index()
        self._refresh_table()

    def _open_file(self, doc):
        import os
        path = doc.get("path", "")
        if os.path.exists(path):
            os.startfile(path)
        else:
            QMessageBox.warning(self, "Erreur", f"Fichier introuvable: {path}")


class CleActivationPage(QWidget):
    """Software license/activation key management."""
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        title = QLabel("🔐 Clé d'Activation — Licence Logiciel")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1B5E20;")
        layout.addWidget(title)

        card = QFrame()
        card.setStyleSheet("""
            QFrame { background: white; border-radius: 12px; border: 1px solid #E0E0E0; padding: 24px; }
        """)
        card_layout = QVBoxLayout(card)

        status = QLabel("✅ Licence Active — Édition Professionnelle")
        status.setStyleSheet("font-size: 14px; font-weight: 600; color: #2E7D32;")
        card_layout.addWidget(status)

        form = QFormLayout()
        form.addRow("Produit:", QLabel("ParaFarm ERP — Gestion Pharmacie"))
        form.addRow("Version:", QLabel("2.0.0"))
        form.addRow("Édition:", QLabel("Professionnelle"))
        form.addRow("Clé:", QLabel("XXXX-XXXX-XXXX-XXXX"))
        form.addRow("Expire:", QLabel("Illimitée"))
        form.addRow("Poste:", QLabel("PC Principal"))
        card_layout.addLayout(form)

        layout.addWidget(card)
        layout.addStretch()


class InformationsEtablissementPage(QWidget):
    """Company profile editor (name, address, logo, QR code, fiscal info)."""
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.db_session = get_session()
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("🏢 Informations de l'Établissement")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #1B5E20;")
        layout.addWidget(title)

        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom de l'établissement")
        form.addRow("Nom *", self.name_input)

        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(60)
        form.addRow("Adresse", self.address_input)

        self.phone_input = QLineEdit()
        form.addRow("Téléphone", self.phone_input)

        self.email_input = QLineEdit()
        form.addRow("Email", self.email_input)

        self.nif_input = QLineEdit()
        self.nif_input.setPlaceholderText("Numéro d'Identification Fiscale")
        form.addRow("NIF", self.nif_input)

        self.nis_input = QLineEdit()
        self.nis_input.setPlaceholderText("Numéro d'Identification Statistique")
        form.addRow("NIS", self.nis_input)

        self.rc_input = QLineEdit()
        self.rc_input.setPlaceholderText("Numéro de Registre de Commerce")
        form.addRow("RC", self.rc_input)

        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Article d'Imposition")
        form.addRow("Article Imposition", self.ai_input)

        layout.addLayout(form)

        save_btn = QPushButton("💾 Enregistrer")
        save_btn.clicked.connect(self._save_data)
        layout.addWidget(save_btn)
        layout.addStretch()

    def _load_data(self):
        settings = {s.key: s.value for s in self.db_session.query(Setting).all()}
        self.name_input.setText(settings.get("company_name", "ParaFarm Pharmacie"))
        self.address_input.setPlainText(settings.get("company_address", ""))
        self.phone_input.setText(settings.get("company_phone", ""))
        self.email_input.setText(settings.get("company_email", ""))
        self.nif_input.setText(settings.get("company_nif", ""))
        self.nis_input.setText(settings.get("company_nis", ""))
        self.rc_input.setText(settings.get("company_rc", ""))
        self.ai_input.setText(settings.get("company_ai", ""))

    def _save_data(self):
        pairs = {
            "company_name": self.name_input.text().strip(),
            "company_address": self.address_input.toPlainText().strip(),
            "company_phone": self.phone_input.text().strip(),
            "company_email": self.email_input.text().strip(),
            "company_nif": self.nif_input.text().strip(),
            "company_nis": self.nis_input.text().strip(),
            "company_rc": self.rc_input.text().strip(),
            "company_ai": self.ai_input.text().strip(),
        }
        for key, value in pairs.items():
            s = self.db_session.query(Setting).filter(Setting.key == key).first()
            if s:
                s.value = value
            else:
                s = Setting(key=key, value=value, category="GENERAL", data_type="STRING")
                self.db_session.add(s)
        self.db_session.commit()
        QMessageBox.information(self, "Succès", "Informations enregistrées.")
