from ui.utils.widgets import SearchableComboBox
"""
ParaFarm ERP — Supplier Form Dialog (FIX 3 Overhaul)
Full bilingual multi-section profile: Identité, Adresse, Contact, Fiscal, Financial Panel.
Extended fields stored as JSON inside the existing supplier.notes column.
"""
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDoubleSpinBox, QMessageBox,
    QFormLayout, QFrame, QCheckBox, QGroupBox,
    QScrollArea, QWidget, QTextEdit, QSpinBox, QComboBox
)
from PySide6.QtCore import Qt
from app.models.supplier import Supplier
from app.services.supplier_service import SupplierService
from app.core.database import get_session
from app.core.exceptions import ValidationError

_JSON_KEY = "__parafarm_ext__"


def _load_ext(supplier: Supplier) -> dict:
    if supplier and supplier.notes:
        try:
            data = json.loads(supplier.notes)
            if isinstance(data, dict) and _JSON_KEY in data:
                return data[_JSON_KEY]
        except Exception:
            pass
    return {}


def _get_plain_notes(supplier: Supplier) -> str:
    if supplier and supplier.notes:
        try:
            data = json.loads(supplier.notes)
            if isinstance(data, dict) and _JSON_KEY in data:
                return data.get("notes", "")
        except Exception:
            return supplier.notes or ""
    return ""


def _section_box(title: str, color: str = "#1B5E20") -> QGroupBox:
    gb = QGroupBox(title)
    gb.setStyleSheet(f"""
        QGroupBox {{
            font-weight: 700;
            font-size: 12px;
            border: 1px solid #BDBDBD;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 12px;
            color: {color};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
        }}
    """)
    return gb


def _ar_input(placeholder: str = "") -> QLineEdit:
    le = QLineEdit()
    le.setLayoutDirection(Qt.RightToLeft)
    le.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    if placeholder:
        le.setPlaceholderText(placeholder)
    return le


