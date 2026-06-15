"""
ParaFarm ERP — Client Form Dialog (FIX 3 Overhaul)
Full bilingual multi-section profile: Identité, Adresse, Contact, Fiscal, Financial Panel.
Extended fields stored as JSON inside the existing client.notes column.
"""
import json
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDoubleSpinBox, QMessageBox,
    QFormLayout, QFrame, QCheckBox, QGroupBox, QSizePolicy,
    QScrollArea, QWidget, QTextEdit, QSpinBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app.models.client import Client
from app.services.client_service import ClientService
from app.core.database import get_session
from app.core.exceptions import ValidationError

# Keys for the JSON blob inside notes
_JSON_KEY = "__parafarm_ext__"


def _load_ext(client: Client) -> dict:
    """Extract extended JSON fields from client.notes, leaving plain text alone."""
    if client and client.notes:
        try:
            data = json.loads(client.notes)
            if isinstance(data, dict) and _JSON_KEY in data:
                return data[_JSON_KEY]
        except Exception:
            pass
    return {}


def _save_ext(client: Client, ext: dict, plain_notes: str):
    """Serialize extended fields + plain notes back into client.notes."""
    blob = {_JSON_KEY: ext, "notes": plain_notes}
    client.notes = json.dumps(blob, ensure_ascii=False)


def _get_plain_notes(client: Client) -> str:
    """Extract human-readable notes from the encoded notes field."""
    if client and client.notes:
        try:
            data = json.loads(client.notes)
            if isinstance(data, dict) and _JSON_KEY in data:
                return data.get("notes", "")
        except Exception:
            return client.notes or ""
    return ""


def _section_box(title: str) -> QGroupBox:
    gb = QGroupBox(title)
    gb.setStyleSheet("""
        QGroupBox {
            font-weight: 700;
            font-size: 12px;
            border: 1px solid #BDBDBD;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 12px;
            color: #1B5E20;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
        }
    """)
    return gb


def _ar_input(placeholder: str = "") -> QLineEdit:
    """Right-to-left Arabic text input."""
    le = QLineEdit()
    le.setLayoutDirection(Qt.RightToLeft)
    le.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    if placeholder:
        le.setPlaceholderText(placeholder)
    return le