class SupplierDialog(QDialog):
    """Full-featured Fiche Fournisseur dialog (bilingual, multi-section, financial panel)."""

    def __init__(self, user, supplier: Supplier = None, parent=None):
        super().__init__(parent)
        self.user = user
        self.supplier = supplier
        self.db_session = get_session()
        self.service = SupplierService(self.db_session)
        self._ext = _load_ext(supplier) if supplier else {}

        self.setWindowTitle("Fiche Fournisseur — Modifier" if supplier else "Fiche Fournisseur — Nouveau")
        self.setMinimumSize(860, 680)
        self.resize(920, 720)
        self._setup_ui()

        if self.supplier:
            self._load_data()

    # ── UI Construction ───────────────────────────────────────────
    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left side (scrollable form) ───────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(10)

        # Header title
        header = QLabel("🏭  FICHE FOURNISSEUR")
        header.setStyleSheet(
            "font-size:16px; font-weight:700; color:#FFFFFF;"
            "background:#1565C0; padding:10px 16px; border-radius:4px;"
        )
        left_layout.addWidget(header)

        # Section 1 — Identité
        id_box = _section_box("① Identité", "#1565C0")
        id_form = QFormLayout(id_box)
        id_form.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom du fournisseur (français)")
        id_form.addRow("Nom (Fr) *", self.name_input)

        self.name_ar_input = _ar_input("اسم المورد")
        id_form.addRow("Nom (Ar)", self.name_ar_input)

        self.category_combo = SearchableComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems([
            "", "PHARMACEUTIQUE", "PARAPHARMACIE", "COSMETIQUE", "GENERAL", "MEDICAL"
        ])
        id_form.addRow("Catégorie", self.category_combo)

        self.activity_input = QLineEdit()
        self.activity_input.setPlaceholderText("Activité / spécialité")
        id_form.addRow("Activité", self.activity_input)

        left_layout.addWidget(id_box)

        # Section 2 — Adresse
        addr_box = _section_box("② Adresse", "#1565C0")
        addr_form = QFormLayout(addr_box)
        addr_form.setSpacing(8)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Adresse principale (français)")
        addr_form.addRow("Adresse (Fr)", self.address_input)

        self.address_ar_input = _ar_input("العنوان الرئيسي")
        addr_form.addRow("Adresse (Ar)", self.address_ar_input)

        self.delivery_addr_input = QLineEdit()
        self.delivery_addr_input.setPlaceholderText("Adresse d'enlèvement (si différente)")
        addr_form.addRow("Enlèvement (Fr)", self.delivery_addr_input)

        self.delivery_ar_input = _ar_input("عنوان الاستلام")
        addr_form.addRow("Enlèvement (Ar)", self.delivery_ar_input)

        left_layout.addWidget(addr_box)

        # Section 3 — Contact
        contact_box = _section_box("③ Contact", "#1565C0")
        contact_form = QFormLayout(contact_box)
        contact_form.setSpacing(8)

        tel_row = QHBoxLayout()
        self.tel_input = QLineEdit()
        self.tel_input.setPlaceholderText("Tél principal")
        self.fax_input = QLineEdit()
        self.fax_input.setPlaceholderText("Fax")
        tel_row.addWidget(self.tel_input)
        tel_row.addWidget(QLabel("/ Fax:"))
        tel_row.addWidget(self.fax_input)
        contact_form.addRow("Tél / Fax", tel_row)

        self.mobile_input = QLineEdit()
        self.mobile_input.setPlaceholderText("0550... / 0770...")
        contact_form.addRow("Mobile", self.mobile_input)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@fournisseur.com")
        contact_form.addRow("Email", self.email_input)

        self.contact_person_input = QLineEdit()
        self.contact_person_input.setPlaceholderText("Nom du représentant commercial")
        contact_form.addRow("Contact", self.contact_person_input)

        left_layout.addWidget(contact_box)

        # Section 4 — Fiscal
        fiscal_box = _section_box("④ Fiscal", "#E65100")
        fiscal_form = QFormLayout(fiscal_box)
        fiscal_form.setSpacing(8)

        self.rc_input = QLineEdit()
        self.rc_input.setPlaceholderText("Registre du Commerce")
        fiscal_form.addRow("RC", self.rc_input)

        self.nif_input = QLineEdit()
        self.nif_input.setPlaceholderText("Numéro d'Identification Fiscale")
        fiscal_form.addRow("NIF", self.nif_input)

        self.nis_input = QLineEdit()
        self.nis_input.setPlaceholderText("Numéro d'Identification Statistique")
        fiscal_form.addRow("NIS", self.nis_input)

        self.article_input = QLineEdit()
        self.article_input.setPlaceholderText("Article d'Imposition")
        fiscal_form.addRow("Article", self.article_input)

        self.tax_center_input = QLineEdit()
        self.tax_center_input.setPlaceholderText("🏛️  Centre des Impôts")
        fiscal_form.addRow("Centre Impôts", self.tax_center_input)

        self.soumis_tva_check = QCheckBox("Soumis à la TVA")
        fiscal_form.addRow("TVA", self.soumis_tva_check)

        left_layout.addWidget(fiscal_box)

        # Notes
        notes_box = _section_box("⑤ Notes", "#1565C0")
        notes_layout = QVBoxLayout(notes_box)
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(70)
        self.notes_input.setPlaceholderText("Observations, conditions commerciales...")
        notes_layout.addWidget(self.notes_input)
        left_layout.addWidget(notes_box)

        left_layout.addStretch()
        scroll.setWidget(left_widget)
        root.addWidget(scroll, 3)

        # ── Right side (Financial Panel + Buttons) ────────────────
        right_panel = QWidget()
        right_panel.setFixedWidth(260)
        right_panel.setStyleSheet("background:#F5F5F5; border-left:1px solid #E0E0E0;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 16, 14, 16)
        right_layout.setSpacing(12)

        fin_title = QLabel("💰  PANNEAU FINANCIER")
        fin_title.setStyleSheet(
            "font-size:12px; font-weight:700; color:#FFFFFF;"
            "background:#1565C0; padding:8px 10px; border-radius:4px;"
        )
        right_layout.addWidget(fin_title)

        # Credit initial (read-only)
        cr_init_label = QLabel("Crédit Fournisseur")
        cr_init_label.setStyleSheet("font-size:11px; color:#757575; font-weight:600;")
        right_layout.addWidget(cr_init_label)

        self.credit_initial_spin = QDoubleSpinBox()
        self.credit_initial_spin.setMaximum(9999999.99)
        self.credit_initial_spin.setSuffix(" DA")
        self.credit_initial_spin.setReadOnly(True)
        self.credit_initial_spin.setStyleSheet("background:#EEEEEE; color:#424242;")
        right_layout.addWidget(self.credit_initial_spin)

        # Credit period
        period_label = QLabel("Période de Crédit")
        period_label.setStyleSheet("font-size:11px; color:#757575; font-weight:600;")
        right_layout.addWidget(period_label)

        self.credit_period_spin = QSpinBox()
        self.credit_period_spin.setRange(0, 365)
        self.credit_period_spin.setValue(30)
        self.credit_period_spin.setSuffix(" jours")
        right_layout.addWidget(self.credit_period_spin)

        # Credit max (editable)
        cr_max_label = QLabel("Limite de Crédit")
        cr_max_label.setStyleSheet("font-size:11px; color:#757575; font-weight:600;")
        right_layout.addWidget(cr_max_label)

        self.credit_limit_spin = QDoubleSpinBox()
        self.credit_limit_spin.setMaximum(9999999.99)
        self.credit_limit_spin.setSuffix(" DA")
        self.credit_limit_spin.setStyleSheet("background:#FFF8E1; color:#E65100; font-weight:700;")
        right_layout.addWidget(self.credit_limit_spin)

        # Blocage
        self.bloquer_check = QCheckBox("🚫  Fournisseur Bloqué")
        self.bloquer_check.setStyleSheet("font-weight:600; color:#B71C1C;")
        right_layout.addWidget(self.bloquer_check)

        right_layout.addStretch()

        # Action buttons (vertical)
        btn_style_save = (
            "QPushButton { background:#1565C0; color:#FFF; font-weight:700;"
            "border-radius:5px; padding:10px; font-size:13px; }"
            "QPushButton:hover { background:#1976D2; }"
        )
        btn_style_cancel = (
            "QPushButton { background:#455A64; color:#FFF; font-weight:700;"
            "border-radius:5px; padding:10px; font-size:13px; }"
            "QPushButton:hover { background:#546E7A; }"
        )

        save_btn = QPushButton("✔  Valider")
        save_btn.setStyleSheet(btn_style_save)
        save_btn.clicked.connect(self._on_save)
        right_layout.addWidget(save_btn)

        cancel_btn = QPushButton("✕  Annuler")
        cancel_btn.setStyleSheet(btn_style_cancel)
        cancel_btn.clicked.connect(self.reject)
        right_layout.addWidget(cancel_btn)

        root.addWidget(right_panel)

    # ── Data load / save ──────────────────────────────────────────
    def _load_data(self):
        s = self.supplier
        ext = self._ext

        self.name_input.setText(s.name or "")
        self.tel_input.setText(s.phone or "")
        self.address_input.setText(s.address or "")
        self.email_input.setText(s.email or "")
        self.credit_limit_spin.setValue(s.credit_limit or 0.0)
        self.credit_period_spin.setValue(s.credit_period_days or 30)
        self.category_combo.setCurrentText(s.category or "")

        # Extended
        self.name_ar_input.setText(ext.get("name_ar", ""))
        self.activity_input.setText(ext.get("activity", ""))
        self.address_ar_input.setText(ext.get("address_ar", ""))
        self.delivery_addr_input.setText(ext.get("delivery_addr", ""))
        self.delivery_ar_input.setText(ext.get("delivery_ar", ""))
        self.fax_input.setText(ext.get("fax", ""))
        self.mobile_input.setText(ext.get("mobile", ""))
        self.contact_person_input.setText(ext.get("contact_person", ""))
        self.rc_input.setText(ext.get("rc", ""))
        self.nif_input.setText(ext.get("nif", s.tax_id or ""))
        self.nis_input.setText(ext.get("nis", ""))
        self.article_input.setText(ext.get("article", ""))
        self.tax_center_input.setText(ext.get("tax_center", ""))
        self.soumis_tva_check.setChecked(ext.get("soumis_tva", False))
        self.credit_initial_spin.setValue(ext.get("credit_initial", 0.0))
        self.bloquer_check.setChecked(ext.get("bloquer", False))
        self.notes_input.setPlainText(_get_plain_notes(s))

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Erreur", "Le nom du fournisseur est obligatoire.")
            return

        ext = {
            "name_ar": self.name_ar_input.text().strip(),
            "activity": self.activity_input.text().strip(),
            "address_ar": self.address_ar_input.text().strip(),
            "delivery_addr": self.delivery_addr_input.text().strip(),
            "delivery_ar": self.delivery_ar_input.text().strip(),
            "fax": self.fax_input.text().strip(),
            "mobile": self.mobile_input.text().strip(),
            "contact_person": self.contact_person_input.text().strip(),
            "rc": self.rc_input.text().strip(),
            "nif": self.nif_input.text().strip(),
            "nis": self.nis_input.text().strip(),
            "article": self.article_input.text().strip(),
            "tax_center": self.tax_center_input.text().strip(),
            "soumis_tva": self.soumis_tva_check.isChecked(),
            "credit_initial": self.credit_initial_spin.value(),
            "bloquer": self.bloquer_check.isChecked(),
        }

        plain_notes = self.notes_input.toPlainText().strip()
        blob = json.dumps({_JSON_KEY: ext, "notes": plain_notes}, ensure_ascii=False)

        data = {
            "name": name,
            "phone": self.tel_input.text().strip() or None,
            "address": self.address_input.text().strip() or None,
            "email": self.email_input.text().strip() or None,
            "category": self.category_combo.currentText().strip() or None,
            "tax_id": self.nif_input.text().strip() or None,
            "credit_period_days": self.credit_period_spin.value(),
            "credit_limit": self.credit_limit_spin.value(),
            "notes": blob,
        }

        try:
            if self.supplier:
                self.service.update_supplier(self.supplier.id, data)
            else:
                self.service.create_supplier(data)
            self.accept()
        except ValidationError as e:
            QMessageBox.warning(self, "Erreur de validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur système", str(e))