class ClientDialog(QDialog):
    """Full-featured Fiche Client dialog (bilingual, multi-section, financial panel)."""

    def __init__(self, user, client: Client = None, parent=None):
        super().__init__(parent)
        self.user = user
        self.client = client
        self.db_session = get_session()
        self.service = ClientService(self.db_session)
        self._ext = _load_ext(client) if client else {}

        self.setWindowTitle("Fiche Client — Modifier" if client else "Fiche Client — Nouveau")
        self.setMinimumSize(860, 680)
        self.resize(920, 720)
        self._setup_ui()

        if self.client:
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
        header = QLabel("🧾  FICHE CLIENT")
        header.setStyleSheet(
            "font-size:16px; font-weight:700; color:#FFFFFF;"
            "background:#1B5E20; padding:10px 16px; border-radius:4px;"
        )
        left_layout.addWidget(header)

        # Section 1 — Identité
        id_box = _section_box("① Identité")
        id_form = QFormLayout(id_box)
        id_form.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom complet (français)")
        id_form.addRow("Nom (Fr) *", self.name_input)

        self.name_ar_input = _ar_input("الاسم الكامل")
        id_form.addRow("Nom (Ar)", self.name_ar_input)

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Ex: GROSSISTE, PHARMACIE...")
        id_form.addRow("Catégorie", self.category_input)

        self.activity_input = QLineEdit()
        self.activity_input.setPlaceholderText("Activité commerciale")
        id_form.addRow("Activité", self.activity_input)

        left_layout.addWidget(id_box)

        # Section 2 — Adresse
        addr_box = _section_box("② Adresse")
        addr_form = QFormLayout(addr_box)
        addr_form.setSpacing(8)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Adresse principale (français)")
        addr_form.addRow("Adresse (Fr)", self.address_input)

        self.address_ar_input = _ar_input("العنوان الرئيسي")
        addr_form.addRow("Adresse (Ar)", self.address_ar_input)

        self.delivery_addr_input = QLineEdit()
        self.delivery_addr_input.setPlaceholderText("Adresse de livraison (si différente)")
        addr_form.addRow("Livraison (Fr)", self.delivery_addr_input)

        self.delivery_ar_input = _ar_input("عنوان التسليم")
        addr_form.addRow("Livraison (Ar)", self.delivery_ar_input)

        left_layout.addWidget(addr_box)

        # Section 3 — Contact
        contact_box = _section_box("③ Contact")
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
        self.email_input.setPlaceholderText("email@example.com")
        contact_form.addRow("Email", self.email_input)

        left_layout.addWidget(contact_box)

        # Section 4 — Fiscal
        fiscal_box = _section_box("④ Fiscal")
        fiscal_box.setStyleSheet(fiscal_box.styleSheet().replace("color: #1B5E20", "color: #E65100"))
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
        notes_box = _section_box("⑤ Notes")
        notes_layout = QVBoxLayout(notes_box)
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(70)
        self.notes_input.setPlaceholderText("Observations, remarques...")
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
        cr_init_label = QLabel("Crédit initial")
        cr_init_label.setStyleSheet("font-size:11px; color:#757575; font-weight:600;")
        right_layout.addWidget(cr_init_label)

        self.credit_initial_spin = QDoubleSpinBox()
        self.credit_initial_spin.setRange(-9999999.99, 9999999.99)
        self.credit_initial_spin.setSuffix(" DA")
        if self.client:
            self.credit_initial_spin.setReadOnly(True)
            self.credit_initial_spin.setStyleSheet("background:#EEEEEE; color:#424242;")
        else:
            self.credit_initial_spin.setStyleSheet("background:#FFFFFF; color:#000000; font-weight: bold;")
        right_layout.addWidget(self.credit_initial_spin)

        # Alarm
        alarm_label = QLabel("🔔  Alerte versement")
        alarm_label.setStyleSheet("font-size:11px; color:#757575; font-weight:600;")
        right_layout.addWidget(alarm_label)

        alarm_row = QHBoxLayout()
        alarm_row.addWidget(QLabel("Chaque"))
        self.alarm_days_spin = QSpinBox()
        self.alarm_days_spin.setRange(0, 365)
        self.alarm_days_spin.setSuffix(" jours")
        alarm_row.addWidget(self.alarm_days_spin)
        right_layout.addLayout(alarm_row)

        # Credit max (editable)
        cr_max_label = QLabel("Crédit Maximum")
        cr_max_label.setStyleSheet("font-size:11px; color:#757575; font-weight:600;")
        right_layout.addWidget(cr_max_label)

        self.credit_limit_spin = QDoubleSpinBox()
        self.credit_limit_spin.setMaximum(9999999.99)
        self.credit_limit_spin.setSuffix(" DA")
        self.credit_limit_spin.setStyleSheet("background:#FFEBEE; color:#C62828; font-weight:700;")
        right_layout.addWidget(self.credit_limit_spin)

        # Blocage
        self.bloquer_check = QCheckBox("🚫  Client Bloqué")
        self.bloquer_check.setStyleSheet("font-weight:600; color:#B71C1C;")
        right_layout.addWidget(self.bloquer_check)

        right_layout.addStretch()

        # Action buttons (vertical stack)
        btn_style_save = (
            "QPushButton { background:#1B5E20; color:#FFF; font-weight:700;"
            "border-radius:5px; padding:10px; font-size:13px; }"
            "QPushButton:hover { background:#2E7D32; }"
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
        c = self.client
        ext = self._ext

        self.name_input.setText(c.name or "")
        self.phone_input_set(c.phone or "")
        self.address_input.setText(c.address or "")
        self.email_input.setText(c.email or "")
        self.credit_limit_spin.setValue(c.credit_limit or 0.0)

        # Extended fields
        self.name_ar_input.setText(ext.get("name_ar", ""))
        self.category_input.setText(ext.get("category", ""))
        self.activity_input.setText(ext.get("activity", ""))
        self.address_ar_input.setText(ext.get("address_ar", ""))
        self.delivery_addr_input.setText(ext.get("delivery_addr", ""))
        self.delivery_ar_input.setText(ext.get("delivery_ar", ""))
        self.fax_input.setText(ext.get("fax", ""))
        self.mobile_input.setText(ext.get("mobile", ""))
        self.rc_input.setText(ext.get("rc", ""))
        self.nif_input.setText(ext.get("nif", c.tax_id or ""))
        self.nis_input.setText(ext.get("nis", ""))
        self.article_input.setText(ext.get("article", ""))
        self.tax_center_input.setText(ext.get("tax_center", ""))
        self.soumis_tva_check.setChecked(ext.get("soumis_tva", False))
        self.credit_initial_spin.setValue(ext.get("credit_initial", 0.0))
        self.alarm_days_spin.setValue(ext.get("alarm_days", 0))
        self.bloquer_check.setChecked(bool(getattr(c, "is_blocked", False) or ext.get("bloquer", False)))
        self.notes_input.setPlainText(_get_plain_notes(c))

    def phone_input_set(self, val):
        """Helper: set phone into tel_input."""
        self.tel_input.setText(val)

    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Erreur", "Le nom du client est obligatoire.")
            return

        # Core model fields
        data = {
            "name": name,
            "phone": self.tel_input.text().strip() or None,
            "address": self.address_input.text().strip() or None,
            "email": self.email_input.text().strip() or None,
            "credit_limit": self.credit_limit_spin.value(),
            "tax_id": self.nif_input.text().strip() or None,
        }

        # Extended JSON fields
        ext = {
            "name_ar": self.name_ar_input.text().strip(),
            "category": self.category_input.text().strip(),
            "activity": self.activity_input.text().strip(),
            "address_ar": self.address_ar_input.text().strip(),
            "delivery_addr": self.delivery_addr_input.text().strip(),
            "delivery_ar": self.delivery_ar_input.text().strip(),
            "fax": self.fax_input.text().strip(),
            "mobile": self.mobile_input.text().strip(),
            "rc": self.rc_input.text().strip(),
            "nif": self.nif_input.text().strip(),
            "nis": self.nis_input.text().strip(),
            "article": self.article_input.text().strip(),
            "tax_center": self.tax_center_input.text().strip(),
            "soumis_tva": self.soumis_tva_check.isChecked(),
            "credit_initial": self.credit_initial_spin.value(),
            "alarm_days": self.alarm_days_spin.value(),
            "bloquer": self.bloquer_check.isChecked(),
        }

        plain_notes = self.notes_input.toPlainText().strip()
        blob = json.dumps({_JSON_KEY: ext, "notes": plain_notes}, ensure_ascii=False)
        data["notes"] = blob

        try:
            if self.client:
                self.service.update_client(self.client.id, data)
                # Handle is_blocked if the model supports it
                try:
                    self.client.is_blocked = self.bloquer_check.isChecked()
                    self.db_session.commit()
                except Exception:
                    pass
            else:
                new_c = self.service.create_client(data)
                
                # Create initial debt if provided
                initial_val = self.credit_initial_spin.value()
                if initial_val != 0.0:
                    from app.models.debt import Debt
                    from app.constants import DebtStatus
                    init_debt = Debt(
                        entity_type="CLIENT",
                        entity_id=new_c.id,
                        reference_type="INITIAL_BALANCE",
                        reference_id=0,
                        total_amount=initial_val if initial_val > 0 else 0.0,
                        paid_amount=abs(initial_val) if initial_val < 0 else 0.0,
                        remaining_amount=initial_val,
                        status=DebtStatus.PENDING.value if initial_val > 0 else DebtStatus.PAID.value,
                        notes="Solde Initial"
                    )
                    self.db_session.add(init_debt)
                    self.db_session.commit()
                    
            self.accept()
        except ValidationError as e:
            QMessageBox.warning(self, "Erreur de validation", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Erreur système", str(e))
